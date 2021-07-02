#!/usr/bin/env python3
import gpiozero
from signal import pause

class Pins:
    def lights_on(self):
        self.motor.on()
        self.brake_disengage.on()
        self.engage_led.on()
        self.go_led.on()
        self.motor_forward.on()
        self.motor_reverse.on()

    def lights_off(self):
        self.motor.off()
        self.brake_disengage.off()
        self.engage_led.off()
        self.go_led.off()
        self.motor_forward.off()
        self.motor_reverse.off()

    def __init__(self):
        # Outputs
        # 23, 22, 12(PWM)
        self.motor = gpiozero.PWMLED(12)
        self.motor_forward = gpiozero.LED(23)
        self.motor_reverse = gpiozero.LED(22)
        # 24
        self.brake_disengage = gpiozero.LED(24)
        # 6
        self.engage_led = gpiozero.LED(6)
        # 27
        self.go_led = gpiozero.LED(27)

        # Inputs
        # 26
        self.engage_button = gpiozero.Button(26)
        self.engage_button.when_pressed = self.lights_on
        self.engage_button.when_released = self.lights_off
        # 16
        self.go_button = gpiozero.Button(16)
        self.go_button.when_pressed = self.lights_on
        self.go_button.when_released = self.lights_off
        # 13 (PWM)
        self.return_button = gpiozero.Button(13)
        self.return_button.when_pressed = self.lights_on
        self.return_button.when_released = self.lights_off
        # 5
        self.limit_sensor = gpiozero.Button(5)
        self.limit_sensor.when_pressed = self.lights_on
        self.limit_sensor.when_released = self.lights_off
        # 17
        self.jog_reverse = gpiozero.Button(17)
        self.jog_reverse.when_pressed = self.lights_on
        self.jog_reverse.when_released = self.lights_off
        # 18
        self.jog_forward = gpiozero.Button(18)
        self.jog_forward.when_pressed = self.lights_on
        self.jog_forward.when_released = self.lights_off
        # 20
        self.rotation_sensor = gpiozero.Button(20)
        self.rotation_sensor.when_pressed = self.lights_on
        self.rotation_sensor.when_released = self.lights_off
        # 21
        self.estop_sensor = gpiozero.Button(21)
        self.estop_sensor.when_pressed = self.lights_on
        self.estop_sensor.when_released = self.lights_off

# Instantiate and run until force close
pins = Pins()
pause()
