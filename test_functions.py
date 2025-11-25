from datetime import datetime
import re
import sys, os
from functools import wraps


def log(msg):
    ts = datetime.now().strftime("%H:%M:%S.%f")[:-3]
    print(f"{ts}] {msg}")


def extract_suffix(url: str) -> str:
            # Extract the filename: e.g. "yy01.png"
            filename = url.split("/")[-1]
            
            # Remove file extension
            name = filename.split(".")[0]  # "yy01"
            
            # Extract the letters before the digits
            match = re.match(r"([a-zA-Z]+)\d+", name)
            if match:
                return match.group(1)
            print("failed to find match")
            return ""


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


    

