"""Durable delivery independent of task execution."""

class RetryDelivery(Exception):
    """Transport certifies the send was NOT accepted and is safe to retry."""


class DeliveryWorker:
    def __init__(self, store, send, *, max_attempts=3, retry_delay=60):
        if not isinstance(max_attempts, int) or not 1 <= max_attempts <= 10 or retry_delay < 1:
            raise ValueError('invalid delivery retry policy')
        self.store, self.send = store, send
        self.max_attempts, self.retry_delay = max_attempts, retry_delay

    def tick(self):
        item = self.store.claim_delivery()
        if item is None:
            return None
        error = None
        try:
            self.send(item)
        except RetryDelivery as exc:
            status = 'pending' if item['attempt'] < self.max_attempts else 'failed'
            error = str(exc)
        except Exception as exc:
            status, error = 'unknown', str(exc)
        else:
            status = 'delivered'
        self.store.finish_delivery(item['id'], item['token'], status=status,
                                   error=error, retry_delay=self.retry_delay)
        return next(r for r in self.store.deliveries() if r['id'] == item['id'])
