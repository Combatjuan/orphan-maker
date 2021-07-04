#!/usr/bin/env python3
import argparse
import gpiozero
import time
from signal import pause

from om_config import Config
from om_inputs import Inputs

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
def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("config_file", type=str, nargs='?', default="default.ini",
            help="Config file to use for settings")
    return parser.parse_args()

# ------------------------------------------------------------------------------
def main():
    args = parse_args()
    config = Config(args.config_file)

    # Instantiate and run until force close
    inputs = Inputs(config)
    outputs = Outputs(config)

    def lights_on():
        print("Lights on")
        outputs.engage_led.on()
        outputs.go_led.on()

    def lights_off():
        print("Lights off")
        outputs.engage_led.off()
        outputs.go_led.off()

    def brakes_on():
        print("Brakes on")
        outputs.brake.engage()

    def brakes_off():
        print("Brakes off")
        outputs.brake.disengage()

    def on_return():
        print("Return")
        brakes_on()

    def on_engage():
        print("Engage")
        lights_on()

    def on_go():
        print("Go")
        lights_on()

    def on_jog_forward():
        print("Jog Forward")
        lights_on()

    def on_jog_backward():
        print("Backward")
        lights_on()

    def on_estop():
        print("Estop")
        lights_on()

    def on_limit():
        print("Limit")
        lights_on()

    def forward():
        outputs.go_led.on()
        outputs.brake.disengage()
        outputs.motor.forward()

    def backward():
        outputs.go_led.on()
        outputs.brake.disengage()
        outputs.motor.backward()

    def stop():
        outputs.go_led.off()
        outputs.motor.stop()
        outputs.brake.engage()

    print("Setting up callbacks...")
    inputs.return_button.when_pressed = on_return
    inputs.return_button.when_released = stop

    inputs.engage_button.when_pressed = on_engage
    inputs.engage_button.when_released = lights_off

    inputs.go_button.when_pressed = on_go
    inputs.go_button.when_released = lights_off

    inputs.limit_sensor.when_pressed = on_limit
    inputs.limit_sensor.when_released = lights_off

    inputs.jog_backward.when_pressed = backward
    inputs.jog_backward.when_released = stop

    inputs.jog_forward.when_pressed = forward
    inputs.jog_forward.when_released = stop

    inputs.estop_button.when_pressed = on_estop
    inputs.estop_button.when_released = lights_off

    #inputs.rotate_sensor.when_pressed = lights_on
    #inputs.rotate_sensor.when_released = lights_off

    print("Motor Forward Pin:", config.motor_forward_pin())
    print("Motor Backward Pin:", config.motor_backward_pin())

    try:
        print("Ready")
        while True:
            print("Motor:", outputs.motor.direction())
            time.sleep(0.1)
        print("End")
    except (KeyboardInterrupt, SystemExit) as e:
        print("Keyboard interupt caught.  Stopping.")
        inputs.stop()
# ------------------------------------------------------------------------------
if __name__ == '__main__':
    main()

