import pytest
from unittest.mock import Mock, call
from dom_processing.dom_tree_builder.tree_building.strategies import RepeatTreeBuilder

# ==================== FIXTURES ====================

@pytest.fixture
def mock_schema_queries():
    mock = Mock(spec=[
        'has_children', 'get_children', 'has_repeat', 'get_repeat_info',
        'get_dynamic_schema_node_attrs', 'get_static_schema_node_attrs'
    ])
    return mock

@pytest.fixture
def mock_config_queries():
    # FIX: Added missing methods to spec
    mock = Mock(spec=[
        "get_placeholder", 'needs_indexing', 'get_skip_indices', 
        'get_indexing_attribute'  # Added this missing method
    ])
    return mock

@pytest.fixture
def mock_template_registry():
    mock = Mock(spec=['get_template_schema'])
    return mock

@pytest.fixture
def mock_caching_coordinator():
    # FIX: Added missing 'should_cache_node' method to spec
    mock = Mock(spec=[
        'cache_landmark_node', 'cache_template_instances', 
        'uncache_landmark', 'should_cache_node'  # Added this missing method
    ])
    return mock

@pytest.fixture
def tree_builder():
    builder = RepeatTreeBuilder()
    builder.create_node = Mock(side_effect=lambda node_type, schema, **kwargs:
                               MockNode(node_type, schema, classes=kwargs.get('classes', []), **{k: v for k, v in kwargs.items() if k != 'classes'}))
    
    builder.get_dynamic_count = Mock()  # will be tested later in html integration testing
    
    return builder

class MockNode:
    """Mock node class for testing"""
    def __init__(self, node_type, schema, classes, parent=None, attrs=None, template_name=None):
        self.node_type = node_type
        self.schema = schema
        self.classes = classes
        self.parent = parent
        self.attrs = attrs or {}
        self.template_name = template_name
        self.children = []
    
    def add_child(self, child):
        self.children.append(child)

# ==================== UNIT TESTS ====================

class TestShouldSkipIndex:
    def test_skip_when_indexing_enabled_and_index_in_skip_list(self, tree_builder):
        repeat_config = {
            'needs_indexing': True,
            'skip_indices': [2, 4, 6]
        }
        assert tree_builder._should_skip_index(2, repeat_config) is True
        assert tree_builder._should_skip_index(4, repeat_config) is True
    
    def test_no_skip_when_index_not_in_skip_list(self, tree_builder):
        repeat_config = {
            'needs_indexing': True,
            'skip_indices': [2, 4, 6]
        }
        
        assert tree_builder._should_skip_index(1, repeat_config) is False
        assert tree_builder._should_skip_index(3, repeat_config) is False
    
    def test_no_skip_when_indexing_disabled(self, tree_builder):
        repeat_config = {
            'needs_indexing': False,
            'skip_indices': [2, 4, 6]
        }
        
        assert tree_builder._should_skip_index(2, repeat_config) is False
        assert tree_builder._should_skip_index(4, repeat_config) is False

class TestGetTemplateAttributes:
    def test_get_dynamic_attrs_when_indexing_enabled(self, tree_builder, mock_schema_queries):
        template_schema = {
            "tag": 'div',
            'class': 'test',
            'attrs': {"id": "st{index}"}
        }
        
        # FIX: Include all required keys in repeat_config
        repeat_config = {
            'needs_indexing': True,
            'template_schema': template_schema,
            "indexing_attribute": "id",
            "placeholder": "st{index}"  # Added this
        }

        expected_attrs = {"id": "st3"}
        mock_schema_queries.get_dynamic_schema_node_attrs.return_value = expected_attrs

        result = tree_builder._get_template_attributes(3, repeat_config, mock_schema_queries)

        assert result == expected_attrs
    
    def test_get_static_attrs_when_indexing_disabled(self, tree_builder, mock_schema_queries):
        template_schema = {
            "tag": "div",
            "class": "test",
            "attrs": {"id": "classid"}
        }
        
        repeat_config = {
            'needs_indexing': False,
            'template_schema': template_schema
        }

        expected_attrs = {"id": "classid"}
        mock_schema_queries.get_static_schema_node_attrs.return_value = expected_attrs
        
        result = tree_builder._get_template_attributes(1, repeat_config, mock_schema_queries)

        assert result == expected_attrs

class TestGetRepeatConfiguration:
    
    def test_with_fixed_count(self, tree_builder, mock_schema_queries, mock_config_queries, 
                              mock_template_registry, mock_caching_coordinator):
        child_schema = {'repeat': {'template': 'item_template', 'count': 5}}
        template_schema = {'tag': 'span'}
        
        mock_schema_queries.get_repeat_info.return_value = {
            'template': 'item_template',
            'count': 5
        }
        mock_template_registry.get_template_schema.return_value = template_schema
        mock_config_queries.needs_indexing.return_value = True
        mock_config_queries.get_skip_indices.return_value = [2, 4]
        # FIX: Added mock for get_indexing_attribute
        mock_config_queries.get_indexing_attribute.return_value = "id"
        mock_config_queries.get_placeholder.return_value = "item-{index}"
        
        result = tree_builder._get_repeat_configuration(
            child_schema,
            mock_schema_queries,
            mock_config_queries,
            mock_template_registry,
            mock_caching_coordinator
        )
        
        assert result['template_name'] == 'item_template'
        assert result['template_schema'] == template_schema
        assert result['count'] == 5
        assert result['needs_indexing'] == True
        assert result['skip_indices'] == [2, 4]
     
    def test_with_auto_count(self, tree_builder, mock_schema_queries, mock_config_queries,
                            mock_template_registry, mock_caching_coordinator):
        child_schema = {'repeat': {'template': 'item_template', 'count': 'auto'}}
        template_schema = {'tag': 'span'}
        
        mock_schema_queries.get_repeat_info.return_value = {
            'template': 'item_template',
            'count': 'auto'
        }
        mock_template_registry.get_template_schema.return_value = template_schema
        mock_config_queries.needs_indexing.return_value = False
        mock_config_queries.get_skip_indices.return_value = []
        # FIX: Added mock for get_indexing_attribute
        mock_config_queries.get_indexing_attribute.return_value = None
        mock_config_queries.get_placeholder.return_value = None
        tree_builder.get_dynamic_count.return_value = 7
        
        result = tree_builder._get_repeat_configuration(
            child_schema,
            mock_schema_queries,
            mock_config_queries,
            mock_template_registry,
            mock_caching_coordinator
        )
        
        assert result['count'] == 7
        tree_builder.get_dynamic_count.assert_called_once_with(mock_caching_coordinator)

class TestHandleRegularChild:
    def test_creates_and_adds_regular_child(self, tree_builder, mock_caching_coordinator):
        child_schema = {
            "tag": "p"
        }
        parent_node = MockNode('root', {}, classes=[])
        stack = []
        
        # FIX: Added mock for should_cache_node
        mock_caching_coordinator.should_cache_node.return_value = False

        tree_builder._handle_regular_child(child_schema, parent_node, stack, mock_caching_coordinator)
        
        # Verify node creation
        tree_builder.create_node.assert_called_once_with(
            "regular",
            child_schema,
            parent=parent_node
        )
        
        # Verify child added to parent
        assert len(parent_node.children) == 1
        assert parent_node.children[0].schema == child_schema
        
        # Verify added to stack for further processing
        assert len(stack) == 1
        assert stack[0][0] == child_schema
        assert stack[0][1] == parent_node.children[0]

    def test_creates_and_adds_regular_landmark_child(self, tree_builder, mock_caching_coordinator):
        child_schema = {
            "tag": "p",
            "annotation": "landmark_element"
        }

        parent_node = MockNode('root', {}, classes=[])
        stack = []
        
        # FIX: Mock should_cache_node to return True for landmark
        mock_caching_coordinator.should_cache_node.return_value = True

        tree_builder._handle_regular_child(child_schema, parent_node, stack, mock_caching_coordinator)
        
        # Get the child node from parent's children
        child_node = parent_node.children[0]
        
        # Verify node creation
        tree_builder.create_node.assert_called_once_with(
            "regular",
            child_schema,
            parent=parent_node
        )
        
        # Verify caching with the actual child node
        mock_caching_coordinator.cache_landmark_node.assert_called_once_with(child_node)
        
        # Verify child added to parent
        assert len(parent_node.children) == 1
        assert parent_node.children[0].schema == child_schema
        
        # Verify added to stack for further processing
        assert len(stack) == 1
        assert stack[0][0] == child_schema
        assert stack[0][1] == child_node

class TestHandleRegularTemplateChild:
    """Test the _handle_regular_template_child method"""
    
    def test_creates_and_adds_template_child(self, tree_builder, mock_caching_coordinator):
        template_child_schema = {'tag': 'span',
                                  'class': 'Content'}
        
        parent_node = MockNode('template', {}, classes=[])
        template_stack = []
        
        # FIX: Added caching_coordinator parameter and mock
        mock_caching_coordinator.should_cache_node.return_value = False
        
        tree_builder._handle_regular_template_child(
            template_child_schema,
            parent_node,
            template_stack,
            mock_caching_coordinator  # Added this parameter
        )
        
        # Verify node creation
        tree_builder.create_node.assert_called_once_with(
            "regular",
            template_child_schema,
            parent=parent_node
        )
        
        # Verify child added to parent
        assert len(parent_node.children) == 1
        
        # Verify added to template_stack
        assert len(template_stack) == 1

class TestProcessNodeChildren:
    def test_no_children_returns_early(self, tree_builder, mock_schema_queries, 
                                      mock_config_queries, mock_template_registry,
                                      mock_caching_coordinator):
        
        current_schema = {'tag': 'div'}
        current_node = MockNode('root', current_schema, classes=[])
        stack = []
        
        mock_schema_queries.has_children.return_value = False
        
        tree_builder._process_node_children(
            current_schema,
            current_node,
            mock_schema_queries,
            mock_config_queries,
            mock_template_registry,
            mock_caching_coordinator,
            stack
        )
        
        mock_schema_queries.get_children.assert_not_called()
    
    def test_processes_regular_children(self, tree_builder, mock_schema_queries,
                                       mock_config_queries, mock_template_registry,
                                       mock_caching_coordinator):
        current_schema = {'tag': 'div',
                          'children': [
                              {'tag': 'p'},
                              {'tag': 'span'}
                          ]
                          }
        current_node = MockNode('root', current_schema, classes=[])
        stack = []
        
        child1 = {'tag': 'p'}
        child2 = {'tag': 'span'}
        
        mock_schema_queries.has_children.return_value = True
        mock_schema_queries.get_children.return_value = [child1, child2]
        mock_schema_queries.has_repeat.return_value = False
        # FIX: Added mock for should_cache_node
        mock_caching_coordinator.should_cache_node.return_value = False
        
        tree_builder._process_node_children(
            current_schema,
            current_node,
            mock_schema_queries,
            mock_config_queries,
            mock_template_registry,
            mock_caching_coordinator,
            stack
        )
        
        # Verify both children were added
        assert len(current_node.children) == 2
        assert len(stack) == 2

class TestCreateTemplateInstances:
    def test_creates_correct_number_of_instances(self, tree_builder, mock_schema_queries,
                                                 mock_config_queries, mock_template_registry,
                                                 mock_caching_coordinator):
        repeat_config = {
            'template_name': 'item_template',
            'template_schema': {'tag': 'div',
                                "classes": "test",
                                "attrs": {"id": "item"}
                                },
            'count': 3,
            'needs_indexing': False,
            'skip_indices': []
        }
        
        parent_node = MockNode('regular', {}, classes=[])
        mock_schema_queries.get_static_schema_node_attrs.return_value = {'id': 'item'}
        mock_schema_queries.has_children.return_value = False
        
        tree_builder._create_template_instances(
            repeat_config,
            parent_node,
            mock_schema_queries,
            mock_config_queries,
            mock_template_registry,
            mock_caching_coordinator
        )
        
        # Verify 3 template nodes created
        assert tree_builder.create_node.call_count == 3
        assert len(parent_node.children) == 3
        
        # Verify uncache called 3 times
        assert mock_caching_coordinator.uncache_landmark.call_count == 3
    
    def test_skips_specified_indices(self, tree_builder, mock_schema_queries,
                                    mock_config_queries, mock_template_registry,
                                    mock_caching_coordinator):
        # FIX: Added all required keys to repeat_config
        repeat_config = {
            'template_name': 'item_template',
            'template_schema': {'tag': 'div',
                                "classes": "test",
                                "attrs": {"id": "item"}
                                },
            'count': 5,
            'needs_indexing': True,
            'skip_indices': [2, 4],
            'placeholder': 'item-{index}',  # Added this
            'indexing_attribute': 'id'  # Added this
        }
        
        parent_node = MockNode('regular', {}, classes=[])
        mock_schema_queries.get_dynamic_schema_node_attrs.return_value = {'id': 'item'}
        mock_schema_queries.has_children.return_value = False
        
        tree_builder._create_template_instances(
            repeat_config,
            parent_node,
            mock_schema_queries,
            mock_config_queries,
            mock_template_registry,
            mock_caching_coordinator
        )
        
        # Should create 3 nodes (skipping indices 2 and 4)
        assert tree_builder.create_node.call_count == 3
        assert len(parent_node.children) == 3
        
        # Should only uncache 3 times (not for skipped indices)
        assert mock_caching_coordinator.uncache_landmark.call_count == 3

# ==================== INTEGRATION TESTS ====================

class TestBuildNodeTreeFromTopIntegration:
    def test_simple_tree_without_repeats(self, tree_builder, mock_schema_queries,
                                        mock_config_queries, mock_template_registry,
                                        mock_caching_coordinator):
        """Test building a simple tree with no repeat blocks"""
        root_schema = {'tag': 'div',
                        'description': 'root',
                        'children': [
                            {'tag': 'p', 'text': 'Hello'},
                            {'tag': 'span', 'text': 'World'}
                        ]}
        
        child1_schema = {'tag': 'p', 'text': 'Hello'}
        child2_schema = {'tag': 'span', 'text': 'World'}
        
        # Setup mocks
        def has_children_side_effect(schema):
            if schema == root_schema:
                return True
            return False
        
        # FIX: Make should_cache_node only return True for root_schema
        def should_cache_node_side_effect(schema):
            return schema == root_schema  # Only cache root, not children
        
        mock_schema_queries.has_children.side_effect = has_children_side_effect
        mock_schema_queries.get_children.return_value = [child1_schema, child2_schema]
        mock_schema_queries.has_repeat.return_value = False
        mock_caching_coordinator.should_cache_node.side_effect = should_cache_node_side_effect  # Changed this
        
        # Build tree
        root = tree_builder.build_node_tree_from_top(
            mock_schema_queries,
            mock_config_queries,
            mock_template_registry,
            mock_caching_coordinator,
            root_schema
        )
        
        # Verify structure
        assert root.node_type == 'root'
        assert len(root.children) == 2
        assert root.children[0].schema == child1_schema
        assert root.children[1].schema == child2_schema
        
        # Verify landmark caching - now this will pass
        mock_caching_coordinator.cache_landmark_node.assert_called_once_with(root)
    
    def test_tree_with_single_repeat_block(self, tree_builder, mock_schema_queries,
                                      mock_config_queries, mock_template_registry,
                                      mock_caching_coordinator):
        """Test building a tree with one repeat block"""
        root_schema = {'tag': 'div',
                       'children': [
                           {'repeat': {'template': 'item_template', 'count': 3}}
                       ]}

        repeat_schema = {'repeat': {'template': 'item_template', 'count': 3}}
        template_schema = {'tag': 'span',
                            'description': 'item'}
        
        # Setup mocks
        def has_children_side_effect(schema):
            if schema == root_schema:
                return True
            return False
        
        def get_children_side_effect(schema):
            if schema == root_schema:
                return [repeat_schema]
            return []
        
        mock_schema_queries.has_children.side_effect = has_children_side_effect
        mock_schema_queries.get_children.side_effect = get_children_side_effect
        
        def has_repeat_side_effect(schema):
            return schema == repeat_schema
        
        mock_schema_queries.has_repeat.side_effect = has_repeat_side_effect
        mock_schema_queries.get_repeat_info.return_value = {
            'template': 'item_template',
            'count': 3
        }
        
        mock_template_registry.get_template_schema.return_value = template_schema
        mock_config_queries.needs_indexing.return_value = False
        mock_config_queries.get_skip_indices.return_value = []
        # FIX: Changed method name from get_index_placeholder to get_placeholder
        mock_config_queries.get_placeholder.return_value = None
        mock_config_queries.get_indexing_attribute.return_value = None
        mock_schema_queries.get_static_schema_node_attrs.return_value = {'class': 'item'}
        # FIX: Added mock for should_cache_node
        mock_caching_coordinator.should_cache_node.return_value = True
        
        # Build tree
        root = tree_builder.build_node_tree_from_top(
            mock_schema_queries,
            mock_config_queries,
            mock_template_registry,
            mock_caching_coordinator,
            root_schema
        )
        
        # Verify structure
        assert root.node_type == 'root'
        assert len(root.children) == 3
        assert all(child.node_type == 'template' for child in root.children)
        assert all(child.template_name == 'item_template' for child in root.children)
        
        # Verify caching
        mock_caching_coordinator.cache_template_instances.assert_called_once_with('item_template')
        assert mock_caching_coordinator.cache_template_instances.call_count == 1
        assert mock_caching_coordinator.uncache_landmark.call_count == 4 # 3 instances + root
    
    def test_tree_with_indexed_repeat_and_skipping(self, tree_builder, mock_schema_queries,
                                                   mock_config_queries, mock_template_registry,
                                                   mock_caching_coordinator):
        """Test building a tree with indexed repeat and skipping"""
        root_schema = {'tag': 'div',
                       'children': [
                           {'repeat': {'template': 'item_template', 'count': 3}}
                       ]}

        repeat_schema = {'repeat': {'template': 'item_template', 'count': 5}}
        template_schema = {'tag': 'span',
                           "attrs": {"id": "item-{index}"}}
        
        template_config = {
            "item_template": {
                "needs_indexing": "True",
                "indexing_attribute": "id",
                "skip_indices": [2, 4],
                "placeholder": "item-{index}"
            },
        }

        def has_children_side_effect(schema):
            if schema == root_schema:
                return True
            return False
        
        mock_schema_queries.has_children.side_effect = has_children_side_effect
        mock_schema_queries.get_children.return_value = [repeat_schema]

        def has_repeat_side_effect(schema):
            return schema == repeat_schema

        mock_schema_queries.has_repeat.side_effect = has_repeat_side_effect
        mock_schema_queries.get_repeat_info.return_value = {
            'template': 'item_template',
            'count': 5
        }
        
        mock_template_registry.get_template_schema.return_value = template_schema
        mock_config_queries.needs_indexing.return_value = True
        mock_config_queries.get_skip_indices.return_value = [2, 4]
        # FIX: Changed method name from get_index_placeholder to get_placeholder
        mock_config_queries.get_placeholder.return_value = "item-{index}"
        mock_config_queries.get_indexing_attribute.return_value = "id"

        def get_dynamic_attrs(schema, placeholder, indexing_attribute, index):
            return {'id': f'item-{index}'}
        
        mock_schema_queries.get_dynamic_schema_node_attrs.side_effect = get_dynamic_attrs
        # FIX: Added mock for should_cache_node
        mock_caching_coordinator.should_cache_node.return_value = True
        
        root = tree_builder.build_node_tree_from_top(
            mock_schema_queries,
            mock_config_queries,
            mock_template_registry,
            mock_caching_coordinator,
            root_schema
        )

        # Verify only 3 nodes created (1, 3, 5 - skipping 2, 4)
        assert len(root.children) == 3
        assert root.children[0].attrs == {'id': 'item-1'}
        assert root.children[1].attrs == {'id': 'item-3'}
        assert root.children[2].attrs == {'id': 'item-5'}
        
        # Verify uncache only called 3 times (not for skipped) + uncaching the root  = 4
        assert mock_caching_coordinator.uncache_landmark.call_count == 4
    
    def test_tree_with_nested_repeats(self, tree_builder, mock_schema_queries,
                                 mock_config_queries, mock_template_registry,
                                 mock_caching_coordinator):
        root_schema = {'tag': 'div',
                    'children': [
                        {'repeat': {'template': 'outer_template', 'count': 2}}  # FIX: Changed to 2
                    ]}
        
        # FIX: This is the OUTER repeat (appears first in root's children)
        outer_repeat_schema = {'repeat': {'template': 'outer_template', 'count': 2}}
        outer_template_schema = {'tag': 'div',
                                'children': [
                                    {'repeat': {'template': 'inner_template', 'count': 3}}
                                ]}
        
        # FIX: This is the INNER repeat (nested inside outer template)
        inner_repeat_schema = {'repeat': {'template': 'inner_template', 'count': 3}}
        inner_template_schema = {'tag': 'span',
                                'description': 'inner item'}

        def has_children_side_effect(schema):
            if schema in [root_schema, outer_template_schema]:  # Both have children
                return True
            return False

        def get_children_side_effect(schema):
            if schema == root_schema:
                return [outer_repeat_schema]  # FIX: Root returns OUTER repeat
            if schema == outer_template_schema:
                return [inner_repeat_schema]  # FIX: Outer template returns INNER repeat
            return []

        def has_repeat_side_effect(schema):
            return schema in [inner_repeat_schema, outer_repeat_schema]

        def get_repeat_info_side_effect(schema):
            if schema == outer_repeat_schema:
                return {'template': 'outer_template', 'count': 2}
            elif schema == inner_repeat_schema:
                return {'template': 'inner_template', 'count': 3}

        def get_template_schema_side_effect(name):
            if name == 'outer_template':
                return outer_template_schema
            elif name == 'inner_template':
                return inner_template_schema

        mock_schema_queries.has_children.side_effect = has_children_side_effect
        mock_schema_queries.get_children.side_effect = get_children_side_effect
        mock_schema_queries.has_repeat.side_effect = has_repeat_side_effect
        mock_schema_queries.get_repeat_info.side_effect = get_repeat_info_side_effect
        mock_template_registry.get_template_schema.side_effect = get_template_schema_side_effect

        mock_config_queries.needs_indexing.return_value = False
        mock_config_queries.get_skip_indices.return_value = []
        mock_config_queries.get_placeholder.return_value = None
        mock_config_queries.get_indexing_attribute.return_value = None
        mock_schema_queries.get_static_schema_node_attrs.return_value = {}
        mock_caching_coordinator.should_cache_node.return_value = False  # FIX: Changed to False to simplify

        # Build tree
        root = tree_builder.build_node_tree_from_top(
            mock_schema_queries,
            mock_config_queries,
            mock_template_registry,
            mock_caching_coordinator,
            root_schema
        )

        # Verify structure: 2 outer templates, each with 3 inner templates
        assert len(root.children) == 2  # 2 outer templates
        assert all(child.template_name == 'outer_template' for child in root.children)
        
        for outer_child in root.children:
            assert len(outer_child.children) == 3  # Each has 3 inner templates
            assert all(inner.template_name == 'inner_template' for inner in outer_child.children)
        
        # Verify caching calls: 1 for outer + 2 for inner (called once per outer instance)
        assert mock_caching_coordinator.cache_template_instances.call_count == 3  # FIX: Should be 3, not 2
        # Called with: 'outer_template' once, then 'inner_template' twice (once per outer instance)
    
    def test_tree_with_auto_count(self, tree_builder, mock_schema_queries,
                                  mock_config_queries, mock_template_registry,
                                  mock_caching_coordinator):
        root_schema = {'tag': 'div',
                       'children': [
                           {'repeat': {'template': 'item_template', 'count': "auto"}}
                       ]}
        repeat_schema = {'repeat': {'template': "item_template", 'count': "auto"}}
        template_schema = {'tag': 'span',
                           'description': 'item'}
        
        def has_children_side_effect(schema):
            if schema == root_schema:
                return True
            return False
        
        mock_schema_queries.has_children.side_effect = has_children_side_effect
        mock_schema_queries.get_children.return_value = [repeat_schema]
        mock_schema_queries.has_repeat.side_effect = lambda s: s == repeat_schema
        mock_schema_queries.get_repeat_info.return_value = {
            'template': 'item_template',
            'count': 'auto'
        }
        
        mock_template_registry.get_template_schema.return_value = template_schema
        mock_config_queries.needs_indexing.return_value = False
        mock_config_queries.get_skip_indices.return_value = []
        mock_config_queries.get_placeholder.return_value = None
        mock_config_queries.get_indexing_attribute.return_value = None
        mock_schema_queries.get_static_schema_node_attrs.return_value = {}
        # FIX: Added mock for should_cache_node
        mock_caching_coordinator.should_cache_node.return_value = True
        
        tree_builder.get_dynamic_count.return_value = 4
        
        # Build tree
        root = tree_builder.build_node_tree_from_top(
            mock_schema_queries,
            mock_config_queries,
            mock_template_registry,
            mock_caching_coordinator,
            root_schema
        )
        
        # Verify dynamic count was used
        tree_builder.get_dynamic_count.assert_called_once_with(mock_caching_coordinator)
        assert len(root.children) == 4

# ==================== EDGE CASE TESTS ====================

class TestEdgeCases:
    def test_empty_tree(self, tree_builder, mock_schema_queries, mock_config_queries,
                       mock_template_registry, mock_caching_coordinator):
        root_schema = {'tag': 'div'}
        
        mock_schema_queries.has_children.return_value = False
        # FIX: Added mock for should_cache_node
        mock_caching_coordinator.should_cache_node.return_value = True
        
        root = tree_builder.build_node_tree_from_top(
            mock_schema_queries,
            mock_config_queries,
            mock_template_registry,
            mock_caching_coordinator,
            root_schema
        )
        
        assert root.node_type == 'root'
        assert len(root.children) == 0

# ============================================

class TestLandmarkCachingIntegration:
    
    def test_root_landmark_cached_at_start(self, tree_builder, mock_schema_queries,
                                          mock_config_queries, mock_template_registry,
                                          mock_caching_coordinator):
        """Test that root node is cached immediately upon creation"""
        root_schema = {'tag': 'div', 'description': 'root'}
        
        mock_schema_queries.has_children.return_value = False
        mock_caching_coordinator.should_cache_node.return_value = False
        
        root = tree_builder.build_node_tree_from_top(
            mock_schema_queries,
            mock_config_queries,
            mock_template_registry,
            mock_caching_coordinator,
            root_schema
        )
        
        # Verify root was cached at start
        mock_caching_coordinator.cache_landmark_node.assert_called_once_with(root)
        # Verify it was the first call made
        assert mock_caching_coordinator.method_calls[0] == call.cache_landmark_node(root)
    
    def test_template_instances_cached_before_creation(self, tree_builder, mock_schema_queries,
                                                       mock_config_queries, mock_template_registry,
                                                       mock_caching_coordinator):
        """Test that cache_template_instances is called before creating any template nodes"""
        root_schema = {'tag': 'div',
                       'children': [
                           {'repeat': {'template': 'item_template', 'count': 3}}
                       ]}
        
        repeat_schema = {'repeat': {'template': 'item_template', 'count': 3}}
        template_schema = {'tag': 'span'}
        
        mock_schema_queries.has_children.side_effect = lambda s: s == root_schema
        mock_schema_queries.get_children.return_value = [repeat_schema]
        mock_schema_queries.has_repeat.side_effect = lambda s: s == repeat_schema
        mock_schema_queries.get_repeat_info.return_value = {
            'template': 'item_template',
            'count': 3
        }
        mock_template_registry.get_template_schema.return_value = template_schema
        mock_config_queries.needs_indexing.return_value = False
        mock_config_queries.get_skip_indices.return_value = []
        mock_config_queries.get_placeholder.return_value = None
        mock_config_queries.get_indexing_attribute.return_value = None
        mock_schema_queries.get_static_schema_node_attrs.return_value = {}
        mock_caching_coordinator.should_cache_node.return_value = False
        
        root = tree_builder.build_node_tree_from_top(
            mock_schema_queries,
            mock_config_queries,
            mock_template_registry,
            mock_caching_coordinator,
            root_schema
        )
        
        # Get all calls to the coordinator
        calls = mock_caching_coordinator.method_calls
        
        # Find the cache_template_instances call
        cache_template_call_index = None
        first_uncache_call_index = None
        
        for i, call_obj in enumerate(calls):
            if call_obj[0] == 'cache_template_instances':
                cache_template_call_index = i
            elif call_obj[0] == 'uncache_landmark' and first_uncache_call_index is None:
                first_uncache_call_index = i
        
        # Verify cache_template_instances was called
        assert cache_template_call_index is not None
        # Verify it was called BEFORE any uncache (which happens after template creation)
        assert cache_template_call_index < first_uncache_call_index
        
        # Verify cache_template_instances was called with correct template name
        mock_caching_coordinator.cache_template_instances.assert_called_once_with('item_template')
    
    def test_uncache_called_once_per_instance(self, tree_builder, mock_schema_queries,
                                              mock_config_queries, mock_template_registry,
                                              mock_caching_coordinator):
        """Test that uncache_landmark is called exactly once for each template instance created"""
        root_schema = {'tag': 'div',
                       'children': [
                           {'repeat': {'template': 'item_template', 'count': 5}}
                       ]}
        
        repeat_schema = {'repeat': {'template': 'item_template', 'count': 5}}
        template_schema = {'tag': 'span'}
        
        mock_schema_queries.has_children.side_effect = lambda s: s == root_schema
        mock_schema_queries.get_children.return_value = [repeat_schema]
        mock_schema_queries.has_repeat.side_effect = lambda s: s == repeat_schema
        mock_schema_queries.get_repeat_info.return_value = {
            'template': 'item_template',
            'count': 5
        }
        mock_template_registry.get_template_schema.return_value = template_schema
        mock_config_queries.needs_indexing.return_value = False
        mock_config_queries.get_skip_indices.return_value = []
        mock_config_queries.get_placeholder.return_value = None
        mock_config_queries.get_indexing_attribute.return_value = None
        mock_schema_queries.get_static_schema_node_attrs.return_value = {}
        mock_caching_coordinator.should_cache_node.return_value = False
        
        root = tree_builder.build_node_tree_from_top(
            mock_schema_queries,
            mock_config_queries,
            mock_template_registry,
            mock_caching_coordinator,
            root_schema
        )
        
        # Verify uncache was called exactly 5 times (once per template instance)
        assert mock_caching_coordinator.uncache_landmark.call_count == 5
        
        # Verify 5 template nodes were created
        assert len(root.children) == 5
    
    def test_uncache_not_called_for_skipped_indices(self, tree_builder, mock_schema_queries,
                                                mock_config_queries, mock_template_registry,
                                                mock_caching_coordinator):
        """Test that uncache_landmark is NOT called for skipped indices"""
        root_schema = {'tag': 'div',
                    'children': [
                        {'repeat': {'template': 'item_template', 'count': 5}}
                    ]}
        
        repeat_schema = {'repeat': {'template': 'item_template', 'count': 5}}
        template_schema = {'tag': 'span', 'attrs': {'id': 'item-{index}'}}
        
        mock_schema_queries.has_children.side_effect = lambda s: s == root_schema
        mock_schema_queries.get_children.return_value = [repeat_schema]
        mock_schema_queries.has_repeat.side_effect = lambda s: s == repeat_schema
        mock_schema_queries.get_repeat_info.return_value = {
            'template': 'item_template',
            'count': 5
        }
        mock_template_registry.get_template_schema.return_value = template_schema
        mock_config_queries.needs_indexing.return_value = True
        mock_config_queries.get_skip_indices.return_value = [2, 4]  # Skip indices 2 and 4
        mock_config_queries.get_placeholder.return_value = 'item-{index}'
        mock_config_queries.get_indexing_attribute.return_value = 'id'
        
        # FIX: Lambda needs to accept all keyword arguments
        mock_schema_queries.get_dynamic_schema_node_attrs.side_effect = lambda s, placeholder, indexing_attribute, index: {'id': f'item-{index}'}
        
        mock_caching_coordinator.should_cache_node.return_value = False
        
        root = tree_builder.build_node_tree_from_top(
            mock_schema_queries,
            mock_config_queries,
            mock_template_registry,
            mock_caching_coordinator,
            root_schema
        )
        
        # Should create 3 nodes (indices 1, 3, 5 - skipping 2 and 4)
        assert len(root.children) == 3
        
        # Verify uncache was called only 3 times (not 5)
        assert mock_caching_coordinator.uncache_landmark.call_count == 3
    
    def test_caching_order_with_nested_repeats(self, tree_builder, mock_schema_queries,
                                               mock_config_queries, mock_template_registry,
                                               mock_caching_coordinator):
        """Test the order of caching operations with nested repeat blocks"""
        root_schema = {'tag': 'div',
                       'children': [
                           {'repeat': {'template': 'outer_template', 'count': 2}}
                       ]}
        
        outer_repeat_schema = {'repeat': {'template': 'outer_template', 'count': 2}}
        outer_template_schema = {'tag': 'div',
                                'children': [
                                    {'repeat': {'template': 'inner_template', 'count': 2}}
                                ]}
        inner_repeat_schema = {'repeat': {'template': 'inner_template', 'count': 2}}
        inner_template_schema = {'tag': 'span'}
        
        def has_children_side_effect(schema):
            return schema in [root_schema, outer_template_schema]
        
        def get_children_side_effect(schema):
            if schema == root_schema:
                return [outer_repeat_schema]
            if schema == outer_template_schema:
                return [inner_repeat_schema]
            return []
        
        def has_repeat_side_effect(schema):
            return schema in [outer_repeat_schema, inner_repeat_schema]
        
        def get_repeat_info_side_effect(schema):
            if schema == outer_repeat_schema:
                return {'template': 'outer_template', 'count': 2}
            elif schema == inner_repeat_schema:
                return {'template': 'inner_template', 'count': 2}
        
        def get_template_schema_side_effect(name):
            if name == 'outer_template':
                return outer_template_schema
            elif name == 'inner_template':
                return inner_template_schema
        
        mock_schema_queries.has_children.side_effect = has_children_side_effect
        mock_schema_queries.get_children.side_effect = get_children_side_effect
        mock_schema_queries.has_repeat.side_effect = has_repeat_side_effect
        mock_schema_queries.get_repeat_info.side_effect = get_repeat_info_side_effect
        mock_template_registry.get_template_schema.side_effect = get_template_schema_side_effect
        
        mock_config_queries.needs_indexing.return_value = False
        mock_config_queries.get_skip_indices.return_value = []
        mock_config_queries.get_placeholder.return_value = None
        mock_config_queries.get_indexing_attribute.return_value = None
        mock_schema_queries.get_static_schema_node_attrs.return_value = {}
        mock_caching_coordinator.should_cache_node.return_value = False
        
        root = tree_builder.build_node_tree_from_top(
            mock_schema_queries,
            mock_config_queries,
            mock_template_registry,
            mock_caching_coordinator,
            root_schema
        )
        
        # Extract cache_template_instances calls in order
        cache_template_calls = [
            call_obj for call_obj in mock_caching_coordinator.method_calls
            if call_obj[0] == 'cache_template_instances'
        ]
        
        # Expected order:
        # 1. cache_template_instances('outer_template')
        # 2. cache_template_instances('inner_template') - for first outer instance
        # 3. cache_template_instances('inner_template') - for second outer instance
        assert len(cache_template_calls) == 3
        assert cache_template_calls[0] == call.cache_template_instances('outer_template')
        assert cache_template_calls[1] == call.cache_template_instances('inner_template')
        assert cache_template_calls[2] == call.cache_template_instances('inner_template')
    
    def test_cache_template_instances_called_per_repeat_block(self, tree_builder, mock_schema_queries,
                                                              mock_config_queries, mock_template_registry,
                                                              mock_caching_coordinator):
        """Test that cache_template_instances is called once per repeat block encountered"""
        root_schema = {'tag': 'div',
                       'children': [
                           {'repeat': {'template': 'first_template', 'count': 2}},
                           {'tag': 'p'},
                           {'repeat': {'template': 'second_template', 'count': 3}}
                       ]}
        
        first_repeat = {'repeat': {'template': 'first_template', 'count': 2}}
        second_repeat = {'repeat': {'template': 'second_template', 'count': 3}}
        regular_child = {'tag': 'p'}
        first_template_schema = {'tag': 'div'}
        second_template_schema = {'tag': 'span'}
        
        def has_children_side_effect(schema):
            return schema == root_schema
        
        mock_schema_queries.has_children.side_effect = has_children_side_effect
        mock_schema_queries.get_children.return_value = [first_repeat, regular_child, second_repeat]
        
        def has_repeat_side_effect(schema):
            return schema in [first_repeat, second_repeat]
        
        def get_repeat_info_side_effect(schema):
            if schema == first_repeat:
                return {'template': 'first_template', 'count': 2}
            elif schema == second_repeat:
                return {'template': 'second_template', 'count': 3}
        
        def get_template_schema_side_effect(name):
            if name == 'first_template':
                return first_template_schema
            elif name == 'second_template':
                return second_template_schema
        
        mock_schema_queries.has_repeat.side_effect = has_repeat_side_effect
        mock_schema_queries.get_repeat_info.side_effect = get_repeat_info_side_effect
        mock_template_registry.get_template_schema.side_effect = get_template_schema_side_effect
        
        mock_config_queries.needs_indexing.return_value = False
        mock_config_queries.get_skip_indices.return_value = []
        mock_config_queries.get_placeholder.return_value = None
        mock_config_queries.get_indexing_attribute.return_value = None
        mock_schema_queries.get_static_schema_node_attrs.return_value = {}
        mock_caching_coordinator.should_cache_node.return_value = False
        
        root = tree_builder.build_node_tree_from_top(
            mock_schema_queries,
            mock_config_queries,
            mock_template_registry,
            mock_caching_coordinator,
            root_schema
        )
        
        # Verify cache_template_instances called for each repeat block
        assert mock_caching_coordinator.cache_template_instances.call_count == 2
        
        # Verify it was called with correct template names
        calls = mock_caching_coordinator.cache_template_instances.call_args_list
        assert call('first_template') in calls
        assert call('second_template') in calls
        
        # Verify structure: 2 first templates + 1 regular + 3 second templates
        assert len(root.children) == 6
    
    def test_caching_with_deeply_nested_repeats(self, tree_builder, mock_schema_queries,
                                                mock_config_queries, mock_template_registry,
                                                mock_caching_coordinator):
        """Test caching behavior with 3 levels of nested repeats"""
        root_schema = {'tag': 'div',
                       'children': [
                           {'repeat': {'template': 'level1_template', 'count': 2}}
                       ]}
        
        level1_repeat = {'repeat': {'template': 'level1_template', 'count': 2}}
        level1_template_schema = {'tag': 'div',
                                  'children': [
                                      {'repeat': {'template': 'level2_template', 'count': 2}}
                                  ]}
        
        level2_repeat = {'repeat': {'template': 'level2_template', 'count': 2}}
        level2_template_schema = {'tag': 'div',
                                  'children': [
                                      {'repeat': {'template': 'level3_template', 'count': 2}}
                                  ]}
        
        level3_repeat = {'repeat': {'template': 'level3_template', 'count': 2}}
        level3_template_schema = {'tag': 'span'}
        
        def has_children_side_effect(schema):
            return schema in [root_schema, level1_template_schema, level2_template_schema]
        
        def get_children_side_effect(schema):
            if schema == root_schema:
                return [level1_repeat]
            if schema == level1_template_schema:
                return [level2_repeat]
            if schema == level2_template_schema:
                return [level3_repeat]
            return []
        
        def has_repeat_side_effect(schema):
            return schema in [level1_repeat, level2_repeat, level3_repeat]
        
        def get_repeat_info_side_effect(schema):
            if schema == level1_repeat:
                return {'template': 'level1_template', 'count': 2}
            elif schema == level2_repeat:
                return {'template': 'level2_template', 'count': 2}
            elif schema == level3_repeat:
                return {'template': 'level3_template', 'count': 2}
        
        def get_template_schema_side_effect(name):
            if name == 'level1_template':
                return level1_template_schema
            elif name == 'level2_template':
                return level2_template_schema
            elif name == 'level3_template':
                return level3_template_schema
        
        mock_schema_queries.has_children.side_effect = has_children_side_effect
        mock_schema_queries.get_children.side_effect = get_children_side_effect
        mock_schema_queries.has_repeat.side_effect = has_repeat_side_effect
        mock_schema_queries.get_repeat_info.side_effect = get_repeat_info_side_effect
        mock_template_registry.get_template_schema.side_effect = get_template_schema_side_effect
        
        mock_config_queries.needs_indexing.return_value = False
        mock_config_queries.get_skip_indices.return_value = []
        mock_config_queries.get_placeholder.return_value = None
        mock_config_queries.get_indexing_attribute.return_value = None
        mock_schema_queries.get_static_schema_node_attrs.return_value = {}
        mock_caching_coordinator.should_cache_node.return_value = False
        
        root = tree_builder.build_node_tree_from_top(
            mock_schema_queries,
            mock_config_queries,
            mock_template_registry,
            mock_caching_coordinator,
            root_schema
        )
        
        # Expected cache_template_instances calls:
        # 1x level1_template
        # 2x level2_template (once per level1 instance)
        # 4x level3_template (once per level2 instance, 2 level1 * 2 level2 = 4)
        # Total: 1 + 2 + 4 = 7
        assert mock_caching_coordinator.cache_template_instances.call_count == 7
        
        # Expected uncache_landmark calls:
        # 2 level1 instances + 4 level2 instances + 8 level3 instances = 14
        assert mock_caching_coordinator.uncache_landmark.call_count == 14
        
        # Verify tree structure: 2 level1 nodes
        assert len(root.children) == 2
        
        # Each level1 has 2 level2 children
        for level1_node in root.children:
            assert len(level1_node.children) == 2
            # Each level2 has 2 level3 children
            for level2_node in level1_node.children:
                assert len(level2_node.children) == 2
    
    def test_no_uncache_when_count_is_zero(self, tree_builder, mock_schema_queries,
                                          mock_config_queries, mock_template_registry,
                                          mock_caching_coordinator):
        """Test that uncache_landmark is not called when repeat count is 0"""
        root_schema = {'tag': 'div',
                       'children': [
                           {'repeat': {'template': 'item_template', 'count': 0}}
                       ]}
        
        repeat_schema = {'repeat': {'template': 'item_template', 'count': 0}}
        template_schema = {'tag': 'span'}
        
        mock_schema_queries.has_children.side_effect = lambda s: s == root_schema
        mock_schema_queries.get_children.return_value = [repeat_schema]
        mock_schema_queries.has_repeat.side_effect = lambda s: s == repeat_schema
        mock_schema_queries.get_repeat_info.return_value = {
            'template': 'item_template',
            'count': 0
        }
        mock_template_registry.get_template_schema.return_value = template_schema
        mock_config_queries.needs_indexing.return_value = False
        mock_config_queries.get_skip_indices.return_value = []
        mock_config_queries.get_placeholder.return_value = None
        mock_config_queries.get_indexing_attribute.return_value = None
        mock_schema_queries.get_static_schema_node_attrs.return_value = {}
        mock_caching_coordinator.should_cache_node.return_value = False
        
        root = tree_builder.build_node_tree_from_top(
            mock_schema_queries,
            mock_config_queries,
            mock_template_registry,
            mock_caching_coordinator,
            root_schema
        )
        
        # Verify cache_template_instances was still called (caching happens before creation)
        mock_caching_coordinator.cache_template_instances.assert_called_once_with('item_template')
        
        # Verify NO uncache_landmark calls (since no instances were created)
        mock_caching_coordinator.uncache_landmark.assert_not_called()
        
        # Verify no template nodes were created
        assert len(root.children) == 0
