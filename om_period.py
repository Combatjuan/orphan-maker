import time

# WARNING: There is no safety factor taken into account here.
# The caller must provide their own buffers on time and distance
# as needed.

DEBUG = True

# ------------------------------------------------------------------------------
class Period:
    """
    This class represents the state of an automatic move operation.

    It tries to keep track of the position, speed, and acceleration
    of the main line and ensures that it gets shut off in time.
    """
    def __init__(self, max_time_s, on_complete):
        """
        Period Data
        """
        # TODO:
        # We can only count full revolutions so this
        # is potentially overshooting by one pulley distance.
        self._max_time_s = max_time_s

        self._start_time = None
        self._duration_s = None

        # This function is called when we exceed our max revolutions or time
        self._on_complete = on_complete

        self._start()

    def _start(self):
        self._start_time = time.monotonic()
        self._last_tick = self._start_time

    def _complete(self):
        self._duration_s = time.monotonic() - self._start_time
        self._on_complete()

    def tick(self):
        now = time.monotonic()
        delta = now - self._last_tick
        self._last_tick = now
        if self._max_time_s and now - self._start_time >= self._max_time_s:
            self._complete()

    def duration(self):
        if self._duration_s is not None:
            return self._duration_s
        else:
            return time.monotonic() - self._start_time
