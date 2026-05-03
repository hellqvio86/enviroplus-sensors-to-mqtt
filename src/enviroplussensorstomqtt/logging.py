"""
Logging module
"""
import logging

def setup_logger(*, debug: bool = False, daemon: bool = False) -> None:
    """
    Setup logger
    """
    root = logging.getLogger()

    formatter = logging.Formatter(
        "%(asctime)s %(process)d %(processName)-10s %(name)-8s %(funcName)-8s %(levelname)-8s %(message)s"
    )

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    root.addHandler(console_handler)

    if debug:
        root.setLevel(logging.DEBUG)
    else:
        root.setLevel(logging.INFO)
