import configparser

class Config:
    """
    Provides the 'static' configuration for the system.

    This is loaded from a file and may be changed by the portal.

    Each configurable item should have as specific allowed range that may
    even be hardcoded to avoid mistaken values.

    For example, fix the maximum speed and length of the run.
    """
    def __init__(self, filename):
        #self._pulley_diameter_m = 0.22
        #self._brake_length_m = 10
        #self._accel_length_m = 20
        #self._length_m = 30
        #self._limit_pos_m = 0.5
        #self._start_pos_m = 4
        #self._limit_range_m = 0.1
        #self._brake_delay_s = 0.1
        #self._max_speed_mps = 0.1
        #self._jog_speed_mps = 0.1
        self.load(filename)

    def load(self, filename):
        config = configparser.ConfigParser()
        config.read(filename)

        geometry = config["geometry"]

        # Geometry settings
        self._pulley_diameter = float(geometry["pulley_diameter_m"])
        self._length_m = float(geometry["length_m"])
        self._limit_range_m = float(geometry["limit_range_m"])
        self._limit_pos_m = float(geometry["limit_pos_m"])
        self._start_pos_m = float(geometry["start_pos_m"])
        self._accel_length_m = float(geometry["accel_length_m"])
        self._brake_length_m  = float(geometry["brake_length_m"])

        # Power settings
        power = config["power"]
        self._brake_delay_s = float(power["brake_delay_s"])
        self._max_speed_mps = float(power["max_speed_mps"])
        self._jog_speed_mps = float(power["jog_speed_mps"])

        # Sanity check settings
        self.validate()

    def validate(self):
        assert 0.05 <= self._pulley_diameter <= 0.25, "Invalid pulley diameter"
        assert 3.0 <= self._start_pos_m <= 10.0, "Invalid length"
        assert 0.05 <= self._limit_range_m <= 0.3, "Invalid limit range"
        assert 0.1 <= self._limit_pos_m <= 2.0, "Invalid limit position"
        assert self._limit_pos_m > self._limit_range_m, "Limit range is insufficient for position"
        assert 3.0 <= self._start_pos_m <= 10.0, "Invalid start position"
        assert self._limit_pos_m < self._start_pos_m, "Limit is before start"
        assert 1.0 <= self._accel_length_m <= 25.0, "Invalid acceleration length"
        assert 3.0 <= self._brake_length_m <= 30.0, "Invalid brake length"
        length_sum_m = (self._brake_length_m + self._accel_length_m + self._start_pos_m)
        assert abs(self._length_m - length_sum_m) < 0.1, "Invalid lengths {} and {} do not add up".format(self._length_m, length_sum_m)
        assert 0.01 <= self._brake_delay_s  <= 0.25, "Invalid brake delay"
        assert 0.0 <= self._max_speed_mps < 10.0, "Invalid max speed"
        assert 0.0 < self._jog_speed_mps <= 1.0, "Invalid jog speed"
        assert self._jog_speed_mps <= self._max_speed_mps, "Jog speed exceeds max speed"

    def __str__(self):
        # TODO: Make me print nicely in imperial and metric units
        return str(self.__dict__)

    # Getters so we don't accidentally modify values
    def pulley_diameter_m(self):
        return self._pulley_diameter_m
    def brake_length_m(self):
        return self._brake_length_m
    def accel_length_m(self):
        return self._accel_length_m
    def start_pos_m(self):
        return self._start_pos_m
    def length_m(self):
        return self._length_m
    def limit_range_m(self):
        return self._limit_range_m
    def brake_delay_s(self):
        return self._brake_delay_s
    def max_speed_mps(self):
        return self._max_speed_mps
    def jog_speed_mps(self):
        return self._jog_speed_mps

