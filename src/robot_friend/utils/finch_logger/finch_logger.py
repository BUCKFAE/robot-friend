import glob
import logging
import os
import sys
from datetime import datetime

import colorlog
import tqdm

from robot_friend.resource_handler import get_log_dir
from robot_friend.utils.clean_setup_dir import clean_setup_dir


class TqdmLoggingHandler(logging.Handler):
    def __init__(self, level=logging.NOTSET):
        super().__init__(level)

    def emit(self, record):
        try:
            msg = self.format(record)
            if "ipykernel" in sys.modules:  # Running inside Jupyter
                print(msg, file=sys.stderr)  # Avoid tqdm interference
            else:
                tqdm.tqdm.write(msg, file=sys.stdout)
            self.flush()
        except Exception:
            self.handleError(record)


def _setup_logger() -> None:
    log_dir = get_log_dir()
    clean_setup_dir(log_dir, delete_content=False)

    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    log_filename = os.path.join(log_dir, f"app_{timestamp}.log")

    # Cleanup old log files, keep only the last 100
    log_files = sorted(glob.glob(os.path.join(log_dir, "app_*.log")), key=os.path.getmtime)
    if len(log_files) > 100:
        for old_log in log_files[:-100]:
            os.remove(old_log)

    # Define log formatters
    formatter_simple = colorlog.ColoredFormatter(
        "%(log_color)s[%(levelname)-8s] %(asctime)s [%(filename)s:%(lineno)d] - %(message)s",
        datefmt="%H:%M:%S",
        log_colors={
            "DEBUG": "cyan",
            "INFO": "green",
            "WARNING": "yellow",
            "ERROR": "red",
            "CRITICAL": "bold_red",
        },
    )

    formatter_detailed = logging.Formatter("%(asctime)s [%(levelname)-8s] %(filename)s:%(lineno)d - %(message)s")

    # Create file handler
    file_handler = logging.FileHandler(log_filename, mode="w")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter_detailed)

    # Create tqdm-compatible console handler with colors
    console_handler: TqdmLoggingHandler = TqdmLoggingHandler()  # type: ignore
    console_handler.setLevel(logging.DEBUG)
    console_handler.setFormatter(formatter_simple)

    # Get root logger and apply handlers
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)

    # Configure specific logger
    finch_logger = logging.getLogger("finch_logger")
    finch_logger.setLevel(logging.DEBUG)
    finch_logger.addHandler(console_handler)
    finch_logger.addHandler(file_handler)
    finch_logger.propagate = False


def _get_logger(name="finch_logger") -> logging.Logger:
    logger = logging.getLogger(name)
    return logger


_setup_logger()
finch_logger: logging.Logger = _get_logger()
