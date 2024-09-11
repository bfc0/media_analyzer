import time


class Timer:

    def __enter__(self):
        self.start = time.monotonic()
        return self

    @property
    def elapsed(self):
        elapsed = time.monotonic() - self.start
        return f"{elapsed:.1f}s"

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass
