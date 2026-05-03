"""
Config module
"""
import os
import yaml

def parse_config(config_file="config.yaml"):
    """
    Read configuration
    """
    config = {}

    if not os.path.isfile(config_file):
        return config  # empty dict

    with open(config_file, "r") as stream:
        config = yaml.safe_load(stream)

    return config
