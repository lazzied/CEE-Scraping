import copy


def clone_tree_structure(node):
    """Recursively clone tree structure without web elements."""
    new_node = copy.copy(node)
    
    if hasattr(new_node, 'web_element'):
        new_node.web_element = None
    
    if hasattr(node, 'children') and node.children:
        new_node.children = [clone_tree_structure(child) for child in node.children]
    
    return new_node
