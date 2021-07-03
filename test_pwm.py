#!/usr/bin/env python3
import gpiozero
import sys
import time
from signal import pause

PERIOD = 10
STEPS = 100
FREQUENCY = int(sys.argv[1])
DUTY_CYCLE = float(sys.argv[2])

class Motor:
    def __init__(self, forward_pin, backward_pin, pwm_pin):
        self.direction = gpiozero.Motor(forward_pin, backward_pin)
        self.speed = gpiozero.PWMOutputDevice(pwm_pin, frequency=FREQUENCY)

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

class Pins:
    def go_forward(self):
        self.motor.forward(1.0)

    def go_backward(self):
        self.motor.backward(1.0)

    def stop(self):
        self.motor.stop()

    def __init__(self):
        # Outputs
        # 23, 22, 12(PWM)
        self.motor = Motor(22, 23, 12)

        # 17
        self.jog_backward = gpiozero.Button(17)
        self.jog_backward.when_pressed = self.go_backward
        self.jog_backward.when_released = self.stop
        # 18
        self.jog_forward = gpiozero.Button(18)
        self.jog_forward.when_pressed = self.go_forward
        self.jog_forward.when_released = self.stop

# Instantiate and run until force close
pins = Pins()

def set_speed(speed):
    pins.motor.set_speed(speed)


set_speed(DUTY_CYCLE)
pause()

while True:
    for i in range (0, STEPS):
        set_speed(float(i) / float(STEPS))
        time.sleep(float(PERIOD) / float(STEPS))
        print(i / float(STEPS))

    for i in range (STEPS, 0, -1):
        set_speed(float(i) / float(STEPS))
        time.sleep(float(PERIOD) / float(STEPS))
        print(i / float(STEPS))
