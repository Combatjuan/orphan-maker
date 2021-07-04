import enum
import functools
import sys
import threading
import time

import gpiozero

from om_period import Period
from om_inputs import Inputs

# ------------------------------------------------------------------------------
# State Transition Matrix
# From             0S  1AE 2AS 3AG 4RU 5ST 7JF 8JR 9ER
# ----------------+---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+
# 0 STARTING      | . | I | . | . | . | . | . | . | x |
# 1 SAFE          | . | . | E | . | . | . | . | . | x |
# 2 AWAIT_SET     | . | e | . | S | . | . | J | J | x |
# 3 AWAIT_GO      | . | e | s | . | G | . | J | J | x |
# 4 RUNNING       | . | . | . | . | . | T | . | . | x |
# 5 STOPPING      | . | T | . | . | . | . | . | . | x |
# 7 JOG_FORWARD   | . | e | . | . | . | . | . | . | x |
# 8 JOG_BACKWARD  | . | e | . | . | . | . | . | . | x |
# 9 ERROR         | . | . | . | . | . | . | . | . | x |

# I - Inititialize
# E - Engage is on
# e - Engage is off
# S - Set becomes on
# s - Set becomes off
# J - Jog (forward or back) is on
# j - Jog is off
# G - Go is on
# x - An error occurs

# Output Matrix
#                  Mot Vol Brk Fwd Rev ELt GLt 
# ----------------+---+---+---+---+---+---+---+
# 0 STARTING      | . | . | E | . | . | X | X |
# 1 SAFE          | . | . | D | . | . | X | . |
# 2 AWAIT_SET     | . | . | D | . | . | . | . |
# 3 AWAIT_GO      | . | . | D | . | . | . | X |
# 4 RUNNING       | X | H | D | X | . | . | . |
# 5 STOPPING      | . | . | E | . | . | . | . |
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
    # Ensures brake is set and motor is off
    SAFE = 1
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
    # We're in the jogging state when jog forward and engage are on
    JOG_FORWARD = 7
    # We're in the jogging state when jog backward and engage are on
    JOG_BACKWARD = 8
    # Any error puts us in the error state which we don't leave
    ERROR = 9

class Motor:
    FREQUENCY = 500

    def __init__(self, forward_pin, backward_pin):
        self._forward_button = gpiozero.DigitalOutputDevice(forward_pin)
        self._backward_button = gpiozero.DigitalOutputDevice(backward_pin)

    def forward(self):
        self._forward_button.on()
        self._backward_button.off()

    def backward(self):
        self._backward_button.on()
        self._forward_button.off()

    def direction(self):
        if self._forward_button.value:
            return 1
        if self._backward_button.value:
            return -1
        else:
            return 0

    def stop(self):
        self._forward_button.off()
        self._backward_button.off()

    def is_stopped(self):
        return not (self._forward_button.value or self._backward_button.value)

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
        )
        self.brake = Brake(config.brake_pin())
        self.engage_led = gpiozero.LED(config.engage_led_pin())
        self.go_led = gpiozero.LED(config.go_led_pin())

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
        # Sentinel for we don't know
        self.position_m = None
        self.rlock = threading.RLock()
        with self.rlock:
            self.to_starting()

    def log_period(self, period, name):
        position = "Unknown" if self.position_m is None else f"{self.position_m}m"
        print(f"Statistics for {name}:")
        print(f"     Duration:	{period.duration()}s")

    def run(self):
        """
        At a high rate, perform reads and ticks.
        """
        log("MAIN LOOP...")
        try:
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
        except (KeyboardInterrupt, SystemExit) as e:
            print(e)
            print("Exiting.")
            self.inputs.stop()

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
        with self.rlock:
            log("Event:	Engage Activated")
            if self.state == OMState.SAFE:
                self.from_safe_to_await_set()
            elif self.state in [OMState.RUNNING, OMState.STOPPING]:
                pass
            # It should not be possible to press the engage button in any other state
            else:
                self.error(f"Somehow the engage button was pressed while in state {self.state}")

    def on_engage_deactivated(self):
        with self.rlock:
            log("Event:	Engage Deactivated")
            if self.state == OMState.AWAIT_SET:
                self.from_await_set_to_safe()
            elif self.state == OMState.AWAIT_GO:
                self.from_await_go_to_safe()
            elif self.state == OMState.JOG_FORWARD:
                self.from_jog_forward_to_safe()
            elif self.state == OMState.JOG_BACKWARD:
                self.from_jog_backward_to_safe()
            # These cases are special cases where we can release the engage button
            # without triggering anything bad happening.
            #
            # Put a different way, the engage button need only be held while the user
            # is initiating a movement or actively continuing one (jog).
            elif self.state in [OMState.RUNNING, OMState.STOPPING]:
                pass
            else:
                log(f"Warn: Somehow the engage button was released while in state {self.state}")

    # --------------------
    def on_limit_activated(self):
        with self.rlock:
            log("Event:	Limit Activated")
            if self.state == OMState.STARTING:
                pass
            elif self.state == OMState.SAFE:
                # FIXME: Is this a possible state?  Momentum?  Pulling the line while on the tube?
                pass
            elif self.state == OMState.AWAIT_SET:
                self.from_await_set_to_await_go()
            elif self.state == OMState.JOG_BACKWARD:
                self.from_jog_backward_to_safe()
            elif self.state == OMState.JOG_FORWARD:
                self.from_jog_forward_to_safe()
            else:
                self.error(f"Somehow the limit was triggered while in state {self.state}")

    def on_limit_deactivated(self):
        with self.rlock:
            log("Event:	Limit Deactivated")
            if self.state == OMState.AWAIT_GO:
                self.from_await_go_to_await_set()
            elif self.state == OMState.SAFE:
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
        with self.rlock:
            log("Event:	Go Activated")
            if self.state == OMState.AWAIT_GO:
                self.from_await_go_to_running()
            elif self.state in [OMState.RUNNING, OMState.STOPPING]:
                # We allow and ignore go press when we're already going
                pass
            pass

    def on_go_deactivated(self):
        with self.rlock:
            log("Event:	Go Deactivated")
            # TODO: Should anything happen when go is released?
            # Should we actually trigger the press on release?
            pass

    # --------------------
    def on_estop_activated(self):
        self.error("E-Stop Press")

    def on_estop_deactivated(self):
        self.error("E-Stop Release")

    # --------------------
    def on_jog_backward_activated(self):
        with self.rlock:
            log("Event:	Jog Backward Activated")
            if self.inputs.limit_sensor.value:
                log("Warn:  Ignoring jog backward request due to limit switch")
            else:
                if self.state == OMState.SAFE:
                    log("Warn:  Can't jog backward without engage set.")
                elif self.state == OMState.AWAIT_SET:
                    self.from_await_set_to_jog_backward()
                elif self.state == OMState.AWAIT_GO:
                    self.from_await_go_to_jog_backward()
                elif self.state in [OMState.RUNNING, OMState.STOPPING]:
                    # Jog switch is ignored while running
                    pass
                else:
                    pass

    def on_jog_backward_deactivated(self):
        with self.rlock:
            log("Event:	Jog Backward Deactivated")
            if self.state == OMState.JOG_BACKWARD:
                self.from_jog_backward_to_safe()
            # TODO: Consider with a brain that has had additional sleep.
            # If the user has engage depressed, starts jogging, and releases
            # engage, the system will be put into a safe state, but the jog
            # is still activated.  Releasing it should have no effect that releasing
            # engage didn't already have.
            else:
                log("Warn:  System wasn't in jog_backward state when jog released")
                #self.error(f"Unexpected jog backward release while in state {self.state}")
                pass

    # --------------------
    def on_jog_forward_activated(self):
        with self.rlock:
            log("Event:	Jog Forward Activated")
            if self.state == OMState.SAFE:
                log("Warn:  Can't jog forward without engage set.")
            elif self.state == OMState.AWAIT_SET:
                self.from_await_set_to_jog_forward()
            elif self.state == OMState.AWAIT_GO:
                self.from_await_go_to_jog_forward()
            elif self.state in [OMState.RUNNING, OMState.STOPPING]:
                # Jog switch is ignored while running
                pass
            else:
                pass

    def on_jog_forward_deactivated(self):
        with self.rlock:
            log("Event:	Jog Forward Deactivated")
            if self.state == OMState.JOG_FORWARD:
                self.from_jog_forward_to_safe()
            # If the user has engage depressed, starts jogging, and releases
            # engage, the system will be put into a safe state, but the jog
            # is still activated.  Releasing it should have no effect that releasing
            # engage didn't already have.
            else:
                log("Warn:  System wasn't in jog_forward state when jog released")
                #self.error(f"Unexpected jog forward release while in state {self.state}")

    # ----------------------------------------
    def tick(self):
        """
        Implements the logic for state transitions at each tick.
        """
        with self.rlock:
            action = {
                OMState.STARTING: self.do_starting,
                OMState.SAFE: self.do_safe,
                OMState.AWAIT_SET: self.do_await_set,
                OMState.AWAIT_GO: self.do_await_go,
                OMState.RUNNING: self.do_running,
                OMState.STOPPING: self.do_stopping,
                OMState.JOG_FORWARD: self.do_jog_forward,
                OMState.JOG_BACKWARD: self.do_jog_backward,
                OMState.ERROR: self.do_error,
            }.get(self.state, self.error)()

    # ----------------------------------------
    # Implement each state
    def do_starting(self):
        if self.state != OMState.STARTING:
            self.error(f"Request to start in invalid state {self.state}")
        self.from_starting_to_safe()

    def do_safe(self):
        self.state = OMState.SAFE
        self.outputs.engage_led.on()

    def do_await_set(self):
        pass

    def do_await_go(self):
        pass

    def do_running(self):
        self.running_data.tick()

    def do_stopping(self):
        self.stopping_data.tick()

    def do_jog_forward(self):
        pass

    def do_jog_backward(self):
        pass

    def do_error(self):
        # FIXME: Why does this ever trigger?
        self.error("Found running in error state")

    # ----------------------------------------------------------
    def setup_events(self):
        self.inputs.engage_button.when_pressed = self.on_engage_activated
        self.inputs.engage_button.when_released = self.on_engage_deactivated

        self.inputs.go_button.when_pressed = self.on_go_activated
        self.inputs.go_button.when_released = self.on_go_deactivated

        # FIXME: Disabled while no rotate sensor
        #self.inputs.return_button.when_pressed = self.on_return_activated
        #self.inputs.return_button.when_released = self.on_return_deactivated

        self.inputs.jog_backward.when_pressed = self.on_jog_backward_activated
        self.inputs.jog_backward.when_released = self.on_jog_backward_deactivated

        self.inputs.jog_forward.when_pressed = self.on_jog_forward_activated
        self.inputs.jog_forward.when_released = self.on_jog_forward_deactivated

        self.inputs.estop_button.when_pressed = self.on_estop_activated
        self.inputs.estop_button.when_released = self.on_estop_deactivated

        self.inputs.limit_sensor.when_pressed = self.on_limit_activated
        self.inputs.limit_sensor.when_released = self.on_limit_deactivated

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
    def to_safe(self):
        self.state = OMState.SAFE
        self.outputs.motor.stop()
        self.outputs.brake.engage()
        self.outputs.engage_led.on()
        if self.inputs.engage_button.value:
            self.from_safe_to_await_set()

    def from_safe(self):
        # This should occur when the user begins holding down the engage
        # button.  This indicates that the system is free to begin movement.
        self.outputs.engage_led.off()
        print("Brake disengage")
        self.outputs.brake.disengage()

    # ----------------------------------------------------------
    def to_await_set(self):
        self.state = OMState.AWAIT_SET
        self.outputs.go_led.blink(on_time=1.0, off_time=1.0)
        if self.inputs.limit_sensor.value:
            self.from_await_set_to_await_go()

    def from_await_set(self):
        self.outputs.go_led.off()

    # ----------------------------------------------------------
    def to_await_go(self):
        self.state = OMState.AWAIT_GO
        self.outputs.go_led.on()
        self.position_m = 0.0

    def from_await_go(self):
        self.outputs.go_led.off()

    # ----------------------------------------------------------
    def to_running(self):
        self.state = OMState.RUNNING
        self.outputs.motor.forward()

        timeout_s = self.config.run_time_s()
        # FIXME: Should this be some large value?
        self.running_data = Period(timeout_s, self.from_running_to_stopping)

    def from_running(self):
        self.outputs.motor.stop()
        self.log_period(self.running_data, "Run")
        print("Run logged")

    # ----------------------------------------------------------
    def to_stopping(self):
        print("To Stopping")
        self.state = OMState.STOPPING
        self.outputs.brake.engage()
        # Extra stop the motor for good measure
        self.outputs.motor.stop()

        # Reinitialize stopping data
        # TODO: Should this be the config setting instead of brake_delay_s?
        print("Get stop time")
        timeout_s = self.config.stop_time_s()
        print("Got it time")
        self.stopping_data = Period(timeout_s, self.from_stopping_to_safe)
        print("Stopping state initialized")

    def from_stopping(self):
        print("From Stopping")
        self.log_period(self.stopping_data, "Stop")

    # ----------------------------------------------------------
    def to_jog_forward(self):
        self.state = OMState.JOG_FORWARD
        self.outputs.motor.forward()

    def from_jog_forward(self):
        # Note: We don't put the brakes on
        self.outputs.motor.stop()

    # ----------------------------------------------------------
    def to_jog_backward(self):
        self.state = OMState.JOG_BACKWARD
        self.outputs.motor.backward()

    def from_jog_backward(self):
        # Note: We don't put the brakes on
        self.outputs.motor.stop()

    # ----------------------------------------------------------
    def from_starting_to_safe(self):
        with self.rlock:
            log("State:	starting	->	safe")
            self.from_starting()
            self.to_safe()

    def from_safe_to_await_set(self):
        with self.rlock:
            log("State:	safe	->	await_set")
            self.from_safe()
            self.to_await_set()

    def from_await_set_to_safe(self):
        with self.rlock:
            log("State:	await_set	->	safe")
            self.from_await_set()
            self.to_safe()

    def from_await_set_to_await_go(self):
        with self.rlock:
            log("State:	await_set	->	await_go")
            self.from_await_set()
            self.to_await_go()

    def from_await_set_to_jog_forward(self):
        with self.rlock:
            log("State:	await_set	->	jog_forward")
            self.from_await_set()
            self.to_jog_forward()

    def from_await_set_to_jog_backward(self):
        with self.rlock:
            log("State:	await_set	->	jog_backward")
            self.from_await_set()
            self.to_jog_backward()

    def from_await_go_to_safe(self):
        with self.rlock:
            log("State:	await_go	->	safe")
            self.from_await_go()
            self.to_safe()

    def from_await_go_to_await_set(self):
        with self.rlock:
            log("State:	await_go	->	await_set")
            # This is an unusual transition because it would need to be caused
            # by the limit sensor becoming unset while the motor is not moving
            # the machine.
            # TODO: self.log...
            self.from_await_go()
            self.to_await_set()

    def from_await_go_to_running(self):
        with self.rlock:
            log("State:	await_go	->	running")
            self.from_await_go()
            self.to_running()

    def from_await_go_to_jog_forward(self):
        with self.rlock:
            log("State:	await_go	->	jog_forward")
            self.from_await_go()
            self.to_jog_forward()

    def from_await_go_to_jog_backward(self):
        with self.rlock:
            log("State:	await_go	->	jog_backward")
            self.from_await_go()
            self.to_jog_backward()

    def from_running_to_stopping(self):
        with self.rlock:
            log("State:	running 	->	stopping")
            self.from_running()
            self.to_stopping()

    def from_stopping_to_safe(self):
        with self.rlock:
            log("State:	stopping	->	safe")
            self.from_stopping()
            self.to_safe()

    def from_jog_forward_to_safe(self):
        with self.rlock:
            log("State:	jog_forward	->	safe")
            self.from_jog_forward()
            self.to_safe()

    def from_jog_backward_to_safe(self):
        with self.rlock:
            log("State:	jog_back	->	safe")
            self.from_jog_backward()
            self.to_safe()

