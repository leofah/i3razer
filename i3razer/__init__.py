#!/usr/bin/python3

import logging
import os
from argparse import ArgumentParser

from i3razer.i3_razer import I3Razer, ConfigParser
from i3razer.map_layout import map_layout

__all__ = [
    "I3Razer",
    "ConfigParser",
    "main",
    "__version__",
]

__version__ = "0.1.dev1"


def main():
    # Arguments
    parser = ArgumentParser()
    parser.add_argument("--version", help="Display version information and exit", action="store_true")
    parser.add_argument("--map", help="Map keyboard layout of connected Razer keyboards", action="store_true")

    default_config = os.path.join(os.path.dirname(__file__), "example_config.yaml")
    parser.add_argument("-c", "--config", default=default_config, help="Config file")
    parser.add_argument("-l", "--layout", help="Keyboard layout for colored keys. Usually detected automatically")
    parser.add_argument("-v", help="Be more verbose", action="count", default=0)

    args = parser.parse_args()

    # only output version
    if args.version:
        print(f"i3 razer version {__version__}")
        exit()

    # map a new layout
    if args.map:
        map_layout()
        exit()

    # set verbosity
    if args.v >= 3:
        level = logging.DEBUG
    elif args.v == 2:
        level = logging.INFO
    elif args.v == 1:
        level = logging.WARNING
    else:
        level = logging.ERROR
    logging.basicConfig(format="%(message)s", level=level)

    # start
    i3razer = I3Razer(config_file=args.config, layout=args.layout)
    i3razer.start()


if __name__ == "__main__":
    main()
