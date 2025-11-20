from collections import OrderedDict
import time


class TTLCache:
    def __init__(self, maxsize: int = 1000, ttl_seconds: int = 1800):
        self.maxsize = maxsize
        self.ttl = ttl_seconds
        self._store: OrderedDict[str, tuple[float, object]] = OrderedDict()

    def _purge_expired(self):
        now = time.time()
        keys_to_delete = []
        for k, (ts, _) in list(self._store.items()):
            if now - ts > self.ttl:
                keys_to_delete.append(k)
        for k in keys_to_delete:
            self._store.pop(k, None)

    def get(self, key: str):
        self._purge_expired()
        if key in self._store:
            ts, val = self._store.pop(key)
            # re-insert to mark as recently used
            self._store[key] = (ts, val)
            return val
        return None

    def set(self, key: str, value: object):
        self._purge_expired()
        if key in self._store:
            self._store.pop(key)
        self._store[key] = (time.time(), value)
        while len(self._store) > self.maxsize:
            # evict least-recently-used
            self._store.popitem(last=False)

    def make_key(self, url: str) -> str:
        return f"cache_{''.join(ch if ch.isalnum() else '_' for ch in url)}"

