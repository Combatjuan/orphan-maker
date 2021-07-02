#!/usr/bin/env python3
import argparse

from om_config import Config
from om_controller import Controller
from om_logger import Logger
from om_portal import Portal

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
    print(config)
    om = Controller(config)
    om.run()

# ------------------------------------------------------------------------------
if __name__ == '__main__':
    main()

