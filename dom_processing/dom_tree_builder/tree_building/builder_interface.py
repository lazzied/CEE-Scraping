

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Type

from dom.node import BaseDOMNode, RegularNode, RootNode, TemplateNode
from dom_processing.json_parser import ConfigQueries, SchemaQueries, TemplateRegistry
import inspect

_NODE_REGISTRY: Dict[str, Type[BaseDOMNode]] = {
    "root": RootNode,
    "template": TemplateNode,
    "regular": RegularNode,
}


class TreeBuilderStrategy(ABC):
    
    @abstractmethod
    def should_apply(
        self, 
        schema_queries: SchemaQueries,
        schema_node: dict
    ) -> bool:
        """Determines if this strategy applies to a given schema"""
        pass
    
    @abstractmethod
    def build_node_tree_from_top(
        self,
        schema_queries: SchemaQueries,
        config_queries: Optional[ConfigQueries],
        template_registry: Optional[TemplateRegistry],
        schema_node: dict,
        parent_node: Optional[BaseDOMNode] = None
    ):
        """Build node tree"""
        pass

    @staticmethod
    def filter_kwargs_for_class(cls: type, kwargs: Dict[str, Any]) -> Dict[str, Any]:
        """
        the need for this function: the schema node is a dictionary that contains
        sometimes  key:value items that aren't needed in the node creation

        Filter kwargs to only include parameters accepted by the class __init__ method.
        
        Args:
            cls: The class to inspect
            kwargs: Dictionary of all available parameters
        
        Returns:
            Filtered dictionary containing only valid parameters for the class
        """
        # Get the __init__ signature
        sig = inspect.signature(cls.__init__)
        
        # Get parameter names (excluding 'self')
        valid_params = set(sig.parameters.keys()) - {'self'}
        
        # Filter kwargs to only include valid parameters
        return {k: v for k, v in kwargs.items() if k in valid_params}
    
    def create_node(self,
    node_type: str,
    schema_node: dict,
    **extra_kwargs
) -> BaseDOMNode:
        """
        Factory function to create nodes from schema.
        
        Args:
            node_type: Type of node to create ('root', 'regular', 'template')
            schema_node: Dictionary containing node configuration
            **extra_kwargs: Additional parameters to pass (like parent)
        
        Returns:
            Created node instance
        """
        try:
            cls = _NODE_REGISTRY[node_type]
        except KeyError:
            raise ValueError(f"Unknown node type: {node_type}")
        
        # Combine schema_node contents with extra_kwargs
        # But also pass schema_node itself as a parameter
        all_kwargs = {
            'schema_node': schema_node,  # Pass the full dict
            **schema_node,               # Unpack for other params (tag, classes, etc.)
            **extra_kwargs               # Runtime params (parent, etc.)
        }
        
        # Filter to only valid parameters for this class
        filtered_kwargs = TreeBuilderStrategy.filter_kwargs_for_class(cls, all_kwargs)
        
        return cls(**filtered_kwargs)