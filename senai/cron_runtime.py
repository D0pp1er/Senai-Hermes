"""Opt-in coordinator adapters: existing authorized Telegram worker to durable cron."""

import argparse
from datetime import datetime
import json
from pathlib import Path
import sqlite3

from .cron.store import Store
from .cron.worker import Worker, UncertainExecution
from .processes import ExecutionUncertain
from .cron.delivery import DeliveryWorker, RetryDelivery
from .integrations.telegram import parse_private_update
from .telegram.api import TelegramError
from .telegram.formatting import split_message
from .workspace import prepare_workspace

CREATE_FIELDS = {"name", "prompt", "at", "timezone", "every", "cron", "misfire",
                 "grace_seconds", "retries", "retry_delay"}
EDIT_FIELDS = CREATE_FIELDS | {"once"}
HELP = (
    '/cron create {"name":"NAME","prompt":"TASK","at":"2030-01-01T09:00:00+06:00"}\n'
    '/cron list | show ID | pause ID | resume ID | delete ID\n'
    '/cron edit ID REVISION {"prompt":"NEW TASK"}\n'
    '/cron runs | deliveries\n'
    'Optional create fields: timezone (default Asia/Dhaka), every seconds or cron '
    '(five fields), misfire (skip/coalesce), grace_seconds, retries, retry_delay. '
    'Chat reminders default to skip after 120 seconds. All results return to this chat.'
)


class TelegramCron:
    """Composition owned by coordinator. Construct only after explicit --enable-cron."""
    scope = "telegram-shared"

    def __init__(self, *, project, account, router, runner, api, clock=None):
        self.project = str(Path(project).expanduser().resolve())
        if not isinstance(account, str) or not account.isascii() or not account.isdecimal():
            raise ValueError("Cron requires a verified numeric bot account.")
        self.account, self.router, self.runner, self.api = account, router, runner, api
        self.store = telegram_store(self.project, account, clock=clock)
        self.worker = Worker(self.store, self.execute)
        self.sender = DeliveryWorker(self.store, self.send, max_attempts=3, retry_delay=60)

    def is_authorized(self, user):
        return self.router.is_authorized(user)

    def target(self, user):
        return dict(platform="telegram", account=self.account, project=self.project,
                    scope=self.scope, user_id=user, chat_id=user)

    def authorize(self, target):
        if not isinstance(target, dict):
            raise PermissionError("Scheduled destination is not authorized.")
        user = target.get("user_id")
        if (type(user) is not int or user <= 0 or type(target.get("chat_id")) is not int
                or target != self.target(user) or not self.is_authorized(user)):
            raise PermissionError("Scheduled destination is not authorized.")
        return user

    def snapshot(self, run):
        snapshot = json.loads(run["snapshot"])
        if snapshot.get("project") != self.project or snapshot.get("scope") != self.scope:
            raise PermissionError("Scheduled execution scope is not authorized.")
        return snapshot

    def execute(self, run):
        snapshot = self.snapshot(run)
        target = json.loads(snapshot["delivery_target"])
        user = self.authorize(target)
        # Same native runner/session store, called on the existing single worker only.
        job = dict(id="cron-" + run["id"] + "-" + str(run["attempt"]),
                   prompt=snapshot["prompt"], user_id=user, chat_id=target["chat_id"])
        try:
            status, response = self.runner(job)
        except ExecutionUncertain as error:
            raise UncertainExecution(str(error)) from None
        if status != "succeeded":
            raise RuntimeError(self.api.redact(response))
        return response

    def send(self, item):
        self.authorize(item["target"])
        snapshot = self.snapshot(item["run"])
        if json.loads(snapshot["delivery_target"]) != item["target"]:
            raise PermissionError("Delivery does not match its immutable scheduled destination.")
        run = item["run"]
        text = ("Scheduled task: " + snapshot["name"] + "\n" +
                (run["result"] if run["status"] == "succeeded" else
                 ("The scheduled request outcome is unknown; its schedule is paused for local review."
                  if run["status"] == "unknown" else
                  "The scheduled request failed. Review local cron run history.")))
        sent = 0
        for part in split_message(self.api.redact(text)):
            self.authorize(item["target"])
            try:
                result = self.api.send_message(item["target"]["chat_id"], part)
            except TelegramError as error:
                # Telegram 429 certifies rejection of this request. Retrying a partially
                # sent multi-part result would duplicate earlier parts, so keep unknown.
                if error.status == 429 and error.not_accepted and sent == 0:
                    raise RetryDelivery("Telegram rate-limited before accepting the result.") from None
                raise
            if not isinstance(result, dict) or type(result.get("message_id")) is not int:
                raise RuntimeError("Telegram did not confirm message acceptance.")
            sent += 1

    def tick(self):
        run = self.worker.tick()
        delivery = self.sender.tick()
        return run is not None or delivery is not None

    def owned(self, identifier, user):
        schedule = self.store.get(identifier)
        target = json.loads(schedule["delivery_target"] or "null")
        if self.authorize(target) != user:
            raise PermissionError("This schedule belongs to another private chat.")
        return schedule

    @staticmethod
    def describe(schedule):
        recurrence = schedule["cron"] or (
            "every " + str(schedule["every"]) + " seconds" if schedule["every"] else "one-shot")
        return (schedule["id"] + " — " + schedule["name"] + "\nNext: " +
                str(schedule["next_due_local"]) + " (" + schedule["timezone"] + ")\n" +
                recurrence + "; misfire " + schedule["misfire"] +
                "; destination this chat; revision " + str(schedule["revision"]))

    def handle(self, update):
        parsed = parse_private_update(update)
        if parsed is None:
            return self.router.handle(update)
        identifier, user, chat, text = parsed
        parts = text.strip().split(maxsplit=1)
        command, _, mention = (parts[0] if parts else "").partition("@")
        if command != "/cron":
            return self.router.handle(update)
        if mention and mention.lower() != self.router.username:
            return self.router.handle(update)
        if self.router.store.consume(identifier) == "duplicate":
            return []
        if not self.is_authorized(user):
            return []
        try:
            if len(text) > 8000:
                raise ValueError("command too long")
            action, _, argument = (parts[1] if len(parts) > 1 else "help").partition(" ")
            if action == "help":
                response = HELP
            elif action == "create":
                spec = json.loads(argument)
                if not isinstance(spec, dict) or set(spec) - CREATE_FIELDS:
                    raise ValueError("unsupported create fields")
                spec = dict(spec)
                spec["at"] = datetime.fromisoformat(spec["at"])
                spec.setdefault("misfire", "skip")
                ident = self.store.create(**spec, project=self.project, scope=self.scope,
                                          delivery_target=self.target(user))
                response = self.describe(self.store.get(ident))
            elif action == "list":
                owned = []
                for schedule in self.store.list():
                    try:
                        owned.append(self.describe(self.owned(schedule["id"], user)))
                    except PermissionError:
                        continue
                response = "\n\n".join(owned) or "No schedules in this chat."
            elif action in ("runs", "deliveries"):
                rows = []
                for row in getattr(self.store, action)():
                    run = row if action == "runs" else next(
                        run for run in self.store.runs() if run["id"] == row["run_id"])
                    try:
                        target = json.loads(run["snapshot"])["delivery_target"]
                        if self.authorize(json.loads(target)) != user:
                            continue
                    except (PermissionError, ValueError, KeyError, TypeError):
                        continue
                    rows.append(row["id"] + ": " + row["status"] +
                                " (attempt " + str(row["attempt"]) + ")")
                response = "\n".join(rows) or "No cron history in this chat."
            elif action == "edit":
                ident, revision, payload = argument.split(maxsplit=2)
                self.owned(ident, user)
                changes = json.loads(payload)
                if not isinstance(changes, dict) or set(changes) - EDIT_FIELDS:
                    raise ValueError("unsupported edit fields")
                if "at" in changes:
                    changes["at"] = datetime.fromisoformat(changes["at"])
                if changes.pop("once", False):
                    changes.update(every=None, cron=None)
                elif "cron" in changes:
                    changes["every"] = None
                elif "every" in changes:
                    changes["cron"] = None
                updated = self.store.update(ident, expected_revision=int(revision), **changes)
                response = self.describe(updated)
            elif action in ("show", "pause", "resume", "delete"):
                schedule = self.owned(argument, user)
                if action == "show":
                    response = self.describe(schedule)
                else:
                    getattr(self.store, action)(argument)
                    response = action + ": " + schedule["id"]
            else:
                response = HELP
        except (ValueError, TypeError, KeyError, PermissionError, sqlite3.Error):
            response = "Cron command rejected; check arguments, ownership or current revision. Use /cron show ID to review."
        return [(chat, response)]



def telegram_store(project, account, *, clock=None):
    """Select an account namespace; local CLI is trusted operator management."""
    if not isinstance(account, str) or not account.isascii() or not account.isdecimal():
        raise ValueError("Cron requires a numeric Telegram bot account.")
    workspace = prepare_workspace(project)
    directory = workspace / ".senai-cron" / "telegram" / account
    for path in (directory, *directory.parents):
        if path == workspace:
            break
        if path.is_symlink():
            raise ValueError("Cron directories cannot be symlinked.")
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    directory.chmod(0o700)
    path = directory / "cron.db"
    if path.is_symlink():
        raise ValueError("Cron database cannot be symlinked.")
    store = Store(path, clock=clock)
    path.chmod(0o600)
    return store


def manage_cli(argv):
    """Manage schedules through shared CLI without starting a worker."""
    from .cron.__main__ import main
    routing = argparse.ArgumentParser(add_help=False, allow_abbrev=False)
    routing.add_argument("--project")
    routing.add_argument("--telegram-account")
    routing.add_argument("command", nargs="?")
    route, extra = routing.parse_known_args(argv)
    if route.command in ("worker", "worker-status"):
        import sys
        from .cron_supervisor import worker_main
        arguments = list(extra)
        if route.project is not None:
            arguments += ["--project", route.project]
        if route.telegram_account is not None:
            arguments += ["--telegram-account", route.telegram_account]
        return worker_main(arguments, sys.stdout, sys.stderr, status_only=route.command == "worker-status")
    parser = argparse.ArgumentParser(add_help=False, allow_abbrev=False)
    parser.add_argument("--telegram-account")
    args, remaining = parser.parse_known_args(argv)
    factory = (lambda project: telegram_store(project, args.telegram_account)) if args.telegram_account else None
    return main(remaining, store_factory=factory)
