class Worker:
    def __init__(self, store, executor, deliver=None):
        self.store, self.executor, self.deliver = store, executor, deliver

    def tick(self):
        run = self.store.claim()
        if run is None:
            if self.deliver:
                from .delivery import DeliveryWorker
                DeliveryWorker(self.store, lambda item: self.deliver(item['run'])).tick()
            return None
        try:
            result = self.executor(run)
        except Exception as exc:
            self.store.finish(run['id'], error=str(exc), enqueue_delivery=self.deliver is not None)
        else:
            self.store.finish(run['id'], result=result, enqueue_delivery=self.deliver is not None)
        saved = next(r for r in self.store.runs() if r['id'] == run['id'])
        if self.deliver:
            from .delivery import DeliveryWorker
            DeliveryWorker(self.store, lambda item: self.deliver(item['run'])).tick()
        return saved
