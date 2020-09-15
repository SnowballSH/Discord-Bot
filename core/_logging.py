"""
Please take the time to improve this at some point.
"""

from logging import handlers
from platform import system
import colorlog
import logging
import sys
import os


def setup_logging(*mute_modules):
    class TimedRotatingFileHandler(handlers.TimedRotatingFileHandler):
        def __init__(self, path: str, **kwargs):
            self.filename = kwargs.get("filename")
            self.path = path
            super().__init__(**kwargs)

        def _open(self):
            """
            Open the current base file with the (original) mode and encoding.
            Return the resulting stream.
            """
            return open(f"{self.path}{self.filename}", self.mode, encoding="UTF-8")

        def doRollover(self):
            """
            do a rollover; in this case, a date/time stamp is appended to the filename
            when the rollover happens.  However, you want the file to be named for the
            start of the interval, not the current time.  If there is a backup count,
            then we have to get a list of matching filenames, sort them and remove
            the one with the oldest suffix.
            """
            import time

            if self.stream:
                self.stream.close()
                self.stream = None

            # get the time that this sequence started at and make it a TimeTuple
            current_time = int(time.time())
            dst_now = time.localtime(current_time)[-1]
            t = self.rolloverAt - self.interval

            if self.utc:
                time_tuple = time.gmtime(t)
            else:
                time_tuple = time.localtime(t)
                dst_then = time_tuple[-1]
                if dst_now != dst_then:
                    if dst_now:
                        addend = 3600
                    else:
                        addend = -3600
                    time_tuple = time.localtime(t + addend)

            dfn = self.rotation_filename(
                f"{self.path}{time.strftime(self.suffix, time_tuple)}.log"
            )
            if not os.path.exists(self.path):
                os.mkdir(self.path)

            if os.path.exists(dfn):
                os.remove(dfn)

            self.rotate(self.baseFilename, dfn)

            if self.backupCount > 0:
                for s in self.getFilesToDelete():
                    os.remove(s)

            if not self.delay:
                self.stream = self._open()

            new_rollover_at = self.computeRollover(current_time)

            while new_rollover_at <= current_time:
                new_rollover_at = new_rollover_at + self.interval

            # If DST changes and midnight or weekly rollover, adjust for this.
            if (self.when == "MIDNIGHT" or self.when.startswith("W")) and not self.utc:
                dst_at_rollover = time.localtime(new_rollover_at)[-1]
                if dst_now != dst_at_rollover:
                    if (
                        not dst_now
                    ):  # DST kicks in before next rollover, so we need to deduct an hour
                        addend = -3600
                    else:  # DST bows out before next rollover, so we need to add an hour
                        addend = 3600
                    new_rollover_at += addend
            self.rolloverAt = new_rollover_at

    root = logging.getLogger()
    root.setLevel(logging.DEBUG)

    stdout = logging.StreamHandler(stream=sys.stdout)
    stdout.setLevel(logging.DEBUG)
    if system().lower() == "linux":
        fmt = {
            "DEBUG": f"%(log_color)s[%(name)s][%(levelname)s] %(message)s",
            "INFO": f"%(log_color)s[%(name)s][%(levelname)s] %(message)s",
            "WARNING": f"%(log_color)s[%(name)s][%(levelname)s] %(message)s",
            "ERROR": f"%(log_color)s[%(name)s][%(levelname)s] %(message)s",
            "CRITICAL": f"%(log_color)s[%(name)s][%(levelname)s] %(message)s",
        }
    else:
        fmt = {
            "DEBUG": f"%(log_color)s[%(asctime)s][%(name)s][%(levelname)s] %(message)s",
            "INFO": f"%(log_color)s[%(asctime)s][%(name)s][%(levelname)s] %(message)s",
            "WARNING": f"%(log_color)s[%(asctime)s][%(name)s][%(levelname)s] %(message)s",
            "ERROR": f"%(log_color)s[%(asctime)s][%(name)s][%(levelname)s] %(message)s",
            "CRITICAL": f"%(log_color)s[%(asctime)s][%(name)s][%(levelname)s] %(message)s",
        }

    stdout.setFormatter(
        colorlog.LevelFormatter(
            fmt=fmt,
            datefmt="%Y-%m-%d %H:%M:%S",
            log_colors={
                "DEBUG": "cyan",
                "INFO": "white",
                "WARNING": "yellow",
                "ERROR": "red",
                "CRITICAL": "bold_red",
            },
        )
    )

    root.addHandler(stdout)

    if not os.path.exists("./logs"):
        os.mkdir("./logs")

    rotator = TimedRotatingFileHandler(
        filename="latest.log",
        encoding="UTF-8",
        backupCount=168,
        when="H",
        path="./logs/",
    )

    rotator.setFormatter(
        logging.Formatter(
            fmt="[%(asctime)s][%(name)s][%(levelname)s] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    )
    rotator.setLevel(logging.DEBUG)
    root.addHandler(rotator)

    for module in mute_modules:
        logging.getLogger(module).setLevel(logging.INFO)
