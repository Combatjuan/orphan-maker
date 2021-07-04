import gpiozero
import time
import threading

PULL_UP=None
ACTIVE_STATE=True
DEBOUNCE_S=None

SLEEP=0.001
CONSECUTIVE=20

class OMButton:
    def __init__(self, pin, name, when_pressed=None, when_released=None, invert=False):
        self.pin = pin
        self.name = name
        self.invert = invert
        self.dev = gpiozero.DigitalInputDevice(pin,
                bounce_time=DEBOUNCE_S,
                pull_up=None,
                active_state=ACTIVE_STATE
        )

        # Buttons default to false
        self.value = 1 if invert else 0
        # If we get <consecutive> new values then we change
        # our value and fire a signal
        self.tracking_value = self.value
        self.consecutive = 0

        self.when_pressed = when_pressed
        self.when_released = when_released

    def tick(self):
        tick_value = self.dev.value
        if tick_value == self.tracking_value:
            self.consecutive += 1
            if self.consecutive >= CONSECUTIVE and tick_value != self.value:
                self.value = tick_value

                if self.invert:
                    if not self.value and self.when_pressed is not None:
                        print(f"Input: Pressed {self.name}")
                        self.when_pressed()
                    elif self.value and self.when_released is not None:
                        print(f"Input: Release {self.name}")
                        self.when_released()
                    else:
                        print("Input: Unhandled OMButton event", self.name, self.value)
                else:
                    if self.value and self.when_pressed is not None:
                        print(f"Input: Pressed {self.name}")
                        self.when_pressed()
                    elif not self.value and self.when_released is not None:
                        print(f"Input: Released {self.name}")
                        self.when_released()
                    else:
                        print("Input: Unhandled OMButton event", self.name, self.value)
        else:
            print(f"Signal: {tick_value} on {self.name}")
            self.tracking_value = tick_value
            self.consecutive = 0

class Inputs:
    def __init__(self, config):
        debounce_consecutive = config.debounce_consecutive()
        global CONSECUTIVE
        CONSECUTIVE = debounce_consecutive

        self.engage_button = OMButton(config.engage_button_pin(), 'engage')
        self.go_button = OMButton(config.go_button_pin(), 'go')
        self.return_button = OMButton(config.return_button_pin(), 'return')
        self.jog_backward = OMButton(config.backward_button_pin(), 'backward')
        self.jog_forward = OMButton(config.forward_button_pin(), 'forward')

        self.limit_sensor = OMButton(config.limit_sensor_pin(), 'limit')
        self.estop_button = OMButton(config.estop_button_pin(), 'estop', invert=True)

        self.buttons = [
            self.engage_button,
            self.go_button,
            self.return_button,
            self.jog_backward,
            self.jog_forward,

            self.limit_sensor,
            self.estop_button,
        ]

        self.thread = threading.Thread(target=self.run)
        self.thread.start()

    def stop(self):
        self.running = False
        self.thread.join()

    def run(self):
        self.running = True
        while self.running:
            time.sleep(SLEEP)
            for button in self.buttons:
                button.tick()                

