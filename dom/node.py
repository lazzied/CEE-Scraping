from abc import ABC, abstractmethod
from typing import List, Optional
import re

class SiblingMixin:
    def siblings(self):
        if self.parent is None:
            raise RuntimeError("Node has no parent")
        return [c for c in self.parent.children if c is not self]

    def get_sibling_index(self):
        return self.parent.children.index(self)

    def get_next_sibling(self):
        idx = self.get_sibling_index()
        return self.parent.children[idx + 1] if idx + 1 < len(self.parent.children) else None

    def get_previous_sibling(self):
        idx = self.get_sibling_index()
        return self.parent.children[idx - 1] if idx > 0 else None


class BaseDOMNode(ABC):
    def __init__(self,
                schema_node: Optional[dict],
                  tag: str,
                    classes:List[str]=None,
                      attrs:Optional[dict]=None,
                        description:Optional[str]=None,
                          annotation:Optional[List["str"]] =None,
                            parent: Optional['BaseDOMNode']=None,
                            condition: Optional[bool]= None,
                            condition_id:Optional[int] = None,
                            target_types: Optional[list] = None,
                            
                          ):
        # Structure (always present)
        self.tag = tag
        self.classes = classes or []
        self.attrs = attrs or {}
        self.description = description
        self.annotation= annotation or []

        self.schema_node = schema_node


        self.children : List['BaseDOMNode'] = []
        self.parent = parent or None


        self.web_element = None

        if annotation and "target_element" in annotation:
            self.metadata_types = schema_node["target_types"]
        else:
            self.metadata_types = None

        self.condition = condition or False
        self.condition_id = condition_id or None
        self.target_types = target_types or []
    

    @abstractmethod
    def validate(self):
        pass

    def print_attributes(self):
        """Print all attributes of this node."""
        attrs_dict = {
            "tag": self.tag,
            "classes": self.classes,
            "attrs": self.attrs,
            #"description": self.description,
            #"template_name": self.template_name,
            #"web_element": self.web_element,
            #"is_dynamic": self.is_dynamic,
            #"parent": self.parent.tag if self.parent else None,
           # "children_count": len(self.children),
            #"siblings_count": len(self.siblings())
        }
        
        for key, value in attrs_dict.items():
            print(f"{key}: {value}")

    
    
    def add_child(self, child):
        """Add a child node."""
        self.children.append(child)

        
    def remove_child(self, child):
        """Remove a child node."""
        if child in self.children:
            self.children.remove(child)
            child.parent = None
    
    def set_attr(self, key, value):
        self.attrs[key] = value
    
    
    def get_text(self):
        """Get text content"""
        if self.web_element:
            return self.web_element.text
        return None
    
    
    
    def get_full_xpath(self):
        """Build XPath from structure"""
        path = ""
        node = self
        while node:
            segment = f"/{node.tag}"
            
            if node.classes or node.attrs:
                conditions = []
                
                for cls in node.classes:
                    conditions.append(f"contains(@class, '{cls}')")
                
                for attr_key, attr_value in node.attrs.items():
                    conditions.append(f"@{attr_key}='{attr_value}'")
                
                if conditions:
                    segment += "[" + " and ".join(conditions) + "]"
            
            path = segment + path
            node = node.parent
        
        return path if path else "/"
    
    def get_css_selector(self):
        """
        Generates CSS selector for this node based on tag, classes, and attributes.
        """
        selector_parts = [self.tag] if self.tag else []
        
        # Add classes
        if self.classes:
            selector_parts.append(''.join(f'.{cls}' for cls in self.classes))
        
        # Add ID if present
        if self.attrs:
            # Add other attributes
            for key, value in self.attrs.items():
                if key != 'id':
                    selector_parts.append(f'[{key}="{value}"]')
                else:
                    selector_parts.append(f"#{self.attrs['id']}")
            
        return ''.join(selector_parts) 

        """
        example: 
        input:
          node = DOMNode(tag="div", classes=["center", "point-center"])
            print(node.get_css_selector())

        output: div.center.point-center
        example 2: for id:
        input:
          node = DOMNode(tag="div", classes=["center"], attrs={"id": "main", "data-type": "example"})
            print(node.get_css_selector())
        output: div.center#main[data-type="example"]
        """
    
    

    def find_in_node(self, selector_type=None, selector_value=None, find_all=False):
        """
        Recursively searches the entire tree (starting from the node)
        for nodes matching the selector.
        
        Args:
            selector_type (str): 'id', 'class', 'tag', 'description', 'css', or 'xpath'
            selector_value (str or callable): The value to match. Can be:
                - A string for exact match
                - A regex pattern (prefix with 'regex:')
                - A range pattern (e.g., 'st{1-33}' matches st1, st2, ..., st33)
                - A range pattern with exceptions (e.g., 'st{1-33!3,7}' excludes st3 and st7)
                - A callable that takes a node and returns bool
            find_all (bool): If True, returns all matching nodes. If False, returns first match.
        
        Returns:
            DOMNode, list[DOMNode], or None: 
                - If find_all=True: list of all matching nodes (empty list if none found)
                - If find_all=False: the first matching node, or None if not found.
        
        Examples:
            # Exact match
            node.find_in_node('id', 'header', find_all=False)
            
            # Range pattern
            node.find_in_node('id', 'st{1-33}', find_all=True)
            
            # Range pattern with exceptions
            node.find_in_node('id', 'st{1-33!3,7}', find_all=True)
            
            # Regex pattern
            node.find_in_node('class', 'regex:btn-.*', find_all=True)
            
            # Custom matcher
            node.find_in_node('tag', lambda n: n.tag.startswith('h'), find_all=True)
        """
        
        # Return early if no selector provided
        if not selector_type or selector_value is None:
            return [] if find_all else None
        
        # If selector_value is callable, use it directly as the matcher
        if callable(selector_value):
            matches = selector_value
        else:
            # Determine the matching strategy based on selector_value format
            expanded_set = None
            regex_pattern = None
            exact_value = None
            
            # Check for regex pattern
            if isinstance(selector_value, str) and selector_value.startswith('regex:'):
                regex_pattern = re.compile(selector_value[6:])
            
            # Check for range pattern with exceptions: prefix{start-end!exc1,exc2,...}suffix
            elif isinstance(selector_value, str):
                match = re.match(r'^(.+)\{(\d+)-(\d+)!([0-9,]+)\}(.*)$', selector_value)
                if match:
                    prefix, start, end, exceptions_str, suffix = match.groups()
                    start_num, end_num = int(start), int(end)
                    exceptions = set(int(exc.strip()) for exc in exceptions_str.split(',') if exc.strip())
                    expanded_set = {f"{prefix}{i}{suffix}" for i in range(start_num, end_num + 1) if i not in exceptions}
                else:
                    # Check for range pattern without exceptions: prefix{start-end}suffix
                    match = re.match(r'^(.+)\{(\d+)-(\d+)\}(.*)$', selector_value)
                    if match:
                        prefix, start, end, suffix = match.groups()
                        start_num, end_num = int(start), int(end)
                        expanded_set = {f"{prefix}{i}{suffix}" for i in range(start_num, end_num + 1)}
                    else:
                        # It's an exact match
                        exact_value = selector_value
            
            # Create the matcher function based on selector type and processed value
            if selector_type == "id":
                if regex_pattern:
                    matches = lambda node: bool(regex_pattern.match(node.attrs.get("id", "")))
                elif expanded_set:
                    matches = lambda node: node.attrs.get("id") in expanded_set
                else:
                    matches = lambda node: node.attrs.get("id") == exact_value
            
            elif selector_type == "class":
                if regex_pattern:
                    matches = lambda node: any(regex_pattern.match(cls) for cls in node.classes)
                elif expanded_set:
                    matches = lambda node: any(cls in expanded_set for cls in node.classes)
                else:
                    matches = lambda node: exact_value in node.classes
            
            elif selector_type == "tag":
                if regex_pattern:
                    matches = lambda node: bool(regex_pattern.match(node.tag))
                elif expanded_set:
                    matches = lambda node: node.tag in expanded_set
                else:
                    matches = lambda node: node.tag == exact_value
            
            elif selector_type == "description":
                if regex_pattern:
                    matches = lambda node: bool(regex_pattern.match(node.description or ""))
                elif expanded_set:
                    matches = lambda node: node.description in expanded_set
                else:
                    matches = lambda node: node.description == exact_value
            
            elif selector_type == "css":
                matches = lambda node: node.get_css_selector() == exact_value
            
            elif selector_type == "xpath":
                matches = lambda node: node.get_node_xpath() == exact_value
            
            else:
                matches = lambda node: False
        
        # Depth-first search
        matching_nodes = []
        stack = [self]
        
        while stack:
            current = stack.pop()
            if matches(current):
                if not find_all:
                    return current
                matching_nodes.append(current)
            stack.extend(reversed(current.children))
        
        return matching_nodes if find_all else None
        
    
    
    
    def print_dom_tree(self,depth=0):
        indent = "  " * depth
        print(
            f'{indent}{self.tag} — classes: {self.classes}'
            + (f' — id: {self.attrs["id"]}' if "id" in self.attrs else "")
            + (f' — webElement: {self.web_element}' if self.web_element else "")
            + (f' - webelement content: {self.web_element.text}' if self.web_element else '')

        )
        for child in self.children:
            child.print_dom_tree( depth + 1)


    def remove_self(self, recursive=True):
        """
        Remove this node from the DOM tree.
        If recursive=True, also detaches all descendants.
        """
        # Remove from parent's children
        if self.parent:
            try:
                self.parent.children.remove(self)
            except ValueError:
                pass
            self.parent = None

        if recursive:
            for child in self.children:
                child.parent = None
            self.children = []
            
    def get_dom_tree_str(self, depth=0) -> str:
        indent = "  " * depth
        s = (
            f'{indent}{self.tag} — classes: {self.classes} -- description: {self.description}'
            + (f' — id: {self.attrs["id"]}' if "id" in self.attrs else "")
            + (f' — webElement: {self.web_element}' if self.web_element else "")
            + "\n"
        )
        for child in self.children:
            s += child.get_dom_tree_str(depth + 1)
        return s
    
class RootNode(BaseDOMNode):
    def __init__(self,
                 schema_node: Optional[dict],
                  tag: str,
                    classes:List[str]=None,
                      attrs:Optional[dict]=None,
                 ):
        super().__init__(
            schema_node,
            tag,
              classes,
                attrs,
                "Root Node")

        self.parent = None  # Root has no parent
        self.annotation = None
    
    def validate(self):
        # Root node is always valid
        return True
    
    
    

class TemplateNode(SiblingMixin,BaseDOMNode):
    def __init__(self,
                 schema_node: Optional[dict],
                  tag: str,
                   parent:BaseDOMNode,
                    classes:List[str]=None,
                      attrs:Optional[dict]=None,
                        description:Optional[str]=None,
                          template_name:Optional[str]=None,
                           annotation:Optional[List["str"]] =None):
        super().__init__(schema_node, tag, classes, attrs, description, annotation)

        self.template_name = template_name
    
    def validate(self):
        # Example validation: ensure template_name is set
        return self.template_name is not None

class RegularNode(SiblingMixin,BaseDOMNode):
    def __init__(self,
                 schema_node: Optional[dict],
                  tag: str,
                  parent:BaseDOMNode,
                    classes:Optional[List[str]]=None,
                      attrs:Optional[dict]=None,
                        description:Optional[str]=None,
                          annotation:Optional[List["str"]] =None,
                            ):
        super().__init__(schema_node,tag, classes, attrs, description, annotation,parent)
    
    def validate(self):
        # Example validation: ensure tag is not empty
        return bool(self.parent)
