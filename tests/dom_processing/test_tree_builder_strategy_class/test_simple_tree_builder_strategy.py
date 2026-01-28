import pytest
from unittest.mock import Mock

from dom_processing.dom_tree_builder.tree_building.strategies import SimpleTreeBuilderStrategy 

class TestSimpleTreeBuilderStrategy:

    def test_single_root_no_children(self):

        builder = SimpleTreeBuilderStrategy()
        schema_queries = Mock()
        schema_node = {
            "tag": "div",
            "description": "root"
        }

        schema_queries.has_children.return_value = False

        result = builder.build_node_tree_from_top(schema_queries,schema_node)

        assert result is not None

        schema_queries.has_children.assert_called_once_with(schema_node)
    
    def test_root_with_single_children(self):
        builder = SimpleTreeBuilderStrategy()
        schema_queries = Mock()

        root_schema = {
            "tag": "div",
            "description": "root",
            "children": [
                {
                    "tag": "span",
                    "description": "child1"
                }
            ]
        }

        child_schema = {
            "tag": "span",
            "description": "child1"
        }
        
        def has_children_side_effect(node):
            return node.get("description") == "root"
        
        schema_queries.has_children.side_effect = has_children_side_effect
        schema_queries.get_children.return_value = [child_schema]

        # Don't mock create_node - let it run for real
        result = builder.build_node_tree_from_top(schema_queries, root_schema)

        # Now test the actual nodes created
        assert result is not None
        assert len(result.children) == 1
        child = result.children[0]
        assert child.parent == result

    def test_multiple_children_order(self):
        builder = SimpleTreeBuilderStrategy()
        schema_queries = Mock()
        root_schema = {
            "tag":"div",
            "description":"root",
            "children":[
                {"tag":"span","description":"child1"},
                {"tag":"span","description":"child2"},
                {"tag":"span","description":"child3"}
            ]
        }

        child_schema_1 = {"tag":"span","description":"child1"}
        child_schema_2 = {"tag":"span","description":"child2"}  
        child_schema_3 = {"tag":"span","description":"child3"}

        def has_children_side_effect(node):
            return node.get("description") == "root"
        
        schema_queries.has_children.side_effect = has_children_side_effect
        schema_queries.get_children.return_value = [
            child_schema_1,
            child_schema_2,
            child_schema_3
        ]
        result = builder.build_node_tree_from_top(schema_queries, root_schema)
        assert result is not None
        assert len(result.children) == 3
        assert result.children[0].description == "child1"
        assert result.children[1].description == "child2"
        assert result.children[2].description == "child3"
    
    def test_multiple_level_children_order(self):
        builder = SimpleTreeBuilderStrategy()
        schema_queries = Mock()
        root_schema = {
            "tag":"div",
            "description":"root",
            "children":[
                {
                    "tag":"section",
                    "description":"child1",
                    "children":[
                        {"tag":"p","description":"grandchild1"},
                        {"tag":"p","description":"grandchild2"}
                    ]
                },
                {"tag":"span","description":"child2"}
            ]
        }

        child_schema_1 = {
            "tag":"section",
            "description":"child1",
            "children":[
                {"tag":"p","description":"grandchild1"},
                {"tag":"p","description":"grandchild2"}
            ]
        }
        child_schema_2 = {"tag":"span","description":"child2"}  

        grandchild_schema_1 = {"tag":"p","description":"grandchild1"}
        grandchild_schema_2 = {"tag":"p","description":"grandchild2"}

        def has_children_side_effect(node):
            return node.get("description") in ["root", "child1"]
        
        def get_children_side_effect(node):
            if node.get("description") == "root":
                return [child_schema_1, child_schema_2]
            elif node.get("description") == "child1":
                return [grandchild_schema_1, grandchild_schema_2]
            return []
        
        schema_queries.has_children.side_effect = has_children_side_effect
        schema_queries.get_children.side_effect = get_children_side_effect

        result = builder.build_node_tree_from_top(schema_queries, root_schema)

        assert result is not None
        assert len(result.children) == 2
        child1 = result.children[0]
        child2 = result.children[1]
        assert child1.description == "child1"
        assert child2.description == "child2"
        assert len(child1.children) == 2
        grandchild1 = child1.children[0]
        grandchild2 = child1.children[1]
        assert grandchild1.description == "grandchild1"
        assert grandchild2.description == "grandchild2"







        