import gpiozero
import enum

# ------------------------------------------------------------------------------
# State Transition Matrix
#                  0S  1AE 2AS 3AG 4RU 5ST 6RT 7JG 9ER
# ----------------+---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+
# 0 STARTING      | . | I | . | . | . | . | . | . | x |
# 1 AWAIT_ENGAGE  | . | . | E | . | . | . | . | . | x |
# 2 AWAIT_SET     | . | e | . | S | . | . | R | J | x |
# 3 AWAIT_GO      | . | e | s | . | G | . | . | J | x |
# 4 RUNNING       | . | . | . | . | . | T | . | . | x |
# 5 STOPPING      | . | T | . | . | . | . | . | . | x |
# 6 RETURNING     | . | e | . | S | . | . | . | J | x |
# 7 JOGGING       | . | e | j | . | . | . | . | . | x |
# 9 ERROR         | . | . | . | . | . | . | . | . | x |

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
#                  Mot Vol Brk Fwd Rev ELt GLt RLt 
# ----------------+---+---+---+---+---+---+---+---+
# 0 STARTING      | . | . | E | . | . | X | X | X |
# 1 AWAIT_ENGAGE  | . | . | D | . | . | X | . | . |
# 2 AWAIT_SET     | . | . | D | . | . | . | . | X |
# 3 AWAIT_GO      | . | . | D | . | . | . | X | . |
# 4 RUNNING       | X | H | D | X | . | . | . | . |
# 5 STOPPING      | . | . | E | . | . | . | . | . |
# 6 RETURNING     | . | L | D | . | X | . | . | . |
# 7 JOGGING       | X | L | D | M | M | . | . | . |
# 9 ERROR         | . | . | E | . | . | . | . | . |

# E - Brake engaged (power off)
# D - Brake disengaged (power on)
# X - On
# L - Low voltage
# H - High voltage

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
    # We're in the jogging state when jogging and engage are on
    JOGGING = 7
    # Any error puts us in the error state which we don't leave
    ERROR = 9

# ------------------------------------------------------------------------------
class Controller:
    def __init__(self, config):
        """
        Set defaults from configuration
        """
        self.state = OMState.STARTING
        self.config = config

    def run(self):
        """
        At a high rate, perform reads and ticks.
        """
        pass

    def read(self):
        """
        Set internal state based on actual IO (e.g. with gpiozero)
        """
        pass

    def tick(self):
        """
        Implements the logic for state transitions at each tick.
        """
        if self.state == OMState.STARTING:
            pass
        elif self.state == OMState.AWAIT_ENGAGE:
            pass
        elif self.state == OMState.AWAIT_SET:
            pass
        elif self.state == OMState.AWAIT_GO:
            pass
        elif self.state == OMState.RUNNING:
            pass
        elif self.state == OMState.STOPPING:
            pass
        elif self.state == OMState.RETURNING:
            pass
        elif self.state == OMState.JOGGING:
            pass
        elif self.state == OMState.ERROR:
            pass
        else:
            transition(self, OMState.ERROR)

    def transition(self, state):
        """
        Checks and implements state transitions.

        Should be called from tick.
        """
        pass

