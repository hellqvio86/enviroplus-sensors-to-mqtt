"""
args handler
"""
import os
import argparse

from .config import parse_config


def args_handler(*, config_file: str = None) -> dict:
    """
    Function for reading arguments and config file

    Returns
    dict - config
    """
    parser = argparse.ArgumentParser()
    parser.add_argument("--username", type=str, required=False)
    parser.add_argument("--password", type=str, required=False)
    parser.add_argument("--host", type=str, required=False)
    parser.add_argument("--port", type=str, required=False)
    parser.add_argument("--topics", type=str, required=False)
    parser.add_argument("--config_file", type=str, required=False)
    parser.add_argument("--log_file", type=str, required=False)
    parser.add_argument("--pid_file", type=str, required=False)
    parser.add_argument("-D", "--debug", action="store_true")
    parser.add_argument("--daemon", action="store_true")
    args = parser.parse_args()

    if "config_file" in args and args.config_file:
        config = parse_config(config_file=args.config_file)
    elif os.path.exists("/etc/enviroplussensorstomqtt.yaml"):
        config = parse_config(config_file="/etc/enviroplussensorstomqtt.yaml")
    elif config_file:
        config = parse_config(config_file=config_file)
    else:
        config = parse_config()

    if "username" in args and args.username:
        config["username"] = args.username

    if "password" in args and args.password:
        config["password"] = args.password

    if "host" in args and args.host:
        config["host"] = args.host

    if "port" in args and args.port:
        config["port"] = int(args.port)

    if "debug" in args and args.debug:
        config["debug"] = True

    if "log_file" in args and args.log_file:
        config["log_file"] = args.log_file

    if "pid_file" in args and args.pid_file:
        config["pid_file"] = args.pid_file

    if "daemon" in args and args.daemon:
        config["daemon"] = args.daemon

    if "topics" in args and args.topics:
        config["topics"] = [item.strip() for item in args.topics.split(",")]

    if config["debug"]:
        print(f"config: {config}")

    return config
