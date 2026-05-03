"""
Logging
"""
import logging
import logging.handlers


def setup_logger(
    *,
    debug: bool = False,
    log_file: str = "/var/log/enviroplussensorstomqtt/enviroplussensorstomqtt.log",
    daemon: bool = False,
) -> logging.Logger:
    """
    Function for setting up logging
    """
    root = logging.getLogger()
    formatter = logging.Formatter(
        "%(asctime)s %(process)d %(processName)-10s %(name)-8s %(funcName)-8s %(levelname)-8s %(message)s"
    )

    if debug or daemon:
        file_handler = logging.handlers.RotatingFileHandler(
            log_file, "a", maxBytes=3 * 10**6, backupCount=10
        )
        file_handler.setFormatter(formatter)
        root.addHandler(file_handler)

    if daemon:
        root.setLevel(logging.INFO)
    elif debug:
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        root.addHandler(console_handler)
        root.setLevel(logging.DEBUG)
    else:
        root.setLevel(logging.INFO)

    return root
