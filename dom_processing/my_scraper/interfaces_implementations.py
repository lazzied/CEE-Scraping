"""
Chinese-specific implementations for document retrieval.
"""
import re
from pathlib import Path

from utils import generate_selector_from_webelement
from .interfaces import ContentTransformer, ImageURLPattern, DocumentRetriever, TextParser
from .services import MetadataProcessing, PageDownloader, PDFConverter
from .models import Instance
import json
from pathlib import Path

class DriverOperations:
    """Base class for Selenium driver operations."""
    
    def __init__(self, selenium_driver=None):
        self.selenium_driver = selenium_driver


class ChineseDriverOperations(DriverOperations):
    """Chinese exam website driver operations."""
    
    def get_page_count(self, driver) -> int:
        """Get page count from JavaScript variable."""

        if not driver:
            raise ValueError("driver cannot be None")
        
        # Access the underlying WebDriver (SeleniumDriver is a wrapper)
        try:
            web_driver = driver.driver if hasattr(driver, 'driver') else driver
        except Exception as e:
            raise RuntimeError(f"Failed to access underlying WebDriver: {type(e).__name__}: {e}")
        
        if not hasattr(web_driver, 'execute_script'):
            raise AttributeError(
                f"WebDriver object has no 'execute_script' method. "
                f"Driver type: {type(web_driver).__name__}"
            )
        
        try:
            page_count = web_driver.execute_script("return _PAGE_COUNT;")
        except Exception as e:
            raise RuntimeError(f"Failed to execute JavaScript to get _PAGE_COUNT: {type(e).__name__}: {e}")
        
        if page_count is None:
            raise ValueError("_PAGE_COUNT JavaScript variable is not defined or is null")
        
        # Convert to int if it's a string or number
        try:
            page_count_int = int(page_count)
        except (ValueError, TypeError) as e:
            raise TypeError(f"_PAGE_COUNT cannot be converted to int, got {type(page_count).__name__}: {page_count}")
        
        if page_count_int < 1:
            raise ValueError(f"_PAGE_COUNT must be >= 1, got {page_count_int}")
        
        return page_count_int
        

class ChineseTextParser(TextParser):
    # Class attributes - valid subjects and exam variants
    VALID_SUBJECTS = {
        "语文",
        "英语",
        "数学",
        "物理",
        "化学",
        "生物",
        "历史",
        "地理",
        "政治",
        "技术"
    }
    
    EXAM_VARIANT_ALIASES = {
    # Province abbreviations
    "黑": "黑龙江卷",
    "黑龙江": "黑龙江卷",
    "吉": "吉林卷",
    "吉林": "吉林卷",
    "辽": "辽宁卷",
    "辽宁": "辽宁卷",
    "蒙": "内蒙古卷",
    "内蒙古": "内蒙古卷",
    "京": "北京卷",
    "沪": "上海卷",
    "津": "天津卷",
    "渝": "重庆卷",
    "冀": "河北卷",
    "晋": "山西卷",
    "苏": "江苏卷",
    "浙": "浙江卷",
    "皖": "安徽卷",
    "闽": "福建卷",
    "赣": "江西卷",
    "鲁": "山东卷",
    "豫": "河南卷",
    "鄂": "湖北卷",
    "湘": "湖南卷",
    "粤": "广东卷",
    "桂": "广西卷",
    "琼": "海南卷",
    "川": "四川卷",
    "蜀": "四川卷",
    "贵": "贵州卷",
    "黔": "贵州卷",
    "云": "云南卷",
    "滇": "云南卷",
    "陕": "陕西卷",
    "秦": "陕西卷",
    "甘": "甘肃卷",
    "陇": "甘肃卷",
    "青": "青海卷",
    "宁": "宁夏卷",
    "新": "新疆卷",
    "藏": "西藏卷",
    
    # Full province names
    "北京": "北京卷",
    "天津": "天津卷",
    "上海": "上海卷",
    "重庆": "重庆卷",
    "河北": "河北卷",
    "山西": "山西卷",
    "江苏": "江苏卷",
    "浙江": "浙江卷",
    "安徽": "安徽卷",
    "福建": "福建卷",
    "江西": "江西卷",
    "山东": "山东卷",
    "河南": "河南卷",
    "湖北": "湖北卷",
    "湖南": "湖南卷",
    "广东": "广东卷",
    "广西": "广西卷",
    "海南": "海南卷",
    "四川": "四川卷",
    "贵州": "贵州卷",
    "云南": "云南卷",
    "陕西": "陕西卷",
    "甘肃": "甘肃卷",
    "青海": "青海卷",
    "宁夏": "宁夏卷",
    "新疆": "新疆卷",
    "西藏": "西藏卷",
    
    # National variants numeric forms
    "全国卷1": "全国一卷",
    "全国一卷": "全国一卷",
    "全国1卷": "全国一卷",
    "全国卷2": "全国二卷",
    "全国二卷": "全国二卷",
    "全国2卷": "全国二卷",
    "全国卷3": "全国三卷",
    "全国三卷": "全国三卷",
    "全国3卷": "全国三卷",
    "新课标1": "全国一卷",
    "新课标2": "全国二卷",
    "新课标3": "全国三卷",
}


    
    def get_metadata_value(self, target_node, target_type, driver):



        if not target_node:
            raise ValueError("target_node cannot be None")
        
        if not target_type:
            raise ValueError("target_type cannot be empty")
        
        if not hasattr(target_node, 'web_element'):
            raise AttributeError(f"target_node missing 'web_element' attribute. Node type: {type(target_node).__name__}")
        
        if target_type != "page_count":
            try:
                text_content = target_node.web_element.text
            except Exception as e:
                raise RuntimeError(f"Failed to get text from web_element: {type(e).__name__}: {e}")
            
            if not text_content:
                raise ValueError(f"Empty text content for target_type '{target_type}'")
        
        try:
            match target_type:
                case "year":
                    # Extract first 4 consecutive digits from text (represents a year)
                    year_match = re.search(r'\d{4}', text_content)
                    if not year_match:
                        raise ValueError(f"No 4-digit year found in text: '{text_content}'")
                    
                    year = year_match.group(0)
                    return ("year", year)
                                
                case "subject":
                    # Loop through valid subjects and find first match in text
                    for subject in self.VALID_SUBJECTS:
                        if subject in text_content:
                            return ("subject", subject)
                    
                    raise ValueError(f"No valid subject found in text: '{text_content}'. Valid subjects: {self.VALID_SUBJECTS}")
                
                case "exam_variant":
                    found_variants = set()
                    
                    # First try to find single variant from long format (e.g., "黑龙江卷")
                    for variant in self.EXAM_VARIANT_ALIASES:
                        if variant in text_content:
                            found_variants.add(variant)
                    
                    # If we found exactly one variant, return it
                    if len(found_variants) == 1:
                        return ("exam_variant", list(found_variants))
                    
                    # If we found multiple long format variants, that's unusual but possible
                    if len(found_variants) > 1:
                        return ("exam_variant", list(found_variants))
                    
                    # No long format variants found - must check for multiple short forms
                    # Sort aliases by length (longest first) to avoid partial matches
                    sorted_aliases = sorted(self.EXAM_VARIANT_ALIASES.items(), 
                                        key=lambda x: len(x[0]), reverse=True)
                    
                    for alias, full_variant in sorted_aliases:
                        # Check if this alias appears as a whole word
                        if len(alias) == 1:
                            # For single chars, check word boundaries
                            if re.search(rf'\b{alias}\b', text_content):
                                found_variants.add(full_variant)
                        else:
                            if alias in text_content:
                                found_variants.add(full_variant)
                    
                    # Return whatever we found (could be multiple variants)
                    if found_variants:
                        return ("exam_variant", list(found_variants))
                    
                    # If still nothing found, return empty list (no error)
                    return ("exam_variant", [])
                
                case "page_count":
                    # Keep original page_count logic unchanged
                    chinese_driver_operations = ChineseDriverOperations()
                    try:
                        page_count = chinese_driver_operations.get_page_count(driver)
                    except Exception as e:
                        raise RuntimeError(f"Failed to get page count: {e}")
                    
                    return ("page_count", page_count)
                
                case _:
                    raise ValueError(
                        f"Unknown metadata type: '{target_type}'. "
                        f"Valid types: year, subject, exam_variant, page_count"
                    )
        except ValueError:
            raise
        except Exception as e:
            raise RuntimeError(f"Failed to extract metadata for type '{target_type}': {type(e).__name__}: {e}")

class ChineseContentTransformer(ContentTransformer):
    def __init__(self):
        dict_path = "dom_processing/dictionnaries/chinese_to_english_dictionnary.json"
        
        try:
            with open(dict_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except FileNotFoundError:
            raise FileNotFoundError(f"Translation dictionary not found at: {dict_path}")
        except json.JSONDecodeError as e:
            raise RuntimeError(f"Invalid JSON in translation dictionary at {dict_path}: {e}")
        except Exception as e:
            raise RuntimeError(f"Failed to load translation dictionary from {dict_path}: {type(e).__name__}: {e}")
        
        # FIXED: Extract the nested dictionary
        if isinstance(data, dict) and "chinese_to_english" in data:
            translation_dict = data["chinese_to_english"]
        elif isinstance(data, dict):
            translation_dict = data  # Fallback if already flat
        else:
            raise TypeError(f"Translation dictionary must be a dict, got {type(data).__name__}")
        
        if not isinstance(translation_dict, dict):
            raise TypeError(f"Translation dictionary must be a dict, got {type(translation_dict).__name__}")
        
        # Debug: Print loaded dictionary
        print(f"DEBUG: Loaded translation dictionary with {len(translation_dict)} entries")
        for key, value in list(translation_dict.items())[:5]:  # Print first 5
            print(f"  '{key}' -> '{value}'")
        
        self.dictionary = translation_dict

    def translate_to_english(self, text):
        if not isinstance(text, str):
            print(f"Warning: translate_to_english expects a string, got {type(text).__name__}: {text}")
            return text
        
        # Get translation
        translated = self.dictionary.get(text, text)
        
        # Warn if no translation found for Chinese text
        if translated == text and any(ord(c) > 127 for c in text):
            print(f"Warning: No translation found for Chinese text: '{text}'")
            # Check available keys that might be similar
            similar = [k for k in self.dictionary.keys() if text in k or k in text]
            if similar:
                print(f"  Similar keys found: {similar[:3]}")
        
        return translated
    
class ChineseImageURLPattern(ImageURLPattern):
    """Chinese exam website URL pattern parser."""
    
    # In ChineseImageURLPattern.get_raw_url()
    def get_raw_url(self, node) -> str:
        """Extract raw URL from DOM node."""
        if not node:
            raise ValueError("node cannot be None")
        
        if not hasattr(node, 'tag'):
            raise AttributeError(f"node missing 'tag' attribute. Node type: {type(node).__name__}")
        
        if not hasattr(node, 'web_element'):
            raise AttributeError(f"node missing 'web_element' attribute. Node type: {type(node).__name__}")
        if node.web_element is None:
            raise ValueError(f"node.web_element is None - element not found on page")

        # DEBUG: Print the node info
        print(f"DEBUG: get_raw_url called for node.tag={node.tag}")
        print(f"DEBUG: web_element type: {type(node.web_element)}")
        
        try:
            if node.tag == "img":
                # DEBUG: Try to get the element's session
                try:
                    session_id = node.web_element._parent.session_id
                    print(f"DEBUG: web_element session ID: {session_id}")
                except:
                    print(f"DEBUG: Could not get session ID")
                
                url = node.web_element.get_attribute("src")
            elif node.tag == "a":
                url = node.web_element.get_attribute("href")
            else:
                raise ValueError(f"Node tag must be 'img' or 'a', got '{node.tag}'")
        except Exception as e:
            raise RuntimeError(f"Failed to get URL attribute from {node.tag} element: {type(e).__name__}: {e}")

        if not url:
            raise ValueError(f"Empty URL from {node.tag} element")

        if url.startswith("data:"):
            raise ValueError("data URLs are not supported")
        
        print(f"DEBUG: Extracted URL: {url}")
        return url

    def get_url_base(self, raw_url: str) -> str:
        """Extract base URL from full URL.
        raw_url = "https://img.eol.cn/e_images/gk/2025/st/qg1/yy01.png"

        # Step by step:
        # 1. raw_url.rsplit("/", 1)
        #    → ["https://img.eol.cn/e_images/gk/2025/st/qg1", "yy01.png"]

        # 2. [0] takes first element
        #    → "https://img.eol.cn/e_images/gk/2025/st/qg1"

        # 3. + "/"
        #    → "https://img.eol.cn/e_images/gk/2025/st/qg1/"

        # Output:
        "https://img.eol.cn/e_images/gk/2025/st/qg1/"
        
        """
        if not raw_url:
            raise ValueError("raw_url cannot be empty")
        
        if not isinstance(raw_url, str):
            raise TypeError(f"raw_url must be a string, got {type(raw_url).__name__}")
        
        if "/" not in raw_url:
            raise ValueError(f"Invalid URL format (no slashes found): {raw_url}")
        
        try:
            return raw_url.rsplit("/", 1)[0] + "/"
        except Exception as e:
            raise RuntimeError(f"Failed to extract base URL from '{raw_url}': {type(e).__name__}: {e}")

    def extract_url_info(self, raw_url: str) -> tuple[str, str]:
        r"""Extract suffix and starting index from URL.
        
        Example URL: https://img.eol.cn/e_images/gk/2025/st/qg1/yy01.png

        Step by step:
        1. image_name = raw_url.split("/")[-1]
        → "yy01.png"

        2. stem = image_name.split(".")[0]
        → "yy01"

        3. match = re.match(r"([a-zA-Z]+)(\d+)", stem)
        → group(1) = "yy"
        → group(2) = "01"

        Returns:
            ("yy", "01") - suffix and start index
        
        Example: image_abc01.png → ("abc", "01")
        """
        if not raw_url:
            raise ValueError("raw_url cannot be empty")
        
        if not isinstance(raw_url, str):
            raise TypeError(f"raw_url must be a string, got {type(raw_url).__name__}")
        
        if "/" not in raw_url:
            raise ValueError(f"Invalid URL format (no slashes found): {raw_url}")
        
        try:
            image_name = raw_url.split("/")[-1]
        except Exception as e:
            raise RuntimeError(f"Failed to extract image name from URL '{raw_url}': {type(e).__name__}: {e}")
        
        if not image_name:
            raise ValueError(f"Empty image name extracted from URL: {raw_url}")
        
        if "." not in image_name:
            raise ValueError(f"Image name has no extension: {image_name} (from URL: {raw_url})")
        
        try:
            stem = image_name.split(".")[0]
        except Exception as e:
            raise RuntimeError(f"Failed to extract stem from image name '{image_name}': {type(e).__name__}: {e}")
        
        if not stem:
            raise ValueError(f"Empty stem extracted from image name: {image_name}")
        
        try:
            match = re.match(r"([a-zA-Z]+)(\d+)", stem)
        except Exception as e:
            raise RuntimeError(f"Regex matching failed for stem '{stem}': {type(e).__name__}: {e}")
        
        if not match:
            raise ValueError(
                f"Image name stem '{stem}' does not match expected pattern (letters followed by digits). "
                f"URL: {raw_url}"
            )
        
        try:
            suffix = match.group(1)
            start_index = match.group(2)
            if start_index not in ("01", "1", "00", "0"):
                start_index = "00"

        except Exception as e:
            raise RuntimeError(f"Failed to extract groups from regex match: {type(e).__name__}: {e}")
        
        if not suffix:
            raise ValueError(f"Empty suffix extracted from stem '{stem}'")
        if not start_index:
            raise ValueError(f"Empty start_index extracted from stem '{stem}'")
        
        return suffix, start_index

    def build_image_urls(
    self, suffix: str, start_index: int, base_url: str, page_count: int, extension: str = "png"
) -> list[str]:
        """Build list of image URLs from pattern."""
        if not suffix:
            raise ValueError("suffix cannot be empty")
        if not isinstance(suffix, str):
            raise TypeError(f"suffix must be a string, got {type(suffix).__name__}")
        
        if not isinstance(start_index, int):
            raise TypeError(f"start_index must be an int, got {type(start_index).__name__}")
        if start_index < 0:
            raise ValueError(f"start_index must be >= 0, got {start_index}")
        
        if not base_url:
            raise ValueError("base_url cannot be empty")
        if not isinstance(base_url, str):
            raise TypeError(f"base_url must be a string, got {type(base_url).__name__}")
        
        if not isinstance(page_count, int):
            raise TypeError(f"page_count must be an int, got {type(page_count).__name__}")
        if page_count < 1:
            raise ValueError(f"page_count must be >= 1, got {page_count}")
        
        try:
            urls = []
            if start_index == 0:
                for i in range(0, page_count):
                    suffix_num = f"{i:02d}"
                    urls.append(f"{base_url}{suffix}{suffix_num}.{extension}")
            else:
                for i in range(start_index, page_count + 1):
                    suffix_num = f"{i:02d}"
                    urls.append(f"{base_url}{suffix}{suffix_num}.{extension}")
            return urls
        except Exception as e:
            raise RuntimeError(
                f"Failed to build image URLs (suffix={suffix}, start={start_index}, "
                f"base_url={base_url}, page_count={page_count}): {type(e).__name__}: {e}"
            )

