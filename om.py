#!/usr/bin/env python3
import argparse

from om_config import Config
from om_controller import Controller
from om_logger import Logger
from om_portal import Portal

# ------------------------------------------------------------------------------
def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("-l", "--length", type=float, required=True,
            help="Length of the acceleration area in meters")
    parser.add_argument("-s", "--speed", type=float, required=True,
            help="Target max speed before braking.")
    return parser.parse_args()

# ------------------------------------------------------------------------------
def main():
    args = parse_args()
    print("Let's make some orphans!", args)
    om = Controller(length=args.length, speed=args.speed)
    om.run()

# ------------------------------------------------------------------------------
if __name__ == '__main__':
    main()

