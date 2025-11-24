from datetime import datetime
import re

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

text ="https://img.eol.cn/e_images/gk/2025/st/qg1/yy01.png"
print("this is the desired suffix",extract_suffix(text))