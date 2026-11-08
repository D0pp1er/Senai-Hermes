class Worker:
    def __init__(self, store, executor, deliver=None):
        self.store, self.executor, self.deliver = store, executor, deliver

    def tick(self):
        run = self.store.claim()
        if run is None:
            return None
        try:
            result = self.executor(run)
        except Exception as exc:
            self.store.finish(run['id'], error=str(exc))
        else:
            self.store.finish(run['id'], result=result)
        saved = next(r for r in self.store.runs() if r['id'] == run['id'])
        if self.deliver and saved['status'] in ('succeeded', 'failed'):
            try:
                self.deliver(saved)
            except Exception as exc:
                self.store.delivery_failed(run['id'], str(exc))
        return saved
