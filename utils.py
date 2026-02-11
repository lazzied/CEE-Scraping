from datetime import datetime
import re
import sys, os
from functools import wraps
import logging
from selenium.common.exceptions import StaleElementReferenceException
from typing import Union, List
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.common.by import By

import json
from pathlib import Path

def generate_selector_from_webelement(web_element):
    tag = web_element.tag_name.lower()
    selector_parts = [tag]

    driver = web_element.parent
    attrs = driver.execute_script(
        """
        const attrs = {};
        for (const attr of arguments[0].attributes) {
            attrs[attr.name] = attr.value;
        }
        return attrs;
        """,
        web_element
    )

    # Classes
    if 'class' in attrs and attrs['class'].strip():
        classes = attrs['class'].split()
        selector_parts.append(''.join(f'.{cls}' for cls in classes))
        del attrs['class']

    # ID
    if 'id' in attrs:
        selector_parts.append(f"#{attrs['id']}")
        del attrs['id']

    # Other attributes
    for key, value in sorted(attrs.items()):
        selector_parts.append(f'[{key}="{value}"]')

    return ''.join(selector_parts)


def get_direct_children_in_range(
    parent: WebElement,
    child_range: Union[str, int, List[int]],
    selector: str
) -> List[WebElement]:
    # Get all direct children first
    children = parent.find_elements(By.XPATH, "./*")
    total = len(children)
    
    # Determine which indices to check based on range
    if child_range == "ALL":
        indices = range(0, total)  # All children
    elif isinstance(child_range, int):
        indices = [child_range - 1]  # Single child (convert to 0-indexed)
    elif isinstance(child_range, list) and len(child_range) == 2:
        start, end = child_range
        indices = range(start - 1, end)  # Range (convert to 0-indexed, end is inclusive)
    else:
        raise ValueError("Invalid range format")
    
    result = []
    for i in indices:
        if i < 0 or i >= total:
            continue
        
        child = children[i]
        
        # Check if this child matches the selector
        if matches_css_selector(child, selector):
            result.append(child)
    
    return result


def matches_css_selector(element: WebElement, selector: str) -> bool:
    """
    Check if a WebElement matches a CSS selector.
    Handles complex selectors like: div.class1.class2#id[attr='value']
    """
    try:
        # Use JavaScript to check if element matches the selector
        driver = element.parent
        result = driver.execute_script(
            "return arguments[0].matches(arguments[1]);",
            element,
            selector
        )
        return result
    except:
        return False

def load_json_from_project(json_path: str, project_root: str | None = None) -> dict:
    """
    Search for a JSON file inside the project and return it as a dict.

    json_path: filename or relative path (e.g. "config.json" or "schemas/main.json")
    project_root: root directory to search from (defaults to cwd)
    """
    root = Path(project_root) if project_root else Path.cwd()

    target = Path(json_path)

    # Case 1: direct relative/absolute path exists
    if target.is_absolute() or (root / target).exists():
        path = target if target.is_absolute() else root / target
    else:
        # Case 2: search by filename inside project
        matches = list(root.rglob(target.name))
        if not matches:
            raise FileNotFoundError(f"JSON file not found in project: {json_path}")
        if len(matches) > 1:
            raise FileExistsError(
                f"Multiple JSON files named '{target.name}' found: {matches}"
            )
        path = matches[0]

    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)





