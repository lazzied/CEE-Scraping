from typing import Optional
from dom.node import BaseDOMNode, RootNode
from dom_processing.dom_tree_builder.caching.cache import HandleCaching
from dom_processing.dom_tree_builder.caching.interfaces import WebElementInterface
from dom_processing.dom_tree_builder.caching.selectors import SelectorBuilder
from dom_processing.json_parser import SchemaQueries


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
    
    def initialize_with_root(self, root_element: WebElementInterface) -> None:
        """Initialize cache with root node's web element"""
        self._cache_handler.initialize_landmark_cache(root_element)
    
    def cache_landmark_node(self, node: 'BaseDOMNode') -> bool:
        """Cache a landmark node"""
        selector = node.get_css_selector()
        return self._cache_handler.push_landmark(selector)
    
    def cache_webelement(self,element: WebElementInterface):
        return self._cache_handler.push_webelement(element)

    def should_cache_node(self, schema_node: dict) -> bool: # this is without prefetch template
        """Check if node should be cached"""
        return self._schema_queries.is_landmark(schema_node) 
    
    def uncache_landmark(self) -> WebElementInterface:
        """Remove current landmark"""
        return self._cache_handler.pop_landmark()
    