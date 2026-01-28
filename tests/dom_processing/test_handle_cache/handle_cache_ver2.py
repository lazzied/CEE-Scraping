from abc import ABC, abstractmethod
from typing import List, Optional, Protocol

from dom.my_stack import Stack
from dom.node import BaseDOMNode, RootNode
from dom_processing.json_parser import ConfigQueries, SchemaQueries, TemplateRegistry

from selenium.webdriver.common.by import By

# ==================== INTERFACES/PROTOCOLS ====================

class WebElementInterface(Protocol):
    """Protocol for web element operations - doesn't require Selenium"""
    
    def find_element(self, by: str, selector: str) -> 'WebElementInterface':
        ...
    
    def find_elements(self, by: str, selector: str) -> List['WebElementInterface']:
        ...


class ElementFinder(ABC):
    """Abstract element finder - can be mocked easily"""
    
    @abstractmethod
    def find_single(self, parent: WebElementInterface, selector: str) -> Optional[WebElementInterface]:
        """Find single element"""
        pass
    
    @abstractmethod
    def find_multiple(self, parent: WebElementInterface, selector: str) -> List[WebElementInterface]:
        """Find multiple elements"""
        pass


class SeleniumElementFinder(ElementFinder):
    """Concrete Selenium implementation - only used in production"""
    
    def find_single(self, parent: WebElementInterface, selector: str) -> Optional[WebElementInterface]:
        try:
            return parent.find_element(By.CSS_SELECTOR, selector)
        except Exception:
            return None
    
    def find_multiple(self, parent: WebElementInterface, selector: str) -> List[WebElementInterface]:
        try:
            return parent.find_elements(By.CSS_SELECTOR, selector)
        except Exception:
            return []


# ==================== IMPROVED CACHE HANDLER ====================

class HandleCaching:
    """
    Manages two types of caching:
    1. Landmark Stack: Hierarchical web elements for navigation
    2. Prefetch Queues: Pre-fetched sibling elements (per template)
    
    Now with dependency injection for optimal testability
    """
    
    def __init__(
        self,
        element_finder: ElementFinder, # in production, use SeleniumElementFinder()
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
        element = self._element_finder.find_single(parent, selector)
        
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
        elements = self._element_finder.find_multiple(parent, selector)
        
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


# ==================== VALIDATOR ====================

class ElementValidator:
    """Validates element types - easily mockable"""
    
    def is_valid_landmark(self, element: any) -> bool:
        """
        Check if element is valid for caching
        
        Input: element - Element to validate
        Output: bool
        """
        # In production, check for WebElement
        from selenium.webdriver.remote.webelement import WebElement
        return isinstance(element, WebElement)


# ==================== SELECTOR BUILDER ====================

class SelectorBuilder:
    """Builds CSS selectors from templates - separated for testability"""
    
    def __init__(
        self,
        template_registry: TemplateRegistry,
        config_queries: ConfigQueries
    ):
        self._template_registry = template_registry
        self._config_queries = config_queries
    
    def build_selector_for_template(self, template_name: str) -> str:
        """
        Build CSS selector for a template
        
        Input: template_name
        Output: CSS selector string
        """
        invariant_chars = self._template_registry.get_template_invariant_characteristics(
            template_name,
            self._config_queries
        )
        return self._template_registry.form_template_selector(template_name, invariant_chars)


# ==================== FACADE/COORDINATOR ====================

class CachingCoordinator:
    """
    High-level coordinator that orchestrates caching operations.
    This is what you'd use in production code.
    """
    
    def __init__(
        self,
        cache_handler: HandleCaching,
        selector_builder: SelectorBuilder,
        schema_queries: SchemaQueries
    ):
        self._cache_handler = cache_handler
        self._selector_builder = selector_builder
        self._schema_queries = schema_queries
    
    def initialize_with_root(self, root_node: 'RootNode') -> None:
        """Initialize cache with root node's web element"""
        self._cache_handler.initialize_landmark_cache(root_node.web_element)
    
    def cache_landmark_node(self, node: 'BaseDOMNode') -> bool:
        """Cache a landmark node"""
        selector = node.get_css_selector()
        return self._cache_handler.push_landmark(selector)
    
    def cache_template_instances(self, template_name: str) -> int:
        """Cache all instances of a template"""
        selector = self._selector_builder.build_selector_for_template(template_name)
        return self._cache_handler.push_prefetched_elements(selector)
    
    def should_cache_node(self, schema_node: dict) -> bool:
        """Check if node should be cached"""
        return self._schema_queries.is_landmark(schema_node)
    
    def uncache_landmark(self) -> Optional[WebElementInterface]:
        """Remove current landmark"""
        return self._cache_handler.pop_landmark()