"""Explicit foreground supervision; one execution loop and independent delivery loop."""

from datetime import datetime, timezone
import json
import os
import signal
import tempfile
import threading


class Supervisor:
    def __init__(self, manager, *, interval=1, status_interval=5):
        if not 0 < interval <= 60 or not 0 < status_interval <= 60:
            raise ValueError("Worker intervals must be positive and at most 60 seconds.")
        self.manager = manager
        self.interval, self.status_interval = interval, status_interval
        self.stop = threading.Event()
        self.failed = threading.Event()
        self.execution_done = threading.Event()
        self.status_path = manager.store.path.parent / "worker-status.json"
        if self.status_path.is_symlink():
            raise ValueError("Worker status cannot be symlinked.")
        self.state = "starting"
        self.threads = []

    def status(self):
        with self.manager.store.connection() as database:
            runs = dict(database.execute("SELECT status,COUNT(*) FROM runs GROUP BY status").fetchall())
            deliveries = dict(database.execute("SELECT status,COUNT(*) FROM deliveries GROUP BY status").fetchall())
        return dict(pid=os.getpid(), state=self.state,
                    updated_at=datetime.now(timezone.utc).isoformat(),
                    execution_alive=bool(self.threads and self.threads[0].is_alive()),
                    delivery_alive=bool(len(self.threads) > 1 and self.threads[1].is_alive()),
                    runs=runs, deliveries=deliveries)

    def publish(self, stdout):
        payload = self.status()
        descriptor, temporary = tempfile.mkstemp(prefix=".status-", dir=self.status_path.parent)
        try:
            os.fchmod(descriptor, 0o600)
            with os.fdopen(descriptor, "w") as stream:
                json.dump(payload, stream)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, self.status_path)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)
        print(json.dumps(payload), file=stdout, flush=True)

    def run(self, stdout, *, once=False, signals=False):
        def execution_loop():
            try:
                while not self.stop.is_set():
                    self.manager.worker.tick()
                    if once:
                        break
                    self.stop.wait(self.interval)
            except Exception:
                self.failed.set()
                self.stop.set()
            finally:
                self.execution_done.set()

        def delivery_loop():
            try:
                while not self.stop.is_set():
                    result = self.manager.sender.tick()
                    if once and self.execution_done.is_set() and result is None:
                        break
                    self.stop.wait(self.interval)
            except Exception:
                self.failed.set()
                self.stop.set()

        def report():
            try:
                self.publish(stdout)
            except Exception:
                self.failed.set()
                self.stop.set()
                try:
                    print("Cron worker status unavailable; stopping for local review.", file=stdout, flush=True)
                except OSError:
                    pass

        previous = {}
        if signals:
            def stop(signum, frame):
                self.stop.set()
            for sig in (signal.SIGINT, signal.SIGTERM):
                previous[sig] = signal.signal(sig, stop)
        self.threads = [threading.Thread(target=execution_loop, name="senai-cron-execution"),
                        threading.Thread(target=delivery_loop, name="senai-cron-delivery")]
        try:
            self.state = "running"
            for thread in self.threads:
                thread.start()
            while not self.stop.is_set():
                report()
                if once and all(not thread.is_alive() for thread in self.threads):
                    break
                self.stop.wait(self.status_interval)
        except KeyboardInterrupt:
            self.stop.set()
        except Exception:
            self.failed.set()
            self.stop.set()
        finally:
            self.state = "stopping"
            self.stop.set()
            report()
            # Native execution has a configured deadline; API and DB I/O are bounded.
            for thread in self.threads:
                if thread.ident is not None:
                    thread.join()
            self.state = "failed" if self.failed.is_set() else "stopped"
            report()
            for sig, handler in previous.items():
                signal.signal(sig, handler)
        return 1 if self.failed.is_set() else 0



def worker_main(argv, stdout, stderr, *, status_only=False):
    """Explicit operator command; never started by import or management commands."""
    import argparse
    from pathlib import Path
    from .cron_runtime import TelegramCron
    from .telegram.api import BotAPI
    from .telegram.config import load_credentials, default_env_file
    from .telegram.connection import identify_bot
    from .telegram.store import JobStore
    from .telegram.router import Router
    from .telegram.runner import CommandRunner
    from .telegram.service import instance_lock

    parser = argparse.ArgumentParser(prog="senai cron worker-status" if status_only else "senai cron worker")
    parser.add_argument("--project", required=True, type=Path)
    parser.add_argument("--telegram-account", required=True)
    if not status_only:
        parser.add_argument("--env-file")
        parser.add_argument("--interval", type=float, default=1)
        parser.add_argument("--status-interval", type=float, default=5)
        parser.add_argument("--execution-timeout", type=float, default=300)
        parser.add_argument("--once", action="store_true", help="One execution claim plus currently due delivery; no retry wait.")
        parser.add_argument("--skip-git-repo-check", action="store_true")
        parser.add_argument("--model")
        parser.add_argument("--profile")
        parser.add_argument("--search", action="store_true")
        parser.add_argument("--skill", action="append", default=[])
    args = parser.parse_args(argv)
    api = None
    try:
        project = args.project.expanduser().resolve(strict=True)
        account = args.telegram_account
        if not account.isascii() or not account.isdecimal() or int(account) <= 0:
            raise ValueError("Use the existing numeric Telegram bot ID.")
        workspace = project / "outputs"
        state = workspace / ".senai-telegram" / account
        cron_dir = workspace / ".senai-cron" / "telegram" / account
        for directory in (state, cron_dir):
            for path in (directory, *directory.parents):
                if path == project:
                    break
                if path.is_symlink():
                    raise ValueError("Worker paths cannot be symlinked.")
        if status_only:
            path = cron_dir / "worker-status.json"
            if path.is_symlink():
                raise ValueError("Worker status cannot be symlinked.")
            with path.open() as stream:
                payload = json.loads(stream.read(100001))
            if type(payload.get("pid")) is not int or payload["pid"] <= 0:
                raise ValueError("Invalid saved worker status.")
            try:
                os.kill(payload["pid"], 0)
                payload["pid_alive"] = True
            except ProcessLookupError:
                payload["pid_alive"] = False
            print(json.dumps(payload), file=stdout)
            return 0
        if not 0 < args.interval <= 60 or not 0 < args.status_interval <= 60:
            raise ValueError("Worker intervals must be positive and at most 60 seconds.")
        if not 0 < args.execution_timeout <= 3600:
            raise ValueError("Execution timeout must be positive and at most 3600 seconds.")
        database = state / "state.sqlite3"
        if database.is_symlink() or not database.is_file():
            raise ValueError("Existing paired Telegram state is required; configure a disposable bot/project first.")
        path = Path(args.env_file).expanduser() if args.env_file else default_env_file(project)
        token, users = load_credentials(env_file=path if args.env_file or path.is_file() else None, require_users=False)
        api = BotAPI(token)
        identity = identify_bot(api)
        if str(identity["id"]) != account:
            raise ValueError("Configured token does not match the selected bot ID.")
        # This is the same lock held by the ordinary bot: never race its native session.
        if (state / "bot.lock").is_symlink():
            raise ValueError("Worker lock cannot be symlinked.")
        with instance_lock(state / "bot.lock"):
            store = JobStore(database)
            with store.connection() as db:
                if db.execute("SELECT 1 FROM jobs WHERE status='running' LIMIT 1").fetchone():
                    raise ValueError("A prior Telegram execution needs local review before starting cron.")
            router = Router(store, users, identity["username"])
            from .defaults import load_defaults
            startup_installation = os.environ.get('SENAI_INSTALLATION_ROOT') or load_defaults().get('installation') or ''
            runner = CommandRunner(project, state, store=store,
                skip_git_repo_check=args.skip_git_repo_check, model=args.model,
                profile=args.profile, search=args.search, skills=tuple(args.skill),
                chat_style=True, execution_timeout=args.execution_timeout, installation=startup_installation)
            manager = TelegramCron(project=project, account=account, router=router, runner=runner, api=api)
            if (manager.store.path.parent / "worker.lock").is_symlink():
                raise ValueError("Worker lock cannot be symlinked.")
            with instance_lock(manager.store.path.parent / "worker.lock"):
                return Supervisor(manager, interval=args.interval, status_interval=args.status_interval).run(
                    stdout, once=args.once, signals=True)
    except (ValueError, KeyError, RuntimeError, OSError) as error:
        message = api.redact(str(error)) if api else str(error)
        print("senai cron worker: " + message, file=stderr)
        return 2
