import logging
import os
import re
import sys

import psutil

_LOGGER = logging.getLogger(__name__)


class Daemonizer:
    """
    Class for Daemonizing a process
    """

    _pid_file = None

    def __init__(self, pid_file: str = None) -> None:
        """
        Constructor
        """
        self._pid_file = pid_file

        self.run()

    def run(self):
        """
        Run function
        """
        self.__background_process()
        self.__decouple()
        self.__background_process()
        self.__redirect()

        if self._pid_file:
            self.___setup_pidfile()


    def ___setup_pidfile(self):
        """
        Private function for setting up a pidfile
        """
        pid = os.getpid()

        _LOGGER.debug(f"Setting up pidfile for PID {pid} to {self._pid_file}")

        if os.path.isfile(self._pid_file):
            pid_desc = open(self._pid_file)

            pid = pid_desc.read()
            if re.match(r"^\d+$", pid):
                pid = int(pid)

            if psutil.pid_exists(pid):
                msg = f"Already running with pid {pid}"
                _LOGGER.error(msg)
                raise Exception(msg)

        pid_desc = open(self._pid_file, "w")

        pid_desc.write(f"{pid}")

        pid_desc.close()


    def __redirect(self):
        """
        Private function for redirecting stderr, stdout and
        stdin to /dev/null
        """
        sys.stdin.close()
        sys.stdin = open("/dev/null")

        sys.stdout.close()
        sys.stdout = open("/dev/null", "w")

        sys.stderr.close()
        sys.stderr = open("/dev/null", "w")


    def __decouple(self):
        """
        Private function for decoupling the process
        from its parent
        """
        self.__change_directory()

        self.__set_new_sid()
        self.__change_file_mode_mask()


    def __change_file_mode_mask(self):
        """
        Private function for changing the default
        file mask
        """
        _LOGGER.debug("Changing filemask to 0")

        os.umask(0)


    def __set_new_sid(self):
        """
        Private function for setting a new sid
        """
        _LOGGER.debug("Setting new sid")

        os.setpgrp()


    def __change_directory(self):
        """
        Private function for changing directory to /
        """
        _LOGGER.debug("Changing directory to /")

        os.chdir("/")

    def __background_process(self):
        """
        Function for forking to background process
        """
        _LOGGER.debug("Forking")

        pid = os.fork()

        if pid == 0:
            # CHILD
            return
        else:
            sys.exit(0)


def start():
    """
    Wrapper for daemonizing the current process
    """
    worker = Daemonizer()
    worker.run()



if __name__ == "__main__":
    start()