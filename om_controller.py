import enum
import sys
import time

import gpiozero

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
# 6 RETURNING     | . | e | . | S | . | . | . | J | J | x |
# 7 FORWARD       | . | e | . | . | . | . | . | . | . | x |
# 8 BACKWARD      | . | e | . | . | . | . | . | . | . | x |
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
# 7 FORWARD       | X | L | D | X | . | . | . |
# 8 BACKWARD      | X | L | D | . | X | . | . |
# 9 ERROR         | . | . | E | . | . | . | . |

# E - Brake engaged (power off)
# D - Brake disengaged (power on)
# X - On
# L - Low voltage
# H - High voltage

ACCEPTABLE_LATENCY = 0.1

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
    def __init__(self, forward_pin, backward_pin, pwm_pin):
        self.direction = gpiozero.Motor(forward_pin, backward_pin)
        self.speed = gpiozero.PWMOutputDevice(pwm_pin)

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

    def set_speed(self):
        raise "Unimplemented"
        # TODO: Need to be able to do the conversion for speed

class Brake:
    def __init__(self, pin):
        self.brake_disengage = gpiozero.OutputDevice(pin)

    def engage(self):
        self.brake_disengage.off()

    def disengage(self):
        self.brake_disengage.on()

class Outputs:
    def __init__(self):
        # Outputs
        # Pins 12 and 13 are the two PWMs
        self.motor = Motor(23, 22, 12)
        self.brake = Brake(24)
        self.engage_led = gpiozero.LED(6)
        self.go_led = gpiozero.LED(27)

class Inputs:
    def __init__(self):
        self.engage_button = gpiozero.Button(26)
        self.go_button = gpiozero.Button(16)
        self.return_button = gpiozero.Button(13)
        self.limit_sensor = gpiozero.DigitalInputDevice(5)
        self.jog_backward = gpiozero.Button(17)
        self.jog_forward = gpiozero.Button(18)
        self.rotation_sensor = gpiozero.DigitalInputDevice(20)
        self.estop_sensor = gpiozero.Button(21)

# ------------------------------------------------------------------------------
class RunningData:
    def __init(self):
        self.start_time = time.monotonic()
        self.revolutions = 0.0
        self.distance = 0.0
        # TODO: Set up a Kalman filter or something to try and keep track of position

class StoppingData:
    def __init(self):
        self.start_time = time.monotonic()
        self.revolutions = 0.0
        self.distance = 0.0
        # TODO: Set up a Kalman filter or something to try and keep track of position

    def duration(self):
        return time.monotonic() - self.start_time

class ReturningData:
    def __init(self):
        self.start_time = time.monotonic()
        self.revolutions = 0.0
        self.distance = 0.0
        # TODO: Set up a Kalman filter or something to try and keep track of position

    def duration(self):
        return time.monotonic() - self.start_time

# ------------------------------------------------------------------------------
class Controller:
    def __init__(self, config):
        """
        Set defaults from configuration
        """
        self.config = config
        self.outputs = Outputs()
        self.inputs = Inputs()
        self.state = OMState.STARTING
        self.to_starting()

    def run(self):
        """
        At a high rate, perform reads and ticks.
        """
        while True:
            time.sleep(0.001)
            try:
                start = time.monotonic()
                self.tick()
                end = time.monotonic()
                if end - start > ACCEPTABLE_LATENCY:
                    self.error(f"Timeout due to latency: {end - start}")
            except:
                self.error("Bad things happened")

    def error(self, message):
        """
        Print a message if possible then shut down the system as thoroughly as possible and exit.
        """
        try:
            self.log.error(message)
        finally:
            self.state = OMState.ERROR
            self.outputs.brake.engage()
            self.outputs.motor.stop()
            time.sleep(0.1)
            sys.exit(2)

    # ----------------------------------------
    # Events
    def on_engage_press(self):
        pass

    def on_engage_release(self):
        pass

    # --------------------
    def on_go_press(self):
        pass

    def on_go_release(self):
        pass

    # --------------------
    def on_return_press(self):
        pass

    def on_return_release(self):
        pass

    # --------------------
    def on_estop_press(self):
        pass

    def on_estop_release(self):
        pass

    # --------------------
    def on_backward_press(self):
        pass

    def on_backward_release(self):
        pass

    # --------------------
    def on_forward_press(self):
        pass

    def on_forward_release(self):
        pass

    # --------------------
    def on_limit_press(self):
        pass

    def on_limit_release(self):
        pass

    # --------------------
    def on_rotate(self):
        pass

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

    def do_await_engage(self):
        self.state = OMState.AWAIT_ENGAGE
        self.outputs.engage_led.on()

    # ----------------------------------------
    # Each valid transition
    def to_starting(self):
        # Indicate startup by engaging both leds
        self.outputs.engage_led.on()
        self.outputs.go_led.on()

    def from_starting(self):
        self.outputs.engage_led.off()
        self.outputs.go_led.off()

    # ----------------------------------------------------------
    def to_await_engage(self):
        self.outputs.motor.stop()
        self.outputs.brake.engage()
        self.outputs.engage_led.on()

    def from_await_engage(self):
        # This should occur when the user begins holding down the engage
        # button.  This indicates that the system is free to begin movement.
        self.outputs.engage_led.off()
        self.outputs.brake.disengage()

    # ----------------------------------------------------------
    def to_await_set(self):
        self.outputs.go_led.blink(on_time=1.0, off_time=1.0)

    def from_await_set(self):
        self.outputs.go_led.off()

    # ----------------------------------------------------------
    def to_await_go(self):
        self.outputs.go_led.on()

    def from_await_go(self):
        self.outputs.go_led.off()

    # ----------------------------------------------------------
    def to_returning(self):
        self.return_data = ReturnData()

    def from_returning(self):
        self.outputs.motor.stop()

    # ----------------------------------------------------------
    def to_jog_forward(self):
        #self.outputs.motor.set_speed(config.max_jog_speed)
        self.outputs.motor.forward(config.max_jog_speed)

    def from_jog_forward(self):
        self.outputs.motor.stop()

    # ----------------------------------------------------------
    def to_jog_backward(self):
        #self.outputs.motor.set_speed(config.max_jog_speed)
        self.outputs.motor.backward(config.max_jog_speed)

    def from_jog_backward(self):
        self.outputs.motor.stop()

    # ----------------------------------------------------------
    def to_running(self):
        # Reinitialize running data
        self.running_data = RunningData()

    def from_running(self):
        self.outputs.motor.off()

    # ----------------------------------------------------------
    def to_stopping(self):
        # Reinitialize running data
        self.stopping_data = StoppingData()
        self.outputs.brake.engage()
        self.outputs.motor.off()

    def from_stopping(self):
        print(self.stopping_data)

    # ----------------------------------------------------------
    def to_jog_forward(self):
        self.outputs.brake.disengage()
        self.outputs.motor.set_speed(self.config.jog_speed_mps)

    def from_jog_forward(self):
        # Note: We don't put the brakes on
        pass

    # ----------------------------------------------------------
    def to_jog_backward(self):
        self.outputs.brake.disengage()
        self.outputs.motor.set_speed(self.config.jog_speed_mps)

    def from_jog_backward(self):
        # Note: We don't put the brakes on
        pass

    # ----------------------------------------------------------
    def from_starting_to_await_engage(self):
        self.from_starting()
        self.to_await_engage()

    def from_await_engage_to_await_set(self):
        self.from_await_engage()
        self.to_await_set()

    def from_await_set_to_await_engage(self):
        self.from_await_set()
        self.to_await_engage()

    def from_await_set_to_await_go(self):
        self.from_await_set()
        self.to_await_go()

    def from_await_set_to_returning(self):
        self.from_await_set()
        self.to_returning()

    def from_await_set_to_jog_forward(self):
        self.from_await_set()
        self.to_jog_forward()

    def from_await_set_to_jog_backward(self):
        self.from_await_set()
        self.to_jog_backward()

    def from_await_go_to_await_engage(self):
        self.from_wait_go()
        self.to_await_engage()

    def from_await_go_to_await_set(self):
        # This is an unusual transition because it would need to be caused
        # by the limit sensor becoming unset while the motor is not moving
        # the machine.
        # TODO: self.log...
        self.from_await_go()
        self.to_await_set()

    def from_await_go_to_running(self):
        self.from_await_go()
        self.to_running()

    def from_await_go_to_jog_forward(self):
        self.from_await_go()
        self.to_jog_forward()

    def from_await_go_to_jog_backward(self):
        self.from_await_go()
        self.to_jog_backward()

    def from_running_to_stopping(self):
        self.from_running()
        self.to_stopping()

    def from_stopping_to_await_engage(self):
        self.from_stopping()
        self.to_await_engage()

    def from_returning_to_await_engage(self):
        self.from_returning()
        self.to_await_engage()

    def from_returning_to_await_go(self):
        self.from_returning()
        self.to_await_go()

    def from_returning_to_jog_forward(self):
        self.from_returning()
        self.to_jog_forward()

    def from_jog_forward_to_await_engage(self):
        self.from_jog_forward()
        self.to_await_engage()

    def from_jog_backward_to_await_engage(self):
        self.from_jog_backward()
        self.to_await_engage()

    # ----------------------------------------------------------
    def transition(self, state):
        """
        Checks and implements state transitions.

        This is a doubley nested if structure with the outer block being the current
        state and the inner block being the requested new state.  Valid transitions
        will have specifically named functions for the transitions.  Any others
        are illegal and should error.

        While this is ugly, it is straightforward, keeps state centralized, and
        avoids some pretty awkward function calls to keep state in check.
        """
        # TODO: Make me a nice declarative set of nested maps.
        if self.state == OMState.STARTING:
            if state == OMState.AWAIT_ENGAGE:
                self.from_starting_to_await_engage()
            else:
                self.error(f"Attempt to transition from {self.state} to {state}")
        elif self.state == OMState.AWAIT_ENGAGE:
            if state == OMState.AWAIT_SET:
                self.from_await_engage_to_await_set()
            else:
                self.error(f"Attempt to transition from {self.state} to {state}")
        elif self.state == OMState.AWAIT_SET:
            if state == OMState.AWAIT_SET:
                self.from_await_set_to_await_engage()
            elif state == OMState.AWAIT_GO:
                self.from_await_set_to_await_go()
            elif state == OMState.RETURNING:
                self.from_await_set_to_returning()
            elif state == OMState.JOGGING:
                self.from_await_set_to_jogging()
            else:
                self.error(f"Attempt to transition from {self.state} to {state}")
        elif self.state == OMState.AWAIT_GO:
            if state == OMState.AWAIT_ENGAGE:
                self.from_await_go_to_await_engage()
            elif state == OMState.AWAIT_SET:
                self.from_await_go_to_await_set()
            elif state == OMState.RUNNING:
                self.from_await_go_to_running()
            elif state == OMState.JOGGING:
                self.from_await_go_to_jogging()
            else:
                self.error(f"Attempt to transition from {self.state} to {state}")
        elif self.state == OMState.RUNNING:
            if state == OMState.STOPPING:
                self.from_running_to_stopping()
            else:
                self.error(f"Attempt to transition from {self.state} to {state}")
        elif self.state == OMState.STOPPING:
            if state == OMState.AWAIT_ENGAGE:
                self.from_stopping_to_await_engage()
            else:
                self.error(f"Attempt to transition from {self.state} to {state}")
        elif self.state == OMState.RETURNING:
            if state == OMState.AWAIT_SET:
                self.from_returning_to_await_engage()
            elif state == OMState.AWAIT_GO:
                self.from_returning_to_await_go()
            elif state == OMState.JOGGING:
                self.from_returning_to_jogging()
            else:
                self.error(f"Attempt to transition from {self.state} to {state}")
        elif self.state == OMState.JOGGING:
            if state == OMState.AWAIT_ENGAGE:
                self.from_jogging_to_await_engage()
            else:
                self.error(f"Attempt to transition from {self.state} to {state}")
        elif self.state == OMState.ERROR:
            self.error("Transition to error state from {state}")
        else:
            self.error(f"Invalid state transition '{state}' requested")

