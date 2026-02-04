from typing import Optional
from selenium.webdriver.common.by import By
from dom.my_stack import Stack
from dom_processing.dom_tree_builder.caching.finders import SeleniumElementFinder
from dom_processing.dom_tree_builder.caching.interfaces import ElementFinder, WebElementInterface
from dom_processing.dom_tree_builder.caching.validators import ElementValidator


class HandleCaching:
    """
    Manages two types of caching:
    1. Landmark Stack: Hierarchical web elements for navigation
    2. Prefetch Queues: Pre-fetched sibling elements (per template)
    
    Now with dependency injection for optimal testability
    """
    
    def __init__(
        self,
        element_finder: SeleniumElementFinder, # in production, use SeleniumElementFinder()
        landmark_cache: Optional[Stack] = None,
        element_validator: Optional['ElementValidator'] = None
    ):
        """
        Input:
            - element_finder: Strategy for finding elements (injected dependency)
            - landmark_cache: Stack for caching (injected for testing)
            - element_validator: Validates element types (injected for testing)
        """
        self._element_finder = element_finder
        self._landmark_cache = landmark_cache or Stack()
        self._element_validator = element_validator or ElementValidator()
    
    # ==================== PUBLIC API ====================
    
    def initialize_landmark_cache(self, root_element: WebElementInterface) -> None:
        """
        Initialize cache with root element
        
        Input: root_element - Root web element
        Output: None
        """
        if self._landmark_cache.is_empty():
            self._landmark_cache.push(root_element)
           
    
    def push_landmark(self, selector: str) -> bool:
        """
        Find and push a landmark element to cache
        
        Input: selector - CSS selector string
        Output: bool - True if element found and pushed, False otherwise
        """
        if self._landmark_cache.is_empty():
            return False
        
        parent = self._landmark_cache.top()
        try:
            element = self._element_finder.find_single(parent, "CSS_SELECTOR", selector)
        except:
                def _print_parent_cssselector(element):
                    parent_id = element.get_attribute("id")
                    parent_class = element.get_attribute("class")

                    parent_selector = element.tag_name \
                                + (f"#{parent_id}" if parent_id else "") \
                + (f".{'.'.join(parent_class.split())}" if parent_class else "")
                    
                    return parent_selector
                raise Exception(f"didn't find the element you want; the current_landmark is: {_print_parent_cssselector(parent)} and the element you want is: {selector}")
                #will later add user inputs, when i fix global parameters and main
       

        if element and self._element_validator.is_valid_landmark(element):
            
            self._landmark_cache.push(element)
            return True
        
        return False
    
    def push_prefetched_elements(self, selector: str) -> int:
        """
        Find and push multiple elements matching selector
        
        Input: selector - CSS selector string
        Output: int - Number of elements pushed
        """
        if self._landmark_cache.is_empty():
            return 0
        
        parent = self._landmark_cache.top()
        elements = self._element_finder.find_multiple(parent, By.CSS_SELECTOR, ">" + selector) #direct children only
        
        # Filter valid elements FIRST, then reverse
        valid_elements = [
            el for el in elements 
            if self._element_validator.is_valid_landmark(el)
        ]
        
        # Push in reverse so first valid element is on top
        for element in reversed(valid_elements):
            self._landmark_cache.push(element)
        
        return len(valid_elements)
    
    def pop_landmark(self) -> Optional[WebElementInterface]:
        """
        Remove and return top element from cache
        
        Output: WebElementInterface or None
        """
        if not self._landmark_cache.is_empty():
            return self._landmark_cache.pop()
        return None
    
    def get_current_landmark(self) -> Optional[WebElementInterface]:
        """
        Get current landmark without removing it
        
        Output: WebElementInterface or None
        """
        if not self._landmark_cache.is_empty():
            return self._landmark_cache.top()
        return None
    
    def cache_size(self) -> int:
        """Get current cache size"""
        return self._landmark_cache.size()
    
    def is_empty(self) -> bool:
        """Check if cache is empty"""
        return self._landmark_cache.is_empty()
    
    def clear(self) -> None:
        """Clear all cached elements"""
        while not self._landmark_cache.is_empty():
            self._landmark_cache.pop()
