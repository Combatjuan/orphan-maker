import enum
import functools
import sys
import time

import gpiozero

from om_operation import Operation

# ------------------------------------------------------------------------------
# State Transition Matrix
# From             0S  1AE 2AS 3AG 4RU 5ST 6RT 7JF 8JR 9ER
# ----------------+---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+
# 0 STARTING      | . | I | . | . | . | . | . | . | . | x |
# 1 AWAIT_ENGAGE  | . | . | E | . | . | . | . | . | . | x |
# 2 AWAIT_SET     | . | e | . | S | . | . | R | J | J | x |
# 3 AWAIT_GO      | . | e | s | . | G | . | . | J | J | x |
# 4 RUNNING       | . | . | . | . | . | T | . | . | . | x |
# 5 STOPPING      | . | T | . | . | . | . | . | . | . | x |
# 6 RETURNING     | . | Se| . | . | . | . | . | J | J | x |
# 7 JOG_FORWARD   | . | e | . | . | . | . | . | . | . | x |
# 8 JOG_BACKWARD  | . | e | . | . | . | . | . | . | . | x |
# 9 ERROR         | . | . | . | . | . | . | . | . | . | x |

# I - Inititialize
# E - Engage is on
# e - Engage is off
# S - Set becomes on
# s - Set becomes off
# J - Jog (forward or back) is on
# j - Jog is off
# G - Go is on
# R - Return is on
# x - An error occurs

# Output Matrix
#                  Mot Vol Brk Fwd Rev ELt GLt 
# ----------------+---+---+---+---+---+---+---+
# 0 STARTING      | . | . | E | . | . | X | X |
# 1 AWAIT_ENGAGE  | . | . | D | . | . | X | . |
# 2 AWAIT_SET     | . | . | D | . | . | . | . |
# 3 AWAIT_GO      | . | . | D | . | . | . | X |
# 4 RUNNING       | X | H | D | X | . | . | . |
# 5 STOPPING      | . | . | E | . | . | . | . |
# 6 RETURNING     | . | L | D | . | X | . | . |
# 7 JOG_FORWARD   | X | L | D | X | . | . | . |
# 8 JOG_BACKWARD  | X | L | D | . | X | . | . |
# 9 ERROR         | . | . | E | . | . | . | . |

# E - Brake engaged (power off)
# D - Brake disengaged (power on)
# X - On
# L - Low voltage
# H - High voltage

ACCEPTABLE_LATENCY = 0.1

def log(message):
    print(message)

def log_error(message):
    print(message)

# ------------------------------------------------------------------------------
class OMState(enum.Enum):
    # The state at startup.
    # Moves out of startup after all possible IO has been found and checked.
    STARTING = 0
    # Default state when the engage switch is NOT actively depressed
    AWAIT_ENGAGE = 1
    # State when engage is set and we're not jogging and we're not set
    AWAIT_SET = 2
    # State when we're engaged and set and not jogging
    AWAIT_GO = 3
    # Go has been pressed.  State transitions are time/sensor based
    RUNNING = 4
    # We disengage go line to motor and engage the braking
    # After some amount of time we assume/verify we're stopped
    # and then we go to await engage
    STOPPING = 5
    # The return button has been pressed
    RETURNING = 6
    # We're in the jogging state when jog forward and engage are on
    JOG_FORWARD = 7
    # We're in the jogging state when jog backward and engage are on
    JOG_BACKWARD = 8
    # Any error puts us in the error state which we don't leave
    ERROR = 9

class Motor:
    FREQUENCY = 500

    def __init__(self, forward_pin, backward_pin, pwm_pin):
        self.direction = gpiozero.Motor(forward_pin, backward_pin)
        self.speed = gpiozero.PWMOutputDevice(pwm_pin, frequency=Motor.FREQUENCY)

    def forward(self, speed):
        self.set_speed(speed)
        self.direction.forward(1)

    def backward(self, speed):
        self.set_speed(speed)
        self.direction.backward(1)

    def stop(self):
        self.speed.off()
        self.direction.forward(0)

    def is_stopped(self):
        return self.speed.value

    def set_speed(self, speed):
        assert 0.0 <= speed <= 1.0
        self.speed.value = speed

class Brake:
    def __init__(self, pin):
        self.brake_disengage = gpiozero.OutputDevice(pin)

    def engage(self):
        self.brake_disengage.off()

    def disengage(self):
        self.brake_disengage.on()

class Outputs:
    def __init__(self, config):
        # Outputs
        # Pins 12 and 13 are the two PWMs
        self.motor = Motor(
                config.motor_forward_pin(),
                config.motor_backward_pin(),
                config.motor_speed_pin()
        )
        self.brake = Brake(config.brake_pin())
        self.engage_led = gpiozero.LED(config.engage_led_pin())
        self.go_led = gpiozero.LED(config.go_led_pin())

class Inputs:
    def __init__(self, config):
        debounce_s = config.button_debounce_s()
        self.engage_button = gpiozero.Button(config.engage_button_pin(), bounce_time=debounce_s)
        self.go_button = gpiozero.Button(config.go_button_pin(), bounce_time=debounce_s)
        self.return_button = gpiozero.Button(config.return_button_pin(), bounce_time=debounce_s)
        self.jog_backward = gpiozero.Button(config.backward_button_pin(), bounce_time=debounce_s)
        self.jog_forward = gpiozero.Button(config.forward_button_pin(), bounce_time=debounce_s)

        # TODO: Determine whether this is a sane bounce_time
        #self.limit_sensor = gpiozero.DigitalInputDevice(config.limit_sensor_pin(), bounce_time=0.1)
        self.limit_sensor = gpiozero.Button(config.limit_sensor_pin(), bounce_time=0.1)
        # TODO: Determine whether this is a sane bounce_time
        #self.rotate_sensor = gpiozero.DigitalInputDevice(config.rotate_sensor_pin(), bounce_time=0.01)
        self.rotate_sensor = gpiozero.Button(config.rotate_sensor_pin(), bounce_time=0.01)
        self.estop_sensor = gpiozero.Button(config.estop_sensor_pin())

# ------------------------------------------------------------------------------
class Controller:
    def __init__(self, config):
        """
        Set defaults from configuration.
        """
        self.config = config
        self.outputs = Outputs(config)
        self.inputs = Inputs(config)
        self.state = OMState.STARTING
        self.position_m = None
        self.to_starting()

    def run(self):
        """
        At a high rate, perform reads and ticks.
        """
        print("Running...")
        while True:
            time.sleep(0.001)
            try:
                start = time.monotonic()
                self.tick()
                end = time.monotonic()
                if end - start > ACCEPTABLE_LATENCY:
                    self.error(f"Timeout due to latency: {end - start}")
            except Exception as e:
                self.error(f"Unhandled exception: {e}")

    def error(self, message):
        """
        Print a message if possible then shut down the system as thoroughly as possible and exit.
        """
        try:
            log_error(message)
        finally:
            self.state = OMState.ERROR
            self.outputs.brake.engage()
            self.outputs.motor.stop()
            time.sleep(0.1)
            sys.exit(2)

    # ----------------------------------------
    # Events
    def on_engage_activated(self):
        log("Event:	Engage Activated")
        if self.state == OMState.AWAIT_ENGAGE:
            self.from_await_engage_to_await_set()
        # It should not be possible to press the engage button in any other state
        else:
            self.error(f"Somehow the engage button was pressed while in state {self.state}")

    def on_engage_deactivated(self):
        log("Event:	Engage Deactivated")
        if self.state == OMState.AWAIT_SET:
            self.from_await_set_to_await_engage()
        elif self.state == OMState.AWAIT_GO:
            self.from_await_go_to_await_engage()
        elif self.state == OMState.RETURNING:
            self.from_returning_to_await_engage()
        elif self.state == OMState.JOG_FORWARD:
            self.from_jog_forward_to_await_engage()
        elif self.state == OMState.JOG_BACKWARD:
            self.from_jog_backward_to_await_engage()
        # These cases are special cases where we can release the engage button
        # without triggering anything bad happening.
        #
        # Put a different way, the engage button need only be held while the user
        # is initiating a movement or actively continuing one (jog).
        elif self.state in [OMState.RUNNING, OMState.STOPPING, OMState.RETURNING]:
            pass
        else:
            self.error(f"Somehow the engage button was released while in state {self.state}")

    # --------------------
    def on_limit_activated(self):
        log("Event:	Limit Activated")
        if self.state == OMState.STARTING:
            pass
        elif self.state == OMState.AWAIT_ENGAGE:
            # FIXME: Is this a possible state?  Momentum?  Pulling the line while on the tube?
            pass
        elif self.state == OMState.AWAIT_SET:
            self.from_await_set_to_await_go()
        elif self.state == OMState.RETURNING:
            self.from_returning_to_await_engage()
        elif self.state == OMState.JOG_BACKWARD:
            self.from_jog_backward_to_await_engage()
        elif self.state == OMState.JOG_FORWARD:
            self.from_jog_forward_to_await_engage()
        else:
            self.error(f"Somehow the limit was triggered while in state {self.state}")

    def on_limit_deactivated(self):
        log("Event:	Limit Deactivated")
        if self.state == OMState.AWAIT_GO:
            self.from_await_go_to_await_set()
        elif self.state == OMState.AWAIT_ENGAGE:
            # FIXME: Is this a possible state?  Manually goofing up the state?
            pass
        elif self.state == OMState.RUNNING:
            # Someone is about to have fun.
            pass
        elif self.state in [OMState.RUNNING, OMState.JOG_FORWARD, OMState.JOG_BACKWARD]:
            pass
        else:
            self.error(f"Somehow the limit was released while in state {self.state}")

    # --------------------
    def on_go_activated(self):
        log("Event:	Go Activated")
        if self.state == OMState.AWAIT_GO:
            self.from_await_go_to_running()
        elif self.state in [OMState.RUNNING, OMState.STOPPING, OMState.RETURNING]:
            # We allow and ignore go press when we're already going
            pass
        pass

    def on_go_deactivated(self):
        log("Event:	Go Deactivated")
        # TODO: Should anything happen when go is released?
        # Should we actually trigger the press on release?
        pass

    # --------------------
    def on_return_activated(self):
        log("Event:	Return Activated")
        if self.state == OMState.AWAIT_SET:
            self.from_await_set_to_returning()
        elif self.inputs.limit_sensor.value:
            log("Can't return when we're already returned.")
        elif self.state in [OMState.RUNNING, OMState.STOPPING, OMState.RETURNING]:
            # We allow and ignore return presses when we're already going
            pass

    def on_return_deactivated(self):
        log("Event:	Return Deactivated")
        # TODO: Should anything happen when return is released?
        # Should we actually trigger the press on release?
        pass

    # --------------------
    def on_estop_activated(self):
        self.error("E-Stop Press")

    def on_estop_deactivated(self):
        self.error("E-Stop Release")

    # --------------------
    def on_jog_backward_activated(self):
        log("Event:	Jog Backward Activated")
        if self.state == OMState.AWAIT_ENGAGE:
            log("Can't jog backward without engage set.")
        elif self.state == OMState.AWAIT_SET:
            self.from_await_set_to_jog_backward()
        elif self.state == OMState.AWAIT_GO:
            self.from_await_go_to_jog_backward()
        elif self.state in [OMState.RUNNING, OMState.STOPPING]:
            # Jog switch is ignored while running
            pass
        elif self.state == OMState.RETURNING:
            # TODO: Consider whether this is a good idea.
            # We allow the user to initiate a jog while returning
            # which allows jog without hitting the engage switch.
            #
            # When they release the jog, the system will brake
            # as it enters await_engage.  This too may be slightly
            # undesirable as it might be nice to have a grace period
            # wherein the user can jog forward, backward a bit until
            # they get to just where they want.
            self.from_returning_to_jog_backward()
        else:
            pass

    def on_jog_backward_deactivated(self):
        log("Event:	Jog Backward Deactivated")
        if self.state == OMState.JOG_BACKWARD:
            self.from_jog_backward_to_await_engage()
        # TODO: Consider with a brain that has had additional sleep.
        # If the user has engage depressed, starts jogging, and releases
        # engage, the system will be put into a safe state, but the jog
        # is still activated.  Releasing it should have no effect that releasing
        # engage didn't already have.
        else:
            #self.error(f"Unexpected jog backward release while in state {self.state}")
            pass

    # --------------------
    def on_jog_forward_activated(self):
        log("Event:	Jog Forward Activated")
        if self.state == OMState.AWAIT_ENGAGE:
            log("Can't jog forward without engage set.")
        elif self.state == OMState.AWAIT_SET:
            self.from_await_set_to_jog_forward()
        elif self.state == OMState.AWAIT_GO:
            self.from_await_go_to_jog_forward()
        elif self.state in [OMState.RUNNING, OMState.STOPPING]:
            # Jog switch is ignored while running
            pass
        elif self.state == OMState.RETURNING:
            # See notes in on_jog_backward_activated
            self.from_returning_to_jog_forward()
        else:
            pass

    def on_jog_forward_deactivated(self):
        log("Event:	Jog Forward Deactivated")
        if self.state == OMState.JOG_FORWARD:
            self.from_jog_forward_to_await_engage()
        # If the user has engage depressed, starts jogging, and releases
        # engage, the system will be put into a safe state, but the jog
        # is still activated.  Releasing it should have no effect that releasing
        # engage didn't already have.
        else:
            #self.error(f"Unexpected jog forward release while in state {self.state}")
            pass

    # --------------------
    def on_rotate_activated(self):
        log(f"Event:	Rotate Magnet On at {self.position_m}")
        if self.state == OMState.RUNNING:
            self.running_data.revolve()
        elif self.state == OMState.STOPPING:
            self.stopping_data.revolve()
        elif self.state == OMState.RETURNING:
            self.returning_data.revolve()
        elif self.state == OMState.JOG_FORWARD:
            self.jog_forward_data.revolve()
        elif self.state == OMState.JOG_BACKWARD:
            self.jog_backward_data.revolve()

    # --------------------
    def on_rotate_deactivated(self):
        log("Event:	Rotate Magnet Off")

    # ----------------------------------------
    def tick(self):
        """
        Implements the logic for state transitions at each tick.
        """
        action = {
            OMState.STARTING: self.do_starting,
            OMState.AWAIT_ENGAGE: self.do_await_engage,
            OMState.AWAIT_SET: self.do_await_set,
            OMState.AWAIT_GO: self.do_await_go,
            OMState.RUNNING: self.do_running,
            OMState.STOPPING: self.do_stopping,
            OMState.RETURNING: self.do_returning,
            OMState.JOG_FORWARD: self.do_jog_forward,
            OMState.JOG_BACKWARD: self.do_jog_backward,
            OMState.ERROR: self.do_error,
        }.get(self.state, self.error)()

    # ----------------------------------------
    # Implement each state
    def do_starting(self):
        if self.state != OMState.STARTING:
            self.error(f"Request to start in invalid state {self.state}")
        self.from_starting_to_await_engage()

    def do_await_engage(self):
        self.state = OMState.AWAIT_ENGAGE
        self.outputs.engage_led.on()

    def do_await_set(self):
        pass

    def do_await_go(self):
        pass

    def do_running(self):
        self.running_data.tick()

    def do_stopping(self):
        self.stopping_data.tick()

    def do_returning(self):
        self.returning_data.tick()

    def do_jog_forward(self):
        self.jog_forward_data.tick()

    def do_jog_backward(self):
        self.jog_backward_data.tick()

    def do_error(self):
        # FIXME: Why does this ever trigger?
        self.error("Found running in error state")

    # ----------------------------------------------------------
    def setup_events(self):
        self.inputs.engage_button.when_activated = self.on_engage_activated
        self.inputs.engage_button.when_deactivated = self.on_engage_deactivated

        self.inputs.go_button.when_activated = self.on_go_activated
        self.inputs.go_button.when_deactivated = self.on_go_deactivated

        self.inputs.return_button.when_activated = self.on_return_activated
        self.inputs.return_button.when_deactivated = self.on_return_deactivated

        self.inputs.jog_backward.when_activated = self.on_jog_backward_activated
        self.inputs.jog_backward.when_deactivated = self.on_jog_backward_deactivated

        self.inputs.jog_forward.when_activated = self.on_jog_forward_activated
        self.inputs.jog_forward.when_deactivated = self.on_jog_forward_deactivated

        self.inputs.limit_sensor.when_activated = self.on_limit_activated
        self.inputs.limit_sensor.when_deactivated = self.on_limit_deactivated

        # This probably needs some special software debouncing
        self.inputs.rotate_sensor.when_activated = self.on_rotate_activated
        self.inputs.rotate_sensor.when_deactivated = self.on_rotate_deactivated

        self.inputs.estop_sensor.when_activated = self.on_estop_activated
        self.inputs.estop_sensor.when_deactivated = self.on_estop_deactivated

    # ----------------------------------------------------------
    # Each valid transition
    def to_starting(self):
        self.state = OMState.STARTING
        # Indicate startup by engaging both leds
        self.outputs.engage_led.on()
        self.outputs.go_led.on()
        self.setup_events()

    def from_starting(self):
        self.outputs.engage_led.off()
        self.outputs.go_led.off()

    # ----------------------------------------------------------
    def to_await_engage(self):
        self.state = OMState.AWAIT_ENGAGE
        self.outputs.motor.stop()
        self.outputs.brake.engage()
        self.outputs.engage_led.on()
        if self.inputs.engage_button.value:
            self.from_await_engage_to_await_set()

    def from_await_engage(self):
        # This should occur when the user begins holding down the engage
        # button.  This indicates that the system is free to begin movement.
        self.outputs.engage_led.off()
        self.outputs.brake.disengage()

    # ----------------------------------------------------------
    def to_await_set(self):
        self.state = OMState.AWAIT_SET
        self.position_m = 0.0
        self.outputs.go_led.blink(on_time=1.0, off_time=1.0)
        if self.inputs.limit_sensor.value:
            self.from_await_set_to_await_go()

    def from_await_set(self):
        self.outputs.go_led.off()

    # ----------------------------------------------------------
    def to_await_go(self):
        self.state = OMState.AWAIT_GO
        self.outputs.go_led.on()

    def from_await_go(self):
        self.outputs.go_led.off()

    # ----------------------------------------------------------
    def to_running(self):
        self.state = OMState.RUNNING

        length_m = self.config.accel_length_m()
        # FIXME: Should this be some large value?
        timeout_s = None
        pulley_diameter_m = self.config.pulley_diameter_m()
        self.running_data = Operation(length_m, timeout_s, pulley_diameter_m, self.from_running_to_stopping)

    def from_running(self):
        self.outputs.motor.stop()
        self.position_m += self.running_data.distance_m()
        print(f"Statistics for Run:")
        print(f"     Distance:	{self.running_data.distance_m()}m")
        print(f"     Duration:	{self.running_data.duration()}s")
        print(f"  Revolutions:	{self.running_data.revolutions()}")
        print(f"    Max Speed:	{self.running_data.max_speed_mps()}m/s")

    # ----------------------------------------------------------
    def to_stopping(self):
        self.state = OMState.STOPPING
        self.outputs.brake.engage()
        # Stop the motor for good measure
        self.outputs.motor.stop()

        # Reinitialize stopping data
        length_m = self.config.brake_length_m()
        # TODO: Should this be the config setting instead of brake_delay_s?
        timeout_s = 5.0
        pulley_diameter_m = self.config.pulley_diameter_m()
        self.stopping_data = Operation(length_m, timeout_s, pulley_diameter_m, self.from_stopping_to_await_engage)

    def from_stopping(self):
        self.position_m += self.stopping_data.distance_m()
        print(f"Statistics for Stop:")
        print(f"     Distance:	{self.stopping_data.distance_m()}m")
        print(f"     Duration:	{self.stopping_data.duration()}s")
        print(f"  Revolutions:	{self.stopping_data.revolutions()}")
        print(f"    Max Speed:	{self.stopping_data.max_speed_mps()}m/s")

    # ----------------------------------------------------------
    def to_returning(self):
        self.state = OMState.RETURNING
        self.outputs.motor.backward(self.config.return_speed_mps())

        # FIXME: This is probably insufficient for returning.
        # We may need a lot more smarts about going faster or slower at
        # different times to make this nice.
        # This implementation should do reasonable deceleration and so forth
        # May need to add some brake_delay time in here?
        length_m = self.config.accel_length_m()
        timeout_s = None
        pulley_diameter_m = self.config.pulley_diameter_m()
        self.returning_data = Operation(length_m, timeout_s, pulley_diameter_m, self.from_returning_to_await_engage)

    def from_returning(self):
        self.outputs.motor.stop()
        self.position_m -= self.returning_data.distance_m()
        print(f"Statistics for Return:")
        print(f"     Distance:	{self.returning_data.distance_m()}m")
        print(f"     Duration:	{self.returning_data.duration()}s")
        print(f"  Revolutions:	{self.returning_data.revolutions()}")
        print(f"    Max Speed:	{self.returning_data.max_speed_mps()}m/s")

    # ----------------------------------------------------------
    def to_jog_forward(self):
        self.state = OMState.JOG_FORWARD
        self.outputs.motor.forward(self.config.jog_speed_mps())

        # TODO:
        # Note that this won't stop you from going too far.
        length_m = self.config.length_m()
        timeout_s = None
        pulley_diameter_m = self.config.pulley_diameter_m()
        self.jog_forward_data = Operation(length_m, timeout_s, pulley_diameter_m, self.from_jog_forward_to_await_engage)

    def from_jog_forward(self):
        # Note: We don't put the brakes on
        self.outputs.motor.stop()
        self.position_m += self.jog_forward_data.distance_m()
        print(f"Statistics for Jog Forward:")
        print(f"     Distance:	{self.jog_forward_data.distance_m()}m")
        print(f"     Duration:	{self.jog_forward_data.duration()}s")
        print(f"  Revolutions:	{self.jog_forward_data.revolutions()}")
        print(f"    Max Speed:	{self.jog_forward_data.max_speed_mps()}m/s")

    # ----------------------------------------------------------
    def to_jog_backward(self):
        self.state = OMState.JOG_BACKWARD
        self.outputs.motor.backward(self.config.jog_speed_mps())

        # TODO:
        # Note that this won't stop you from going too far.
        length_m = self.config.length_m()
        timeout_s = None
        pulley_diameter_m = self.config.pulley_diameter_m()
        self.jog_backward_data = Operation(length_m, timeout_s, pulley_diameter_m, self.from_jog_backward_to_await_engage)
    def from_jog_backward(self):
        # Note: We don't put the brakes on
        self.outputs.motor.stop()
        self.position_m -= self.jog_backward_data.distance_m()
        print(f"Statistics for Jog Backward:")
        print(f"     Distance:	{self.jog_backward_data.distance_m()}m")
        print(f"     Duration:	{self.jog_backward_data.duration()}s")
        print(f"  Revolutions:	{self.jog_backward_data.revolutions()}")
        print(f"    Max Speed:	{self.jog_backward_data.max_speed_mps()}m/s")

    # ----------------------------------------------------------
    def from_starting_to_await_engage(self):
        log("State:	starting	->	await_engage")
        self.from_starting()
        self.to_await_engage()

    def from_await_engage_to_await_set(self):
        log("State:	await_engage	->	await_set")
        self.from_await_engage()
        self.to_await_set()

    def from_await_set_to_await_engage(self):
        log("State:	await_set	->	await_engage")
        self.from_await_set()
        self.to_await_engage()

    def from_await_set_to_await_go(self):
        log("State:	await_set	->	await_go")
        self.from_await_set()
        self.to_await_go()

    def from_await_set_to_returning(self):
        log("State:	await_set	->	returning")
        self.from_await_set()
        self.to_returning()

    def from_await_set_to_jog_forward(self):
        log("State:	await_set	->	jog_forward")
        self.from_await_set()
        self.to_jog_forward()

    def from_await_set_to_jog_backward(self):
        log("State:	await_set	->	jog_backward")
        self.from_await_set()
        self.to_jog_backward()

    def from_await_go_to_await_engage(self):
        log("State:	await_go	->	await_engage")
        self.from_await_go()
        self.to_await_engage()

    def from_await_go_to_await_set(self):
        log("State:	await_go	->	await_set")
        # This is an unusual transition because it would need to be caused
        # by the limit sensor becoming unset while the motor is not moving
        # the machine.
        # TODO: self.log...
        self.from_await_go()
        self.to_await_set()

    def from_await_go_to_running(self):
        log("State:	await_go	->	running")
        self.from_await_go()
        self.to_running()

    def from_await_go_to_jog_forward(self):
        log("State:	await_go	->	jog_forward")
        self.from_await_go()
        self.to_jog_forward()

    def from_await_go_to_jog_backward(self):
        log("State:	await_go	->	jog_backward")
        self.from_await_go()
        self.to_jog_backward()

    def from_running_to_stopping(self):
        log("State:	running 	->	stopping")
        self.from_running()
        self.to_stopping()

    def from_stopping_to_await_engage(self):
        log("State:	stopping	->	await_engage")
        self.from_stopping()
        self.to_await_engage()

    def from_returning_to_await_engage(self):
        log("State:	returning	->	await_engage")
        self.from_returning()
        self.to_await_engage()

    #!def from_returning_to_await_go(self):
    #!    log("State:	returning	->	await_go")
    #!    self.from_returning()
    #!    self.to_await_go()

    def from_returning_to_jog_forward(self):
        log("State:	returning	->	jog_forward")
        self.from_returning()
        self.to_jog_forward()

    def from_returning_to_jog_backward(self):
        log("State:	returning	->	jog_backward")
        self.from_returning()
        self.to_jog_backward()

    def from_jog_forward_to_await_engage(self):
        log("State:	jog_forward	->	await_engage")
        self.from_jog_forward()
        self.to_await_engage()

    def from_jog_backward_to_await_engage(self):
        log("State:	jog_back	->	await_engage")
        self.from_jog_backward()
        self.to_await_engage()

