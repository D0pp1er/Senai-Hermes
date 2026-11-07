"""Long-polling controller and independent single-worker execution loop."""

from contextlib import contextmanager
from pathlib import Path
import threading

from .api import TelegramError
from .formatting import split_message
from .router import result_text


@contextmanager
def instance_lock(path):
    import fcntl
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('a+') as lock:
        path.chmod(0o600)
        try:
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise ValueError('Telegram is already running for this bot and project.') from None
        try:
            yield
        finally:
            fcntl.flock(lock.fileno(), fcntl.LOCK_UN)


class BotService:
    def __init__(self, api, store, router, runner, *, poll_timeout=10):
        self.api, self.store, self.router, self.runner = api, store, router, runner
        self.poll_timeout = poll_timeout
        self.stop = threading.Event()
        self.worker_failed = False

    def skip_pending(self):
        updates = self.api.get_updates(-1, timeout=0)
        identifiers = [item['update_id'] for item in updates if isinstance(item, dict) and type(item.get('update_id')) is int]
        if identifiers:
            self.store.set_offset(max(identifiers) + 1)

    def send_text(self, chat_id, text):
        for part in split_message(self.api.redact(text)):
            self.api.send_message(chat_id, part)

    def deliver_results(self):
        for job in self.store.pending_results():
            if job['user_id'] not in self.router.allowed_users:
                self.store.mark_delivered(job['id'])
                continue
            parts = split_message(self.api.redact(result_text(job)))
            for part in parts[job['parts_sent']:]:
                self.api.send_message(job['chat_id'], part)
                self.store.mark_part_sent(job['id'])
            self.store.mark_delivered(job['id'])

    def poll_once(self):
        self.deliver_results()
        updates = self.api.get_updates(self.store.offset(), timeout=self.poll_timeout)
        updates = [item for item in updates if isinstance(item, dict) and type(item.get('update_id')) is int]
        for update in sorted(updates, key=lambda item: item['update_id']):
            for chat_id, text in self.router.handle(update):
                self.send_text(chat_id, text)
        self.deliver_results()

    def run_one(self):
        job = self.store.claim_next()
        if job is None:
            return False
        if job['user_id'] not in self.router.allowed_users:
            status, text = 'failed', 'Authorization was revoked; this queued request was not executed.'
        else:
            try:
                status, text = self.runner(job)
            except Exception:
                status, text = 'failed', 'Local request execution failed. Inspect the bot terminal and local job logs.'
        self.store.finish(job['id'], status, text)
        return True

    def run_forever(self, stdout, stderr):
        def worker_loop():
            try:
                while not self.stop.is_set():
                    if not self.run_one():
                        self.stop.wait(0.25)
            except Exception:
                self.worker_failed = True
                self.stop.set()
        worker = threading.Thread(target=worker_loop, name='senai-telegram-worker')
        worker.start()
        try:
            while not self.stop.is_set():
                try:
                    self.poll_once()
                except TelegramError as error:
                    if error.status in (401, 403, 409):
                        raise
                    print(self.api.redact(str(error)) + ' Retrying; saved jobs will not be rerun.', file=stderr, flush=True)
                    self.stop.wait(min(error.retry_after or 3, 60))
            if self.worker_failed:
                raise RuntimeError('Telegram job worker failed; inspect the local state/logs before restarting.')
            return 0
        except KeyboardInterrupt:
            print('Stopping after the active request finishes. Queued jobs and pending replies remain saved.', file=stdout, flush=True)
            return 130
        finally:
            self.stop.set()
            worker.join()
