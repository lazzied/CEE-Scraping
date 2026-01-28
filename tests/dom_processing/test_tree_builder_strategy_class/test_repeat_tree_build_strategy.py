import pytest
from unittest.mock import Mock, MagicMock, call, patch


# ==================== FIXTURES ====================

@pytest.fixture
def mock_schema_queries():
    mock = Mock(spec=['has_children', 'get_children', 'has_repeat', 'get_repeat_info',
                      'get_dynamic_schema_node_attrs', 'get_static_schema_node_attrs'])
    return mock


@pytest.fixture
def mock_config_queries():
    mock = Mock(spec=['needs_indexing', 'get_skip_indices'])
    return mock


@pytest.fixture
def mock_template_registry():
    mock = Mock(spec=['get_template_schema'])
    return mock


@pytest.fixture
def mock_caching_coordinator():
    mock = Mock(spec=['cache_landmark_node', 'cache_template_instances', 'uncache_landmark'])
    return mock


@pytest.fixture
def tree_builder():
    """Fixture that provides a tree builder instance with mocked create_node"""
    builder = TreeBuilder()
    builder.create_node = Mock(side_effect=lambda node_type, schema, **kwargs: 
                               MockNode(node_type, schema, **kwargs))
    builder.get_dynamic_count = Mock(return_value=3)
    return builder


class MockNode:
    """Mock node class for testing"""
    def __init__(self, node_type, schema, parent=None, attrs=None, template_name=None):
        self.node_type = node_type
        self.schema = schema
        self.parent = parent
        self.attrs = attrs or {}
        self.template_name = template_name
        self.children = []
    
    def add_child(self, child):
        self.children.append(child)


class TreeBuilder:
    """Placeholder for the actual TreeBuilder class"""
    def create_node(self, node_type, schema, **kwargs):
        pass
    
    def get_dynamic_count(self, caching_coordinator):
        pass


# ==================== UNIT TESTS ====================

class TestShouldSkipIndex:
    """Test the _should_skip_index method"""
    
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
    """Test the _get_template_attributes method"""
    
    def test_get_dynamic_attrs_when_indexing_enabled(self, tree_builder, mock_schema_queries):
        template_schema = {'tag': 'div'}
        repeat_config = {
            'needs_indexing': True,
            'template_schema': template_schema
        }
        
        expected_attrs = {'id': 'item-3', 'text': 'Item 3'}
        mock_schema_queries.get_dynamic_schema_node_attrs.return_value = expected_attrs
        
        result = tree_builder._get_template_attributes(3, repeat_config, mock_schema_queries)
        
        assert result == expected_attrs
        mock_schema_queries.get_dynamic_schema_node_attrs.assert_called_once_with(
            template_schema,
            placeholder="{index}",
            index=3
        )
    
    def test_get_static_attrs_when_indexing_disabled(self, tree_builder, mock_schema_queries):
        template_schema = {'tag': 'div'}
        repeat_config = {
            'needs_indexing': False,
            'template_schema': template_schema
        }
        
        expected_attrs = {'class': 'static-item'}
        mock_schema_queries.get_static_schema_node_attrs.return_value = expected_attrs
        
        result = tree_builder._get_template_attributes(3, repeat_config, mock_schema_queries)
        
        assert result == expected_attrs
        mock_schema_queries.get_static_schema_node_attrs.assert_called_once_with(template_schema)


class TestGetRepeatConfiguration:
    """Test the _get_repeat_configuration method"""
    
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
        
        result = tree_builder._get_repeat_configuration(
            child_schema,
            mock_schema_queries,
            mock_config_queries,
            mock_template_registry,
            mock_caching_coordinator
        )
        
        assert result == {
            'template_name': 'item_template',
            'template_schema': template_schema,
            'count': 5,
            'needs_indexing': True,
            'skip_indices': [2, 4]
        }
    
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
    """Test the _handle_regular_child method"""
    
    def test_creates_and_adds_regular_child(self, tree_builder):
        child_schema = {'tag': 'p', 'text': 'Hello'}
        parent_node = MockNode('root', {})
        stack = []
        
        tree_builder._handle_regular_child(child_schema, parent_node, stack)
        
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


class TestHandleRegularTemplateChild:
    """Test the _handle_regular_template_child method"""
    
    def test_creates_and_adds_template_child(self, tree_builder):
        template_child_schema = {'tag': 'span', 'text': 'Content'}
        parent_node = MockNode('template', {})
        template_stack = []
        
        tree_builder._handle_regular_template_child(
            template_child_schema,
            parent_node,
            template_stack
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
    """Test the _process_node_children method"""
    
    def test_no_children_returns_early(self, tree_builder, mock_schema_queries, 
                                      mock_config_queries, mock_template_registry,
                                      mock_caching_coordinator):
        current_schema = {'tag': 'div'}
        current_node = MockNode('root', current_schema)
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
        current_schema = {'tag': 'div'}
        current_node = MockNode('root', current_schema)
        stack = []
        
        child1 = {'tag': 'p'}
        child2 = {'tag': 'span'}
        
        mock_schema_queries.has_children.return_value = True
        mock_schema_queries.get_children.return_value = [child1, child2]
        mock_schema_queries.has_repeat.return_value = False
        
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
    """Test the _create_template_instances method"""
    
    def test_creates_correct_number_of_instances(self, tree_builder, mock_schema_queries,
                                                 mock_config_queries, mock_template_registry,
                                                 mock_caching_coordinator):
        repeat_config = {
            'template_name': 'item_template',
            'template_schema': {'tag': 'div'},
            'count': 3,
            'needs_indexing': False,
            'skip_indices': []
        }
        
        parent_node = MockNode('root', {})
        mock_schema_queries.get_static_schema_node_attrs.return_value = {'class': 'item'}
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
        repeat_config = {
            'template_name': 'item_template',
            'template_schema': {'tag': 'div'},
            'count': 5,
            'needs_indexing': True,
            'skip_indices': [2, 4]
        }
        
        parent_node = MockNode('root', {})
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
    """Integration tests for the full tree building process"""
    
    def test_simple_tree_without_repeats(self, tree_builder, mock_schema_queries,
                                         mock_config_queries, mock_template_registry,
                                         mock_caching_coordinator):
        """Test building a simple tree with no repeat blocks"""
        root_schema = {'tag': 'div', 'description': 'root'}
        child1_schema = {'tag': 'p', 'text': 'Hello'}
        child2_schema = {'tag': 'span', 'text': 'World'}
        
        # Setup mocks
        def has_children_side_effect(schema):
            if schema == root_schema:
                return True
            return False
        
        mock_schema_queries.has_children.side_effect = has_children_side_effect
        mock_schema_queries.get_children.return_value = [child1_schema, child2_schema]
        mock_schema_queries.has_repeat.return_value = False
        
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
        
        # Verify landmark caching
        mock_caching_coordinator.cache_landmark_node.assert_called_once_with(root)
    
    def test_tree_with_single_repeat_block(self, tree_builder, mock_schema_queries,
                                          mock_config_queries, mock_template_registry,
                                          mock_caching_coordinator):
        """Test building a tree with one repeat block"""
        root_schema = {'tag': 'div', 'description': 'root'}
        repeat_schema = {'repeat': {'template': 'item_template', 'count': 3}}
        template_schema = {'tag': 'span', 'description': 'item'}
        
        # Setup mocks
        call_count = {'has_children': 0}
        
        def has_children_side_effect(schema):
            call_count['has_children'] += 1
            if call_count['has_children'] == 1:  # First call for root
                return True
            return False  # All other calls (template nodes)
        
        mock_schema_queries.has_children.side_effect = has_children_side_effect
        mock_schema_queries.get_children.return_value = [repeat_schema]
        
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
        mock_schema_queries.get_static_schema_node_attrs.return_value = {'class': 'item'}
        
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
        assert mock_caching_coordinator.uncache_landmark.call_count == 3
    
    def test_tree_with_indexed_repeat_and_skipping(self, tree_builder, mock_schema_queries,
                                                   mock_config_queries, mock_template_registry,
                                                   mock_caching_coordinator):
        """Test repeat block with indexing and skip indices"""
        root_schema = {'tag': 'div'}
        repeat_schema = {'repeat': {'template': 'item_template', 'count': 5}}
        template_schema = {'tag': 'span'}
        
        # Setup mocks
        call_count = {'has_children': 0}
        
        def has_children_side_effect(schema):
            call_count['has_children'] += 1
            if call_count['has_children'] == 1:
                return True
            return False
        
        mock_schema_queries.has_children.side_effect = has_children_side_effect
        mock_schema_queries.get_children.return_value = [repeat_schema]
        mock_schema_queries.has_repeat.side_effect = lambda s: s == repeat_schema
        mock_schema_queries.get_repeat_info.return_value = {
            'template': 'item_template',
            'count': 5
        }
        
        mock_template_registry.get_template_schema.return_value = template_schema
        mock_config_queries.needs_indexing.return_value = True
        mock_config_queries.get_skip_indices.return_value = [2, 4]
        
        def get_dynamic_attrs(schema, placeholder, index):
            return {'id': f'item-{index}'}
        
        mock_schema_queries.get_dynamic_schema_node_attrs.side_effect = get_dynamic_attrs
        
        # Build tree
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
        
        # Verify uncache only called 3 times (not for skipped)
        assert mock_caching_coordinator.uncache_landmark.call_count == 3
    
    def test_tree_with_nested_repeats(self, tree_builder, mock_schema_queries,
                                     mock_config_queries, mock_template_registry,
                                     mock_caching_coordinator):
        """Test building a tree with nested repeat blocks"""
        root_schema = {'tag': 'div'}
        outer_repeat_schema = {'repeat': {'template': 'outer_template', 'count': 2}}
        outer_template_schema = {'tag': 'section'}
        inner_repeat_schema = {'repeat': {'template': 'inner_template', 'count': 2}}
        inner_template_schema = {'tag': 'span'}
        
        # Setup complex mock behavior
        def has_children_side_effect(schema):
            if schema in [root_schema, outer_template_schema]:
                return True
            return False
        
        def get_children_side_effect(schema):
            if schema == root_schema:
                return [outer_repeat_schema]
            elif schema == outer_template_schema:
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
        mock_schema_queries.get_static_schema_node_attrs.return_value = {}
        
        # Build tree
        root = tree_builder.build_node_tree_from_top(
            mock_schema_queries,
            mock_config_queries,
            mock_template_registry,
            mock_caching_coordinator,
            root_schema
        )
        
        # Verify structure: 2 outer templates, each with 2 inner templates
        assert len(root.children) == 2
        assert all(child.template_name == 'outer_template' for child in root.children)
        
        for outer_child in root.children:
            assert len(outer_child.children) == 2
            assert all(inner.template_name == 'inner_template' for inner in outer_child.children)
        
        # Verify caching calls
        assert mock_caching_coordinator.cache_template_instances.call_count == 3  # 1 outer + 2 inner
        assert mock_caching_coordinator.uncache_landmark.call_count == 6  # 2 outer + 4 inner
    
    def test_tree_with_auto_count(self, tree_builder, mock_schema_queries,
                                  mock_config_queries, mock_template_registry,
                                  mock_caching_coordinator):
        """Test repeat block with 'auto' count"""
        root_schema = {'tag': 'div'}
        repeat_schema = {'repeat': {'template': 'item_template', 'count': 'auto'}}
        template_schema = {'tag': 'span'}
        
        # Setup mocks
        call_count = {'has_children': 0}
        
        def has_children_side_effect(schema):
            call_count['has_children'] += 1
            if call_count['has_children'] == 1:
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
        mock_schema_queries.get_static_schema_node_attrs.return_value = {}
        
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
    """Test edge cases and error conditions"""
    
    def test_empty_tree(self, tree_builder, mock_schema_queries, mock_config_queries,
                       mock_template_registry, mock_caching_coordinator):
        """Test building a tree with no children"""
        root_schema = {'tag': 'div'}
        
        mock_schema_queries.has_children.return_value = False
        
        root = tree_builder.build_node_tree_from_top(
            mock_schema_queries,
            mock_config_queries,
            mock_template_registry,
            mock_caching_coordinator,
            root_schema
        )
        
        assert root.node_type == 'root'
        assert len(root.children) == 0
    
    def test_repeat_with_count_zero(self, tree_builder, mock_schema_queries,
                                   mock_config_queries, mock_template_registry,
                                   mock_caching_coordinator):
        """Test repeat block with count=0"""
        root_schema = {'tag': 'div'}
        repeat_schema = {'repeat': {'template': 'item_template', 'count': 0}}
        template_schema = {'tag': 'span'}
        
        call_count = {'has_children': 0}
        
        def has_children_side_effect(schema):
            call_count['has_children'] += 1
            if call_count['has_children'] == 1:
                return True
            return False
        
        mock_schema_queries.has_children.side_effect = has_children_side_effect
        mock_schema_queries.get_children.return_value = [repeat_schema]
        mock_schema_queries.has_repeat.side_effect = lambda s: s == repeat_schema
        mock_schema_queries.get_repeat_info.return_value = {
            'template': 'item_template',
            'count': 0
        }
        
        mock_template_registry.get_template_schema.return_value = template_schema
        mock_config_queries.needs_indexing.return_value = False
        mock_config_queries.get_skip_indices.return_value = []
        
        root = tree_builder.build_node_tree_from_top(
            mock_schema_queries,
            mock_config_queries,
            mock_template_registry,
            mock_caching_coordinator,
            root_schema
        )
        
        # Should create no template instances
        assert len(root.children) == 0
        assert mock_caching_coordinator.uncache_landmark.call_count == 0
    
    def test_all_indices_skipped(self, tree_builder, mock_schema_queries,
                                mock_config_queries, mock_template_registry,
                                mock_caching_coordinator):
        """Test when all indices are in skip list"""
        root_schema = {'tag': 'div'}
        repeat_schema = {'repeat': {'template': 'item_template', 'count': 3}}
        template_schema = {'tag': 'span'}
        
        call_count = {'has_children': 0}
        
        def has_children_side_effect(schema):
            call_count['has_children'] += 1
            if call_count['has_children'] == 1:
                return True
            return False
        
        mock_schema_queries.has_children.side_effect = has_children_side_effect
        mock_schema_queries.get_children.return_value = [repeat_schema]
        mock_schema_queries.has_repeat.side_effect = lambda s: s == repeat_schema
        mock_schema_queries.get_repeat_info.return_value = {
            'template': 'item_template',
            'count': 3
        }
        
        mock_template_registry.get_template_schema.return_value = template_schema
        mock_config_queries.needs_indexing.return_value = True
        mock_config_queries.get_skip_indices.return_value = [1, 2, 3]
        
        root = tree_builder.build_node_tree_from_top(
            mock_schema_queries,
            mock_config_queries,
            mock_template_registry,
            mock_caching_coordinator,
            root_schema
        )
        
        # Should create no nodes
        assert len(root.children) == 0
        assert mock_caching_coordinator.uncache_landmark.call_count == 0


class TestLandmarkCachingIntegration:
    """Integration tests specifically for landmark caching behavior"""
    
    def test_root_landmark_cached_at_start(self, tree_builder, mock_schema_queries,
                                          mock_config_queries, mock_template_registry,
                                          mock_caching_coordinator):
        """Test that root is cached as landmark at the beginning"""
        root_schema = {'tag': 'div'}
        
        mock_schema_queries.has_children.return_value = False
        
        root = tree_builder.build_node_tree_from_top(
            mock_schema_queries,
            mock_config_queries,
            mock_template_registry,
            mock_caching_coordinator,
            root_schema
        )
        
        # Verify root was cached as landmark
        mock_caching_coordinator.cache_landmark_node.assert_called_once_with(root)
        
        # Verify it was the first call made
        first_call = mock_caching_coordinator.method_calls[0]
        assert first_call[0] == 'cache_landmark_node'
    
    def test_template_instances_cached_before_creation(self, tree_builder, mock_schema_queries,
                                                       mock_config_queries, mock_template_registry,
                                                       mock_caching_coordinator):
        """Test that cache_template_instances is called before creating instances"""
        root_schema = {'tag': 'div'}
        repeat_schema = {'repeat': {'template': 'item_template', 'count': 3}}
        template_schema = {'tag': 'span'}
        
        call_count = {'has_children': 0}
        
        def has_children_side_effect(schema):
            call_count['has_children'] += 1
            return call_count['has_children'] == 1
        
        mock_schema_queries.has_children.side_effect = has_children_side_effect
        mock_schema_queries.get_children.return_value = [repeat_schema]
        mock_schema_queries.has_repeat.side_effect = lambda s: s == repeat_schema
        mock_schema_queries.get_repeat_info.return_value = {
            'template': 'item_template',
            'count': 3
        }
        mock_template_registry.get_template_schema.return_value = template_schema
        mock_config_queries.needs_indexing.return_value = False
        mock_config_queries.get_skip_indices.return_value = []
        mock_schema_queries.get_static_schema_node_attrs.return_value = {}
        
        tree_builder.build_node_tree_from_top(
            mock_schema_queries,
            mock_config_queries,
            mock_template_registry,
            mock_caching_coordinator,
            root_schema
        )
        
        # Get all calls to caching coordinator
        calls = mock_caching_coordinator.method_calls
        
        # Find cache_template_instances call
        cache_call_index = None
        first_uncache_index = None
        
        for i, call in enumerate(calls):
            if call[0] == 'cache_template_instances' and call[1] == ('item_template',):
                cache_call_index = i
            elif call[0] == 'uncache_landmark' and first_uncache_index is None:
                first_uncache_index = i
        
        # Verify cache was called before first uncache
        assert cache_call_index is not None, "cache_template_instances was not called"
        assert first_uncache_index is not None, "uncache_landmark was not called"
        assert cache_call_index < first_uncache_index, "cache_template_instances should be called before uncache_landmark"
    
    def test_uncache_called_once_per_instance(self, tree_builder, mock_schema_queries,
                                              mock_config_queries, mock_template_registry,
                                              mock_caching_coordinator):
        """Test that uncache is called exactly once per created instance"""
        root_schema = {'tag': 'div'}
        repeat_schema = {'repeat': {'template': 'item_template', 'count': 5}}
        template_schema = {'tag': 'span'}
        
        call_count = {'has_children': 0}
        
        def has_children_side_effect(schema):
            call_count['has_children'] += 1
            return call_count['has_children'] == 1
        
        mock_schema_queries.has_children.side_effect = has_children_side_effect
        mock_schema_queries.get_children.return_value = [repeat_schema]
        mock_schema_queries.has_repeat.side_effect = lambda s: s == repeat_schema
        mock_schema_queries.get_repeat_info.return_value = {
            'template': 'item_template',
            'count': 5
        }
        mock_template_registry.get_template_schema.return_value = template_schema
        mock_config_queries.needs_indexing.return_value = False
        mock_config_queries.get_skip_indices.return_value = []
        mock_schema_queries.get_static_schema_node_attrs.return_value = {}
        
        root = tree_builder.build_node_tree_from_top(
            mock_schema_queries,
            mock_config_queries,
            mock_template_registry,
            mock_caching_coordinator,
            root_schema
        )
        
        # Verify uncache called exactly 5 times (once per instance)
        assert mock_caching_coordinator.uncache_landmark.call_count == 5
        
        # Verify 5 instances were created
        assert len(root.children) == 5
    
    def test_uncache_not_called_for_skipped_indices(self, tree_builder, mock_schema_queries,
                                                    mock_config_queries, mock_template_registry,
                                                    mock_caching_coordinator):
        """Test that uncache is NOT called when indices are skipped"""
        root_schema = {'tag': 'div'}
        repeat_schema = {'repeat': {'template': 'item_template', 'count': 5}}
        template_schema = {'tag': 'span'}
        
        call_count = {'has_children': 0}
        
        def has_children_side_effect(schema):
            call_count['has_children'] += 1
            return call_count['has_children'] == 1
        
        mock_schema_queries.has_children.side_effect = has_children_side_effect
        mock_schema_queries.get_children.return_value = [repeat_schema]
        mock_schema_queries.has_repeat.side_effect = lambda s: s == repeat_schema
        mock_schema_queries.get_repeat_info.return_value = {
            'template': 'item_template',
            'count': 5
        }
        mock_template_registry.get_template_schema.return_value = template_schema
        mock_config_queries.needs_indexing.return_value = True
        mock_config_queries.get_skip_indices.return_value = [2, 4]
        
        def get_dynamic_attrs(schema, placeholder, index):
            return {'id': f'item-{index}'}
        
        mock_schema_queries.get_dynamic_schema_node_attrs.side_effect = get_dynamic_attrs
        
        root = tree_builder.build_node_tree_from_top(
            mock_schema_queries,
            mock_config_queries,
            mock_template_registry,
            mock_caching_coordinator,
            root_schema
        )
        
        # Should uncache only 3 times (for indices 1, 3, 5 - NOT for 2, 4)
        assert mock_caching_coordinator.uncache_landmark.call_count == 3
        
        # Verify only 3 instances were created
        assert len(root.children) == 3
    
    def test_caching_order_with_nested_repeats(self, tree_builder, mock_schema_queries,
                                               mock_config_queries, mock_template_registry,
                                               mock_caching_coordinator):
        """Test caching order: outer cache -> inner cache -> inner uncache -> outer uncache"""
        root_schema = {'tag': 'div'}
        outer_repeat_schema = {'repeat': {'template': 'outer_template', 'count': 2}}
        outer_template_schema = {'tag': 'section'}
        inner_repeat_schema = {'repeat': {'template': 'inner_template', 'count': 2}}
        inner_template_schema = {'tag': 'span'}
        
        def has_children_side_effect(schema):
            if schema in [root_schema, outer_template_schema]:
                return True
            return False
        
        def get_children_side_effect(schema):
            if schema == root_schema:
                return [outer_repeat_schema]
            elif schema == outer_template_schema:
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
        mock_schema_queries.get_static_schema_node_attrs.return_value = {}
        
        tree_builder.build_node_tree_from_top(
            mock_schema_queries,
            mock_config_queries,
            mock_template_registry,
            mock_caching_coordinator,
            root_schema
        )
        
        # Extract all caching-related calls
        calls = mock_caching_coordinator.method_calls
        cache_calls = [c for c in calls if c[0] in ['cache_template_instances', 'uncache_landmark']]
        
        # Expected order:
        # 1. cache_template_instances('outer_template')
        # 2. cache_template_instances('inner_template') - for first outer instance
        # 3. uncache_landmark() - first inner instance
        # 4. uncache_landmark() - second inner instance
        # 5. uncache_landmark() - first outer instance
        # 6. cache_template_instances('inner_template') - for second outer instance
        # 7. uncache_landmark() - first inner instance
        # 8. uncache_landmark() - second inner instance
        # 9. uncache_landmark() - second outer instance
        
        # Verify cache_template_instances calls
        assert cache_calls[0] == ('cache_template_instances', ('outer_template',), {})
        assert cache_calls[1] == ('cache_template_instances', ('inner_template',), {})
        
        # Count uncache calls between caches
        uncaches_before_second_cache = 0
        for i in range(2, len(cache_calls)):
            if cache_calls[i][0] == 'uncache_landmark':
                uncaches_before_second_cache += 1
            elif cache_calls[i][0] == 'cache_template_instances':
                break
        
        # Should have 3 uncaches: 2 inner + 1 outer before second inner cache
        assert uncaches_before_second_cache == 3
        
        # Total uncaches should be 6 (2 outer * 2 inner + 2 outer)
        total_uncaches = sum(1 for c in cache_calls if c[0] == 'uncache_landmark')
        assert total_uncaches == 6
    
    def test_cache_template_instances_called_per_repeat_block(self, tree_builder, mock_schema_queries,
                                                              mock_config_queries, mock_template_registry,
                                                              mock_caching_coordinator):
        """Test that cache_template_instances is called once per repeat block"""
        root_schema = {'tag': 'div'}
        repeat1_schema = {'repeat': {'template': 'template1', 'count': 2}}
        repeat2_schema = {'repeat': {'template': 'template2', 'count': 2}}
        template1_schema = {'tag': 'span'}
        template2_schema = {'tag': 'div'}
        
        call_count = {'has_children': 0}
        
        def has_children_side_effect(schema):
            call_count['has_children'] += 1
            return call_count['has_children'] == 1
        
        mock_schema_queries.has_children.side_effect = has_children_side_effect
        mock_schema_queries.get_children.return_value = [repeat1_schema, repeat2_schema]
        
        def has_repeat_side_effect(schema):
            return schema in [repeat1_schema, repeat2_schema]
        
        def get_repeat_info_side_effect(schema):
            if schema == repeat1_schema:
                return {'template': 'template1', 'count': 2}
            elif schema == repeat2_schema:
                return {'template': 'template2', 'count': 2}
        
        def get_template_schema_side_effect(name):
            if name == 'template1':
                return template1_schema
            elif name == 'template2':
                return template2_schema
        
        mock_schema_queries.has_repeat.side_effect = has_repeat_side_effect
        mock_schema_queries.get_repeat_info.side_effect = get_repeat_info_side_effect
        mock_template_registry.get_template_schema.side_effect = get_template_schema_side_effect
        mock_config_queries.needs_indexing.return_value = False
        mock_config_queries.get_skip_indices.return_value = []
        mock_schema_queries.get_static_schema_node_attrs.return_value = {}
        
        tree_builder.build_node_tree_from_top(
            mock_schema_queries,
            mock_config_queries,
            mock_template_registry,
            mock_caching_coordinator,
            root_schema
        )
        
        # Verify cache_template_instances called twice (once per repeat block)
        cache_calls = [c for c in mock_caching_coordinator.method_calls 
                      if c[0] == 'cache_template_instances']
        
        assert len(cache_calls) == 2
        assert cache_calls[0] == ('cache_template_instances', ('template1',), {})
        assert cache_calls[1] == ('cache_template_instances', ('template2',), {})
        
        # Verify uncache called 4 times total (2 instances per template)
        assert mock_caching_coordinator.uncache_landmark.call_count == 4
    
    def test_caching_with_deeply_nested_repeats(self, tree_builder, mock_schema_queries,
                                                mock_config_queries, mock_template_registry,
                                                mock_caching_coordinator):
        """Test caching behavior with 3 levels of nested repeats"""
        root_schema = {'tag': 'div'}
        level1_repeat = {'repeat': {'template': 'level1', 'count': 2}}
        level1_schema = {'tag': 'section'}
        level2_repeat = {'repeat': {'template': 'level2', 'count': 2}}
        level2_schema = {'tag': 'article'}
        level3_repeat = {'repeat': {'template': 'level3', 'count': 2}}
        level3_schema = {'tag': 'span'}
        
        def has_children_side_effect(schema):
            return schema in [root_schema, level1_schema, level2_schema]
        
        def get_children_side_effect(schema):
            if schema == root_schema:
                return [level1_repeat]
            elif schema == level1_schema:
                return [level2_repeat]
            elif schema == level2_schema:
                return [level3_repeat]
            return []
        
        def has_repeat_side_effect(schema):
            return schema in [level1_repeat, level2_repeat, level3_repeat]
        
        def get_repeat_info_side_effect(schema):
            if schema == level1_repeat:
                return {'template': 'level1', 'count': 2}
            elif schema == level2_repeat:
                return {'template': 'level2', 'count': 2}
            elif schema == level3_repeat:
                return {'template': 'level3', 'count': 2}
        
        def get_template_schema_side_effect(name):
            schemas = {
                'level1': level1_schema,
                'level2': level2_schema,
                'level3': level3_schema
            }
            return schemas[name]
        
        mock_schema_queries.has_children.side_effect = has_children_side_effect
        mock_schema_queries.get_children.side_effect = get_children_side_effect
        mock_schema_queries.has_repeat.side_effect = has_repeat_side_effect
        mock_schema_queries.get_repeat_info.side_effect = get_repeat_info_side_effect
        mock_template_registry.get_template_schema.side_effect = get_template_schema_side_effect
        mock_config_queries.needs_indexing.return_value = False
        mock_config_queries.get_skip_indices.return_value = []
        mock_schema_queries.get_static_schema_node_attrs.return_value = {}
        
        tree_builder.build_node_tree_from_top(
            mock_schema_queries,
            mock_config_queries,
            mock_template_registry,
            mock_caching_coordinator,
            root_schema
        )
        
        # Total instances: 2 level1 * 2 level2 * 2 level3 = 8 level3 nodes
        # Plus 2 level1 * 2 level2 = 4 level2 nodes
        # Plus 2 level1 nodes
        # Total uncaches: 8 + 4 + 2 = 14
        assert mock_caching_coordinator.uncache_landmark.call_count == 14
        
        # Verify cache_template_instances called for each repeat block
        # Should be: 1 level1 + 2 level2 (one per level1 instance) + 4 level3 (one per level2 instance)
        cache_calls = [c for c in mock_caching_coordinator.method_calls 
                      if c[0] == 'cache_template_instances']
        assert len(cache_calls) == 7  # 1 + 2 + 4
        
        # Verify template names in cache calls
        level1_caches = sum(1 for c in cache_calls if c[1] == ('level1',))
        level2_caches = sum(1 for c in cache_calls if c[1] == ('level2',))
        level3_caches = sum(1 for c in cache_calls if c[1] == ('level3',))
        
        assert level1_caches == 1
        assert level2_caches == 2
        assert level3_caches == 4
    
    def test_no_uncache_when_count_is_zero(self, tree_builder, mock_schema_queries,
                                          mock_config_queries, mock_template_registry,
                                          mock_caching_coordinator):
        """Test that uncache is never called when repeat count is 0"""
        root_schema = {'tag': 'div'}
        repeat_schema = {'repeat': {'template': 'item_template', 'count': 0}}
        template_schema = {'tag': 'span'}
        
        call_count = {'has_children': 0}
        
        def has_children_side_effect(schema):
            call_count['has_children'] += 1
            return call_count['has_children'] == 1
        
        mock_schema_queries.has_children.side_effect = has_children_side_effect
        mock_schema_queries.get_children.return_value = [repeat_schema]
        mock_schema_queries.has_repeat.side_effect = lambda s: s == repeat_schema
        mock_schema_queries.get_repeat_info.return_value = {
            'template': 'item_template',
            'count': 0
        }
        mock_template_registry.get_template_schema.return_value = template_schema
        mock_config_queries.needs_indexing.return_value = False
        mock_config_queries.get_skip_indices.return_value = []
        
        tree_builder.build_node_tree_from_top(
            mock_schema_queries,
            mock_config_queries,
            mock_template_registry,
            mock_caching_coordinator,
            root_schema
        )
        
        # cache_template_instances should still be called
        mock_caching_coordinator.cache_template_instances.assert_called_once_with('item_template')
        
        # But uncache_landmark should NEVER be called
        mock_caching_coordinator.uncache_landmark.assert_not_called()


