#!/usr/bin/python3

from i3razer.i3_razer import I3Razer, ConfigParser
from i3razer.map_layout import map_layout

__all__ = [
    "I3Razer",
    "ConfigParser",
    "main",
    "__version__",
]

__version__ = "0.1"


def main():
    from i3razer.i3_razer import I3Razer
    from argparse import ArgumentParser
    import logging
    import os

    i3razer = None
    default_config = os.path.join(os.path.dirname(__file__), "example_config.yaml")

    # Arguments
    parser = ArgumentParser()
    parser.add_argument("--version", help="Display version information and exit", action="store_true")
    parser.add_argument("--map", help="Map keyboard layout of connected Razer keyboards", action="store_true")

    parser.add_argument("-c", "--config", default=default_config, help="Config file")
    parser.add_argument("-l", "--layout", help="Keyboard layout for colored keys. Usually detected automatically")
    # Daemonize not working ok with logger, and somehow doesn't start if not foreground=True
    # parser.add_argument("-b", "--background", help="Fork to the background", action="store_true")
    # parser.add_argument("--pid", help="Location of pid File if forking", default="/dev/null")
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

    # handle forking ?!
    # if args.background:
    #    # d = Daemonize(keep_fds=[0, 1, 2], app="i3razer", pid=args.pid, action=begin, logger=logging.getLogger(__name__))
    #    # logging.info("Forking to background")
    #    # d.start()
    # else:
    #     begin()


if __name__ == "__main__":
    main()
