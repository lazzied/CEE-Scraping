from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement
from typing import List, Optional

from dom_processing.dom_tree_builder.caching.interfaces import WebElementInterface

class SeleniumElementFinder:
    """Concrete Selenium implementation - only used in production"""

    def _resolve_by(self, by_suffix: str):
        """Convert a string like 'XPATH' or 'CSS_SELECTOR' into By.XPATH, etc."""
        by_suffix = by_suffix.upper()  # make sure it's uppercase
        mapping = {
            "ID": By.ID,
            "NAME": By.NAME,
            "XPATH": By.XPATH,
            "LINK_TEXT": By.LINK_TEXT,
            "PARTIAL_LINK_TEXT": By.PARTIAL_LINK_TEXT,
            "TAG_NAME": By.TAG_NAME,
            "CLASS_NAME": By.CLASS_NAME,
            "CSS_SELECTOR": By.CSS_SELECTOR
        }
        if by_suffix not in mapping:
            raise ValueError(f"Invalid by_suffix: {by_suffix}")
        return mapping[by_suffix]

    def find_single(self, parent: WebElementInterface, by_suffix: str, selector: str) -> WebElementInterface:
        try:
            by = self._resolve_by(by_suffix)
            return parent.find_element(by, selector)
        except Exception:
            return None

    def find_multiple(self, parent: WebElementInterface, by_suffix: str, selector: str) -> List[WebElementInterface]:
        try:
            by = self._resolve_by(by_suffix)
            return parent.find_elements(by, selector)
        except Exception:
            return []
