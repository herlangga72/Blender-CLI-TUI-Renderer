import logging
import sys

def setup_logger(name, level="INFO", log_file=None):
    """
    Configures and returns a logger instance.
    """
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper()))

    # Prevent duplicate handlers if called multiple times
    if not logger.handlers:
        formatter = logging.Formatter('[%(asctime)s] [%(levelname)s]: %(message)s')

        if log_file:
            handler = logging.FileHandler(log_file)
        else:
            handler = logging.StreamHandler(sys.stdout)

        handler.setFormatter(formatter)
        logger.addHandler(handler)

    return logger
