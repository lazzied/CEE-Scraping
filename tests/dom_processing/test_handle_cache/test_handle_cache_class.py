from unittest.mock import Mock
import pytest
from dom_processing.json_parser import ConfigQueries, SchemaQueries, TemplateRegistry
from tests.dom_processing.test_handle_cache.handle_cache_ver2 import CachingCoordinator, ElementFinder, ElementValidator, HandleCaching, SelectorBuilder


class TestHandleCaching:
    """Tests for improved HandleCaching - no Selenium mocking needed!"""
    
    @pytest.fixture
    def mock_element_finder(self):
        """Mock element finder"""
        return Mock(spec=ElementFinder)
    
    @pytest.fixture
    def mock_element_validator(self):
        """Mock validator"""
        validator = Mock(spec=ElementValidator)
        validator.is_valid_landmark.return_value = True
        return validator
    
    @pytest.fixture
    def cache_handler(self, mock_element_finder, mock_element_validator):
        """Create cache handler with mocked dependencies"""
        return HandleCaching(
            element_finder=mock_element_finder,
            element_validator=mock_element_validator
        )
    
    @pytest.fixture
    def mock_element(self):
        """Simple mock element - no Selenium needed"""
        return Mock(name="MockElement")
    
    # ==================== Tests ====================
    
    def test_initialize_landmark_cache_with_empty_cache(
        self,
        cache_handler,
        mock_element
    ):
        """Should push root element when cache is empty"""
        cache_handler.initialize_landmark_cache(mock_element)
        
        assert cache_handler.cache_size() == 1
        assert cache_handler.get_current_landmark() == mock_element
    
    def test_initialize_landmark_cache_when_not_empty(
        self,
        cache_handler,
        mock_element
    ):
        """Should not push if cache already has elements"""
        first_element = Mock(name="FirstElement")
        cache_handler.initialize_landmark_cache(first_element)
        
        cache_handler.initialize_landmark_cache(mock_element)
        
        assert cache_handler.cache_size() == 1
        assert cache_handler.get_current_landmark() == first_element
    
    def test_push_landmark_success(
        self,
        cache_handler,
        mock_element_finder,
        mock_element
    ):
        """Should find and push landmark element"""
        # Setup
        parent = Mock(name="Parent")
        found_element = Mock(name="FoundElement")
        
        cache_handler.initialize_landmark_cache(parent)
        mock_element_finder.find_single.return_value = found_element
        
        # Execute
        result = cache_handler.push_landmark("div.test")  # this is the found_element webelement
        
        # Verify
        assert result is True
        assert cache_handler.cache_size() == 2
        assert cache_handler.get_current_landmark() == found_element
        mock_element_finder.find_single.assert_called_once_with(parent, "div.test")
    
    def test_push_landmark_element_not_found(
        self,
        cache_handler,
        mock_element_finder,
        mock_element
    ):
        """Should return False when element not found"""
        cache_handler.initialize_landmark_cache(mock_element)
        mock_element_finder.find_single.return_value = None
        
        result = cache_handler.push_landmark("div.test")
        
        assert result is False
        assert cache_handler.cache_size() == 1  # Only root
    
    def test_push_landmark_invalid_element(
        self,
        cache_handler,
        mock_element_finder,
        mock_element_validator,
        mock_element
    ):
        """Should return False when element is invalid"""
        cache_handler.initialize_landmark_cache(mock_element)
        
        found_element = Mock(name="InvalidElement")
        mock_element_finder.find_single.return_value = found_element
        mock_element_validator.is_valid_landmark.return_value = False
        
        result = cache_handler.push_landmark("div.test")
        
        assert result is False
        assert cache_handler.cache_size() == 1
    
    def test_push_landmark_with_empty_cache(
        self,
        cache_handler,
        mock_element_finder
    ):
        """Should return False when cache is empty"""
        result = cache_handler.push_landmark("div.test")
        
        assert result is False
        mock_element_finder.find_single.assert_not_called()
    
    def test_push_prefetched_elements_success(
        self,
        cache_handler,
        mock_element_finder,
        mock_element
    ):
        """Should find and push multiple elements in reverse order"""
        # Setup
        parent = Mock(name="Parent")
        el1 = Mock(name="Element1")
        el2 = Mock(name="Element2")
        el3 = Mock(name="Element3")
        
        cache_handler.initialize_landmark_cache(parent)
        mock_element_finder.find_multiple.return_value = [el1, el2, el3]
        
        # Execute
        count = cache_handler.push_prefetched_elements("div.card")
        
        # Verify
        assert count == 3
        assert cache_handler.cache_size() == 4  # parent + 3 elements
        
        # Verify reverse order (el1 should be on top)
        assert cache_handler.get_current_landmark() == el1
    
    def test_push_prefetched_elements_maintains_order(
        self,
        cache_handler,
        mock_element_finder
    ):
        """Should push elements so first found is on top"""
        parent = Mock(name="Parent")
        el1 = Mock(name="El1")
        el2 = Mock(name="El2")
        el3 = Mock(name="El3")
        
        cache_handler.initialize_landmark_cache(parent)
        mock_element_finder.find_multiple.return_value = [el1, el2, el3]
        
        cache_handler.push_prefetched_elements("div.card")
        
        # Pop and verify order
        assert cache_handler.pop_landmark() == el1
        assert cache_handler.pop_landmark() == el2
        assert cache_handler.pop_landmark() == el3
        assert cache_handler.pop_landmark() == parent
    
    def test_push_prefetched_elements_empty_results(
        self,
        cache_handler,
        mock_element_finder,
        mock_element
    ):
        """Should handle no elements found gracefully"""
        cache_handler.initialize_landmark_cache(mock_element)
        mock_element_finder.find_multiple.return_value = []
        
        count = cache_handler.push_prefetched_elements("div.card")
        
        assert count == 0
        assert cache_handler.cache_size() == 1  # Only root
    
    def test_push_prefetched_elements_filters_invalid(
        self,
        cache_handler,
        mock_element_finder,
        mock_element_validator,
        mock_element
    ):
        """Should only push valid elements"""
        parent = Mock(name="Parent")
        valid_el = Mock(name="ValidElement")
        invalid_el = Mock(name="InvalidElement")
        
        cache_handler.initialize_landmark_cache(parent)
        mock_element_finder.find_multiple.return_value = [valid_el, invalid_el]
        
        # Only first element is valid
        mock_element_validator.is_valid_landmark.side_effect = [True, False]
        
        count = cache_handler.push_prefetched_elements("div.card")
        
        assert count == 1
        assert cache_handler.get_current_landmark() == valid_el
    
    def test_push_prefetched_elements_empty_cache(
        self,
        cache_handler,
        mock_element_finder
    ):
        """Should return 0 when cache is empty"""
        count = cache_handler.push_prefetched_elements("div.card")
        
        assert count == 0
        mock_element_finder.find_multiple.assert_not_called()
    
    def test_pop_landmark_removes_element(self, cache_handler):
        """Should remove and return top element"""
        el1 = Mock(name="Element1")
        el2 = Mock(name="Element2")
        
        cache_handler.initialize_landmark_cache(el1)
        cache_handler._landmark_cache.push(el2)
        
        popped = cache_handler.pop_landmark()
        
        assert popped == el2
        assert cache_handler.cache_size() == 1
        assert cache_handler.get_current_landmark() == el1
    
    def test_pop_landmark_on_empty_cache(self, cache_handler):
        """Should return None when cache is empty"""
        result = cache_handler.pop_landmark()
        
        assert result is None
    
    def test_get_current_landmark_without_removing(self, cache_handler):
        """Should return top element without removing it"""
        element = Mock(name="Element")
        cache_handler.initialize_landmark_cache(element)
        
        current = cache_handler.get_current_landmark()
        
        assert current == element
        assert cache_handler.cache_size() == 1  # Not removed
    
    def test_get_current_landmark_on_empty_cache(self, cache_handler):
        """Should return None when cache is empty"""
        result = cache_handler.get_current_landmark()
        
        assert result is None
    
    def test_cache_size(self, cache_handler):
        """Should return correct cache size"""
        assert cache_handler.cache_size() == 0
        
        cache_handler.initialize_landmark_cache(Mock())
        assert cache_handler.cache_size() == 1
        
        cache_handler._landmark_cache.push(Mock())
        assert cache_handler.cache_size() == 2
    
    def test_is_empty(self, cache_handler):
        """Should correctly report empty status"""
        assert cache_handler.is_empty() is True
        
        cache_handler.initialize_landmark_cache(Mock())
        assert cache_handler.is_empty() is False
    
    def test_clear(self, cache_handler):
        """Should remove all elements from cache"""
        cache_handler.initialize_landmark_cache(Mock())
        cache_handler._landmark_cache.push(Mock())
        cache_handler._landmark_cache.push(Mock())
        
        assert cache_handler.cache_size() == 3
        
        cache_handler.clear()
        
        assert cache_handler.is_empty() is True
        assert cache_handler.cache_size() == 0


class TestSelectorBuilder:
    """Tests for SelectorBuilder - completely isolated"""
    
    @pytest.fixture
    def mock_template_registry(self):
        mock = Mock(spec=TemplateRegistry)
        mock.get_template_invariant_characteristics.return_value = ["tag", "classes"]
        mock.form_template_selector.return_value = "div.card"
        return mock
    
    @pytest.fixture
    def mock_config_queries(self):
        return Mock(spec=ConfigQueries)
    
    @pytest.fixture
    def selector_builder(self, mock_template_registry, mock_config_queries):
        return SelectorBuilder(mock_template_registry, mock_config_queries)
    
    def test_build_selector_for_template(
        self,
        selector_builder,
        mock_template_registry,
        mock_config_queries
    ):
        """Should build selector using template and config"""
        result = selector_builder.build_selector_for_template("exam_card")
        
        assert result == "div.card"
        mock_template_registry.get_template_invariant_characteristics.assert_called_once_with(
            "exam_card",
            mock_config_queries
        )
        mock_template_registry.form_template_selector.assert_called_once_with(
            "exam_card",
            ["tag", "classes"]
        )


class TestCachingCoordinator:
    """Tests for high-level coordinator"""
    
    @pytest.fixture
    def mock_cache_handler(self):
        return Mock(spec=HandleCaching)
    
    @pytest.fixture
    def mock_selector_builder(self):
        mock = Mock(spec=SelectorBuilder)
        mock.build_selector_for_template.return_value = "div.card"
        return mock
    
    @pytest.fixture
    def mock_schema_queries(self):
        return Mock(spec=SchemaQueries)
    
    @pytest.fixture
    def coordinator(
        self,
        mock_cache_handler,
        mock_selector_builder,
        mock_schema_queries
    ):
        return CachingCoordinator(
            mock_cache_handler,
            mock_selector_builder,
            mock_schema_queries
        )
    
    def test_initialize_with_root(self, coordinator, mock_cache_handler):
        """Should initialize cache with root node's web element"""
        root_node = Mock()
        root_node.web_element = Mock(name="RootElement")
        
        coordinator.initialize_with_root(root_node)
        
        mock_cache_handler.initialize_landmark_cache.assert_called_once_with(
            root_node.web_element
        )
    
    def test_cache_landmark_node(self, coordinator, mock_cache_handler):
        """Should cache landmark using node's selector"""
        node = Mock()
        node.get_css_selector.return_value = "div.landmark"
        mock_cache_handler.push_landmark.return_value = True
        
        result = coordinator.cache_landmark_node(node)
        
        assert result is True
        mock_cache_handler.push_landmark.assert_called_once_with("div.landmark")
    
    def test_cache_template_instances(
        self,
        coordinator,
        mock_cache_handler,
        mock_selector_builder
    ):
        """Should cache template instances using built selector"""
        mock_cache_handler.push_prefetched_elements.return_value = 5
        
        count = coordinator.cache_template_instances("exam_card")
        
        assert count == 5
        mock_selector_builder.build_selector_for_template.assert_called_once_with("exam_card")
        mock_cache_handler.push_prefetched_elements.assert_called_once_with("div.card")
    
    def test_should_cache_node(self, coordinator, mock_schema_queries):
        """Should delegate to schema queries"""
        schema_node = {"annotation": ["landmark_element"]}
        mock_schema_queries.is_landmark.return_value = True
        
        result = coordinator.should_cache_node(schema_node)
        
        assert result is True
        mock_schema_queries.is_landmark.assert_called_once_with(schema_node)