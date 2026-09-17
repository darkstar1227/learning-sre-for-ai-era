import logging
import sys

from pythonjsonlogger import jsonlogger


def configure_logging() -> logging.Logger:
    logger = logging.getLogger("sre-lab-api")
    logger.setLevel(logging.INFO)

    handler = logging.StreamHandler(sys.stdout)
    formatter = jsonlogger.JsonFormatter(
        "%(asctime)s %(levelname)s %(message)s",
        rename_fields={
            "asctime": "timestamp",
            "levelname": "level",
        },
    )
    handler.setFormatter(formatter)

    logger.handlers = [handler]
    logger.propagate = False

    return logger


logger = configure_logging()
