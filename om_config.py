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
        ##self._length_m = 30
        #self._limit_pos_m = 0.5
        #self._start_pos_m = 4
        #self._limit_range_m = 0.1
        self._stop_time_s = 1.0
        self._run_time_s = 2.0

        #self._brake_delay_s = 0.1
        #self._max_speed_mps = 0.1
        #self._jog_speed_mps = 0.2
        #self._return_speed_mps = 0.1

        self._motor_forward_pin = 22
        self._motor_backward_pin = 23
        self._motor_speed_pin = 12
        self._brake_pin = 24
        self._engage_led_pin = 6
        self._go_led_pin = 27

        self._engage_button_pin = 26
        self._go_button_pin = 16
        self._return_button_pin = 13
        self._backward_button_pin = 17
        self._forward_button_pin = 18
        self._estop_button_pin = 21

        self._limit_sensor_pin = 5
        self._rotate_sensor_pin = 20

        self._debounce_consecutive = 20

        self.load(filename)

    def load(self, filename):
        config = configparser.ConfigParser()
        config.read(filename)

        timing = config["timing"]
        self._stop_time_s = float(timing["stop_time_s"])
        self._run_time_s = float(timing["run_time_s"])

        geometry = config["geometry"]

        # Geometry settings
        #self._pulley_diameter = float(geometry["pulley_diameter_m"])
        #self._length_m = float(geometry["length_m"])
        #self._limit_range_m = float(geometry["limit_range_m"])
        #self._limit_pos_m = float(geometry["limit_pos_m"])
        #self._start_pos_m = float(geometry["start_pos_m"])
        #self._accel_length_m = float(geometry["accel_length_m"])
        #self._brake_length_m  = float(geometry["brake_length_m"])

        # Power settings
        power = config["power"]
        #self._brake_delay_s = float(power["brake_delay_s"])
        #self._max_speed_mps = float(power["max_speed_mps"])
        #self._jog_speed_mps = float(power["jog_speed_mps"])
        #self._return_speed_mps = float(power["return_speed_mps"])

        # Pin Settings
        pins = config["pins"]
        self._motor_forward_pin = int(pins["motor_forward"])
        self._motor_backward_pin = int(pins["motor_backward"])
        self._motor_speed_pin = int(pins["motor_speed"])
        self._brake_pin = int(pins["brake"])
        self._engage_led_pin = int(pins["engage_led"])
        self._go_led_pin = int(pins["go_led"])

        self._engage_button_pin = int(pins["engage_button"])
        self._go_button_pin = int(pins["go_button"])
        self._return_button_pin = int(pins["return_button"])
        self._backward_button_pin = int(pins["backward_button"])
        self._forward_button_pin = int(pins["forward_button"])

        self._limit_sensor_pin = int(pins["limit_sensor"])
        self._rotate_sensor_pin = int(pins["rotate_sensor"])
        self._estop_button_pin = int(pins["estop_button"])

        # Misc Settings
        misc = config["misc"]
        #self._button_debounce_s = float(power["button_debounce_s"])
        #if self._button_debounce_s == 0.0:
        #    self._button_debounce_s = None
        self._debounce_consecutive = int(misc["debounce_consecutive"])

        # Sanity check settings
        self.validate()

    def validate(self):
        # Timing
        assert 0.1 <= self._stop_time_s <= 10.0, "Extreme start time "
        assert 0.1 <= self._run_time_s <= 10.0, "Extreme run time "

        # Geometry
        #assert 0.05 <= self._pulley_diameter <= 0.25, "Invalid pulley diameter"
        #assert 3.0 <= self._start_pos_m <= 10.0, "Invalid length"
        #assert 0.05 <= self._limit_range_m <= 0.3, "Invalid limit range"
        #assert 0.1 <= self._limit_pos_m <= 2.0, "Invalid limit position"
        #assert self._limit_pos_m > self._limit_range_m, "Limit range is insufficient for position"
        #assert 3.0 <= self._start_pos_m <= 10.0, "Invalid start position"
        #assert self._limit_pos_m < self._start_pos_m, "Limit is before start"
        #assert 1.0 <= self._accel_length_m <= 25.0, "Invalid acceleration length"
        #assert 3.0 <= self._brake_length_m <= 30.0, "Invalid brake length"
        #length_sum_m = (self._brake_length_m + self._accel_length_m + self._start_pos_m)
        #assert abs(self._length_m - length_sum_m) < 0.1, "Invalid lengths {} and {} do not add up".format(self._length_m, length_sum_m)

        # Power
        #assert 0.01 <= self._brake_delay_s  <= 0.25, "Invalid brake delay"
        #assert 0.0 <= self._max_speed_mps < 10.0, "Invalid max speed"

        #assert 0.0 < self._jog_speed_mps <= 1.0, "Invalid jog speed"
        #assert self._jog_speed_mps <= self._max_speed_mps, "Jog speed exceeds max speed"

        #assert 0.0 < self._return_speed_mps <= 0.5, "Invalid jog speed"
        #assert self._return_speed_mps <= self._max_speed_mps, "Return speed exceeds max speed"

        # Misc
        #assert self._button_debounce_s is None or 0.0 < self._button_debounce_s < 0.25, "Invalid button debounce value"
        assert self._debounce_consecutive is None or 10 < self._debounce_consecutive < 1000, "Invalid debounce consecutive value"


        # Pins
        pins = [
            self._motor_forward_pin,
            self._motor_backward_pin,
            self._motor_speed_pin,
            self._brake_pin,
            self._engage_led_pin,
            self._go_led_pin,

            self._engage_button_pin,
            self._go_button_pin,
            self._return_button_pin,
            self._backward_button_pin,
            self._forward_button_pin,

            self._limit_sensor_pin,
            self._rotate_sensor_pin,
            self._estop_button_pin,
        ]
        # FIXME: Are 9, 10, 11, 0 allowed?
        unconfirmed_gpio_pins = set([1, 8, 9, 10, 11, 14, 15, 19])
        gpio_pins = set([
            1, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27,
        ])
        assert len(set(pins)) == len(pins), "Duplicate pin assignments detected"
        for pin in pins:
            if pin in unconfirmed_gpio_pins:
                print(f"GPIO pin {pin} was designated but is unconfirmed to work.")
            assert str(pin) == str(int(pin)), f"Non numeric pin designation '{pin}"
            assert pin in gpio_pins, f"Non-GPIO pin {pin} requested"

    def __str__(self):
        # TODO: Make me print nicely in imperial and metric units
        return str(self.__dict__)

    # Getters so we don't accidentally modify values
    #def pulley_diameter_m(self):
    #    return self._pulley_diameter_m
    #def brake_length_m(self):
    #    return self._brake_length_m
    #def accel_length_m(self):
    #    return self._accel_length_m
    #def start_pos_m(self):
    #    return self._start_pos_m
    #def length_m(self):
    #    return self._length_m
    #def limit_range_m(self):
    #    return self._limit_range_m
    #def brake_delay_s(self):
    #    return self._brake_delay_s
    #def max_speed_mps(self):
    #    return self._max_speed_mps
    #def jog_speed_mps(self):
    #    return self._jog_speed_mps
    #def return_speed_mps(self):
    #    return self._return_speed_mps
    #def button_debounce_s(self):
    #    return self._button_debounce_s

    def run_time_s(self):
        return self._run_time_s
    def stop_time_s(self):
        return self._stop_time_s

    def motor_forward_pin(self):
        return self._motor_forward_pin
    def motor_backward_pin(self):
        return self._motor_backward_pin
    def motor_speed_pin(self):
        return self._motor_speed_pin
    def brake_pin(self):
        return self._brake_pin
    def engage_led_pin(self):
        return self._engage_led_pin
    def go_led_pin(self):
        return self._go_led_pin
    def engage_button_pin(self):
        return self._engage_button_pin
    def go_button_pin(self):
        return self._go_button_pin
    def return_button_pin(self):
        return self._return_button_pin
    def backward_button_pin(self):
        return self._backward_button_pin
    def forward_button_pin(self):
        return self._forward_button_pin
    def limit_sensor_pin(self):
        return self._limit_sensor_pin
    def rotate_sensor_pin(self):
        return self._rotate_sensor_pin
    def estop_button_pin(self):
        return self._estop_button_pin

    def debounce_consecutive(self):
        return self._debounce_consecutive
