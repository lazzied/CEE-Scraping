from datetime import datetime
import re
import sys, os
from functools import wraps


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


print(extract_suffix("https://img.eol.cn/e_images/gk/2025/st/qg1/sxd06.png"))

