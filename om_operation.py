import time

# WARNING: There is no safety factor taken into account here.
# The caller must provide their own buffers on time and distance
# as needed.

DEBUG = True

# ------------------------------------------------------------------------------
class Operation:
    """
    This class represents the state of an automatic move operation.

    It tries to keep track of the position, speed, and acceleration
    of the main line and ensures that it gets shut off in time.
    """
    def __init__(self, max_distance_m, max_time_s, pulley_diameter_m, on_complete):
        """
        Operation Data
        """
        assert pulley_diameter_m >= 0.01, "Your pulley is too small"

        # TODO:
        # We can only count full revolutions so this
        # is potentially overshooting by one pulley distance.
        self._max_revolutions = max_distance_m // pulley_diameter_m
        self._max_time_s = max_time_s
        self._max_distance_m = max_distance_m
        self._pulley_diameter_m = pulley_diameter_m

        self._start_time = None
        self._last_revolution = None
        self._last_speed_mps = None
        self._max_speed_mps = None
        self._duration_s = None

        # This function is called when we exceed our max revolutions or time
        self._on_complete = on_complete

        self._start()

    def _start(self):
        self._start_time = time.monotonic()
        self._last_revolution = self._start_time
        self._last_tick = self._start_time
        self._distance_m = 0.0
        self._revolutions = 0

    def _complete(self):
        self._duration_s = time.monotonic() - self._start_time
        self._last_speed_mps = None
        self._on_complete()

    def revolve(self):
        now = time.monotonic()
        self._revolutions += 1
        self._distance_m += self._pulley_diameter_m
        if self._last_revolution is not None:
            # We can't reasonably guess speed unless we know we have fully gone around at least once
            delta = now - self._last_revolution
            # Catch divide by zero and set reasonable max speed
            if delta <= 0.01:
                delta = 0.01
            speed_mps = self._pulley_diameter_m / delta
            self._last_speed_mps = speed_mps
            if self._max_speed_mps is None or speed_mps > self._max_speed_mps:
                self._max_speed_mps = speed_mps
        self._last_revolution = now

        if self._revolutions >= self._max_revolutions:
            self._complete()
        elif self._distance_m >= self._max_distance_m:
            self._complete()

        # TODO: Log differently
        if DEBUG:
            print(f"   ...{self._distance_m} / {self._max_distance_m}")

        # TODO: Calculate speed assuming constant acceleration
        # unless speed is approximately the same as previous iteration.

        # TODO: Set up a Kalman filter or something to try and keep track of position

    def tick(self):
        now = time.monotonic()
        delta = now - self._last_tick
        self._last_tick = now
        if self._max_time_s and now - self._start_time >= self._max_time_s:
            self._complete()

    def distance_m(self):
        return self._distance_m

    def speed_mps(self):
        return self._last_speed_mps

    def max_speed_mps(self):
        return self._max_speed_mps

    def revolutions(self):
        return self._revolutions

    def duration(self):
        if self._duration_s is not None:
            return self._duration_s
        else:
            return time.monotonic() - self._start_time
