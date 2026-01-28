from abc import ABC, abstractmethod
from typing import List, Optional

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
        self.children.insert(0,child)

        
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
            for a node matching the selector.
            
            Args:
                selector_type (str): 'id', 'class', 'tag', 'attr', 'css', or 'xpath'
                selector_value (str): The value to match.
                find_all (bool): If True, returns all matching nodes. If False, returns first match.
            
            Returns:
                DOMNode, list[DOMNode], or None: 
                    - If find_all=True: list of all matching nodes (empty list if none found)
                    - If find_all=False: the first matching node, or None if not found.
            """

            def matches(node):
                if not selector_type or not selector_value:
                    return False

                if selector_type == "id":
                    return node.attrs.get("id") == selector_value

                elif selector_type == "class":
                    return selector_value in node.classes

                elif selector_type == "tag":
                    return node.tag == selector_value
                elif selector_type == "description":
                    return node.description == selector_value

                elif selector_type == "attr":
                    if "=" in selector_value:
                        key, val = selector_value.split("=", 1)
                        return node.attrs.get(key) == val
                    return selector_value in node.attrs

                elif selector_type == "css":
                    # Compare full CSS selector from node.get_css_selector()
                    try:
                        node_selector = node.get_css_selector()
                        return node_selector == selector_value
                    except Exception:
                        return False
                elif selector_type == "xpath":
                    node_selector = node.get_node_xpath()
                    # this is hard to implement since i don't have access to the element text

                return False

            # Depth-first search starting from the root node
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
            f'{indent}{self.tag} — classes: {self.classes}'
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
