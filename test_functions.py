import os
import logging

LOG_DIR = "logs"
os.makedirs(LOG_DIR, exist_ok=True)

def get_logger(name: str):
    """
    Create a logger with a dedicated file for each module.
    """
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)

    # Prevent adding handlers multiple times
    if logger.handlers:
        return logger

    # File: logs/<module>.log — USE UTF-8
    file_handler = logging.FileHandler(
        f"{LOG_DIR}/{name}.log",
        encoding="utf-8"
    )
    
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    file_handler.setFormatter(formatter)

    logger.addHandler(file_handler)

    return logger


import json
_translation_cache = None

def load_translation_map():
    global _translation_cache
    if _translation_cache is not None:
        with open("translator.json") as f :
            _translation_cache = json.load(f)
    return _translation_cache