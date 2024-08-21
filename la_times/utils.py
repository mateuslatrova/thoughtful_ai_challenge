import logging


def get_stdout_logger(logger_name: str) -> logging.Logger:
    logger = logging.getLogger(logger_name)

    logger.setLevel(logging.DEBUG)

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG)

    formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")

    console_handler.setFormatter(formatter)

    logger.addHandler(console_handler)

    return logger
