class DOMNode:
    def __init__(self, tag, classes=None, attrs=None, description="", template_name=None):
        # Structure (always present)
        self.tag = tag
        self.classes = classes or []
        self.attrs = attrs or {}
        self.description = description
        self.template_name = template_name
        self.web_element = None
        self.children = []
        self.parent = None
        self.is_dynamic = False
        # Don't store siblings - compute them dynamically!

        

    def siblings(self):
        """
        Dynamically compute siblings from parent's children.
        Always up-to-date, no manual tracking needed.
        """
        if self.parent is None:
            return []
        return [child for child in self.parent.children if child is not self]
    
    def add_child(self, child):
        """Add a child and set its parent pointer."""
        child.parent = self
        self.children.append(child)
        # Siblings are computed dynamically, so no manual update needed!
    
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
    
    def click(self):
        """Click element"""
        if self.web_element:
            self.web_element.click()
    
    
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
        if 'id' in self.attrs:
            selector_parts.append(f"#{self.attrs['id']}")
        
        # Add other attributes
        for key, value in self.attrs.items():
            if key != 'id':
                selector_parts.append(f'[{key}="{value}"]')
        
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
     
    def get_sibling_index(self):
        """Get this node's index among its siblings."""
        if self.parent is None:
            return 0
        return self.parent.children.index(self)
    
    def find_in_node(self, selector_type=None, selector_value=None):
        """
        Recursively searches the entire tree (starting from the node)
        for a node matching the selector.
        
        Args:
            selector_type (str): 'id', 'class', 'tag', 'attr', or 'css' or "xpath'
            selector_value (str): The value to match.
        
        Returns:
            DOMNode or None: The first matching node, or None if not found.
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
            elif selector_type == "xpath" :
                node_selector == node.get_node_xpath()
                # this is hard to implement since i don"t have access to the element text

            return False

        # Depth-first search starting from the root node
        stack = [self]
        while stack:
            current = stack.pop()
            if matches(current):
                return current
            stack.extend(reversed(current.children))

        return None
    
    def get_node_xpath(self):
        return
    
    def get_next_sibling(self):
        """Get the next sibling node."""
        if self.parent is None:
            return None
        idx = self.get_sibling_index()
        if idx + 1 < len(self.parent.children):
            return self.parent.children[idx + 1]
        return None
    
    def get_previous_sibling(self):
        """Get the previous sibling node."""
        if self.parent is None:
            return None
        idx = self.get_sibling_index()
        if idx > 0:
            return self.parent.children[idx - 1]
        return None
    
    def print_dom_tree(self,depth=0):
        indent = "  " * depth
        print(
            f'{indent}{self.tag} — classes: {self.classes}'
            + (f' — id: {self.attrs["id"]}' if "id" in self.attrs else "")
            +(f' — webElement: {self.web_element}')

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
