from datetime import datetime
import re
import sys, os
from functools import wraps
import logging
from selenium.common.exceptions import StaleElementReferenceException

def log(msg):
    ts = datetime.now().strftime("%H:%M:%S.%f")[:-3]
    print(f"{ts}] {msg}")


def extract_suffix(url: str) -> tuple[str, str]:
    filename = url.split("/")[-1]
    name = filename.split(".")[0]
    
    print(f"[DEBUG] Extracting from filename: {filename}, name: {name}")

    match = re.match(r"([a-zA-Z]+)(\d+)", name)
    if match:
        letters = match.group(1)
        number = match.group(2)
        print(f"[DEBUG] Matched - letters: {letters}, number: {number}")
        return letters, number
    
    print(f"[WARNING] No match for pattern in: {name}")
    return "", ""

def is_stale(element) -> bool:
    try:
        element.is_enabled()
        return False
    except StaleElementReferenceException:
        return True

def suppress_print(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        _stdout = sys.stdout
        sys.stdout = open(os.devnull, "w")
        try:
            return func(*args, **kwargs)
        finally:
            sys.stdout = _stdout
    return wrapper



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


def description_fetcher(node):
    """Fetch all unique descriptions from the DOM tree."""
    
    return list



