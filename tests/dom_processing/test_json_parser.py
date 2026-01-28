import pytest
from unittest.mock import Mock
from dom_processing.json_parser import SchemaStructureValidator, AttributeFormatter, ConfigQueries, HtmlValidator, SchemaQueries, TemplateRegistry, ValidationError

# Assuming imports from your module
# from your_module import (
#     HtmlValidator, AttributeFormatter, TemplateRegistry, ConfigQueries,
#     SchemaQueries, SchemaStructureValidator, ValidationError, AnnotationType
# )


# ==================== TEST HTML VALIDATOR ====================

class TestHtmlValidator:
    """Tests for HtmlValidator utility class"""
    
    def test_is_valid_html_tag_with_valid_lowercase_tag(self):
        """Should return True for valid lowercase HTML tags"""
        assert HtmlValidator.is_valid_html_tag("div") is True
        assert HtmlValidator.is_valid_html_tag("span") is True
        assert HtmlValidator.is_valid_html_tag("body") is True
    
    def test_is_valid_html_tag_with_valid_uppercase_tag(self):
        """Should return True for valid uppercase HTML tags (case-insensitive)"""
        assert HtmlValidator.is_valid_html_tag("DIV") is True
        assert HtmlValidator.is_valid_html_tag("SPAN") is True
    
    def test_is_valid_html_tag_with_valid_mixed_case_tag(self):
        """Should return True for valid mixed case HTML tags"""
        assert HtmlValidator.is_valid_html_tag("DiV") is True
        assert HtmlValidator.is_valid_html_tag("SpAn") is True
    
    def test_is_valid_html_tag_with_invalid_tag(self):
        """Should return False for invalid HTML tags"""
        assert HtmlValidator.is_valid_html_tag("notarealtag") is False
        assert HtmlValidator.is_valid_html_tag("custom-element") is False
        assert HtmlValidator.is_valid_html_tag("xyz") is False
    
    def test_is_valid_html_tag_with_non_string_input(self):
        """Should return False for non-string inputs"""
        assert HtmlValidator.is_valid_html_tag(123) is False
        assert HtmlValidator.is_valid_html_tag(None) is False
        assert HtmlValidator.is_valid_html_tag([]) is False
        assert HtmlValidator.is_valid_html_tag({}) is False
    
    def test_is_valid_html_tag_with_empty_string(self):
        """Should return False for empty string"""
        assert HtmlValidator.is_valid_html_tag("") is False
    
    @pytest.mark.parametrize("tag,expected", [
        ("div", True),
        ("span", True),
        ("p", True),
        ("h1", True),
        ("invalid", False),
        ("", False),
        ("DIV", True),
    ])
    def test_is_valid_html_tag_parametrized(self, tag, expected):
        """Parametrized test for various HTML tags"""
        assert HtmlValidator.is_valid_html_tag(tag) == expected


# ==================== TEST ATTRIBUTE FORMATTER ====================

class TestAttributeFormatter:
    """Tests for AttributeFormatter utility class"""
    
    def test_format_dynamic_attributes_with_index(self):
        """Should format placeholders with index value"""
        attributes = {"id": "item-{index}"}
        result = AttributeFormatter.format_dynamic_attributes(
            attributes = attributes,
            placeholders=["{index}"],
            values=[5])
        
        assert result == {"id": "item-5"}
    
    def test_format_dynamic_attributes_with_multiple_placeholders(self):
        """Should format multiple placeholders with index value"""
        attributes = {"data-item": "item-{item_index}",
                       "data-value": "value-{value_index}"}

        result = AttributeFormatter.format_dynamic_attributes(
            attributes = attributes,
            placeholders=["{item_index}", "{value_index}"],
            values=[3, 5])

        assert result == {"data-item": "item-3", "data-value": "value-5"}



    

# ==================== TEST TEMPLATE REGISTRY ====================

class TestTemplateRegistry:
    """Tests for TemplateRegistry class"""
    
    @pytest.fixture
    def sample_templates(self):
        """Sample template definitions"""
        return {
            "exam_variant": {
                "tag": "div",
                "classes": ["exam-card"],
                "attrs": {"data-index": "{index}"}
            },
            "simple_card": {
                "tag": "div",
                "classes": ["card", "item"],
                "attrs": {"id": "main"}
            }
        }
    
    @pytest.fixture
    def template_registry(self, sample_templates):
        """Create TemplateRegistry instance"""
        return TemplateRegistry(sample_templates)
    
    def test_get_template_schema_existing_template(self, template_registry):
        """Should return template schema for existing template"""
        result = template_registry.get_template_schema("exam_variant")
        
        assert result == {
            "tag": "div",
            "classes": ["exam-card"],
            "attrs": {"data-index": "{index}"}
        }
    
    def test_get_template_schema_nonexistent_template(self, template_registry):
        """Should return None for non-existent template"""
        result = template_registry.get_template_schema("nonexistent")
        assert result is None
    
    def test_get_all_template_names(self, template_registry):
        """Should return list of all template names"""
        result = template_registry.get_all_template_names()
        
        assert set(result) == {"exam_variant", "simple_card"}
        assert len(result) == 2
    
    def test_template_exists_returns_true_for_existing(self, template_registry):
        """Should return True for existing templates"""
        assert template_registry.template_exists("exam_variant") is True
        assert template_registry.template_exists("simple_card") is True
    
    def test_template_exists_returns_false_for_nonexistent(self, template_registry):
        """Should return False for non-existent templates"""
        assert template_registry.template_exists("nonexistent") is False
        assert template_registry.template_exists("") is False
    
    def test_get_template_invariant_characteristics_with_indexing(self):
        """Should exclude indexing attribute from invariant characteristics"""
        templates = {
            "exam": {
                "tag": "div",
                "classes": ["exam"],
                "attrs": {"data-index": "{index}", "type": "exam"}
            }
        }
        registry = TemplateRegistry(templates)
        
        # Mock config that specifies indexing
        mock_config = Mock()
        mock_config.needs_indexing.return_value = True  
        mock_config.get_indexing_attribute.return_value = "data-index"
        
        result = registry.get_template_invariant_characteristics("exam", mock_config)
        
        # Should include tag, classes, type but NOT data-index
        assert "tag" in result
        assert "classes" in result
        assert "type" in result
        assert "data-index" not in result
    
    def test_get_template_invariant_characteristics_without_indexing(self):
        """Should include all characteristics when no indexing needed"""
        templates = {
            "card": {
                "tag": "div",
                "classes": ["card"],
                "attrs": {"id": "main", "type": "card"}
            }
        }

        registry = TemplateRegistry(templates)
        
        mock_config = Mock()
        mock_config.needs_indexing.return_value = False
        
        result = registry.get_template_invariant_characteristics("card", mock_config)
        
        assert "tag" in result
        assert "classes" in result
        assert "id" in result
        assert "type" in result
    
    def test_get_template_invariant_characteristics_no_classes(self):
        """Should not include classes if template has no classes"""
        templates = {
            "simple": {
                "tag": "span",
                "attrs": {"id": "test"}
            }
        }
        registry = TemplateRegistry(templates)
        
        mock_config = Mock()
        mock_config.needs_indexing.return_value = False
        
        result = registry.get_template_invariant_characteristics("simple", mock_config)
        
        assert "tag" in result
        assert "classes" not in result
        assert "id" in result
    
    def test_form_template_selector_with_tag_and_classes(self):
        """Should form CSS selector with tag and classes"""
        templates = {
            "card": {
                "tag": "div",
                "classes": ["card", "item"],
                "attrs": {}
            }
        }
        registry = TemplateRegistry(templates)
        
        result = registry.form_template_selector("card",["tag","classes"])
        assert result == "div.card.item"
    
    def test_form_template_selector_with_tag_and_id(self):
        """Should form CSS selector with tag and id"""
        templates = {
            "main": {
                "tag": "div",
                "attrs": {"id": "main-container"}
            }
        }

        registry = TemplateRegistry(templates)
        
        result = registry.form_template_selector("main",["tag", "id"])
        assert result == "div#main-container"
    
    def test_form_template_selector_with_tag_classes_and_id(self):
        """Should form CSS selector with tag, classes, and id"""
        templates = {
            "complex": {
                "tag": "div",
                "classes": ["card", "item"],
                "attrs": {"id": "main"}
            }
        }
        registry = TemplateRegistry(templates)
        
        result = registry.form_template_selector("complex", ["tag", "classes", "id"])
        assert result == "div.card.item#main"
    
    def test_form_template_selector_with_custom_attributes(self):
        """Should form CSS selector with custom attributes"""
        templates = {
            "input": {
                "tag": "input",
                "classes": ["form-control"],
                "attrs": {"type": "text", "name": "username"}
            }
        }
        registry = TemplateRegistry(templates)
        
        result = registry.form_template_selector("input", ["tag", "classes", "type","name"])
        assert result == "input.form-control[type='text'][name='username']"
    
    def test_form_template_selector_raises_error_for_invalid_tag(self):
        """Should raise ValueError for invalid tag"""
        templates = {
            "invalid": {
                "tag": "notarealtag",
                "classes": []
            }
        }
        registry = TemplateRegistry(templates)
        
        with pytest.raises(ValueError, match="Invalid or missing tag"):
            registry.form_template_selector("invalid", ["tag"])
    
    def test_form_template_selector_raises_error_for_missing_tag(self):
        """Should raise ValueError when tag is missing"""
        templates = {
            "no_tag": {
                "classes": ["card"]
            }
        }

        registry = TemplateRegistry(templates)
        
        with pytest.raises(ValueError, match="Invalid or missing tag"):
            registry.form_template_selector("no_tag", ["tag"])


# ==================== TEST CONFIG QUERIES ====================

class TestConfigQueries:
    """Tests for ConfigQueries class"""
    
    @pytest.fixture
    def sample_config(self):
        """Sample configuration"""
        return {
            "exam_variant": {
                "needs_indexing": True,
                "indexing_attribute": "data-index",
                "skip_indices": [2, 5, 7]
            },
            "simple_card": {
                "needs_indexing": False
            }
        }
    
    @pytest.fixture
    def config_queries(self, sample_config):
        """Create ConfigQueries instance"""
        return ConfigQueries(sample_config)
    
    def test_get_template_config_existing_template(self, config_queries):
        """Should return config for existing template"""
        result = config_queries.get_template_config("exam_variant")
        
        assert result == {
            "needs_indexing": True,
            "indexing_attribute": "data-index",
            "skip_indices": [2, 5, 7]
        }
    
    def test_get_template_config_nonexistent_template(self, config_queries):
        """Should return None for non-existent template"""
        with pytest.raises(ValueError, match="Template 'nonexistent' not found in configuration"):
            config_queries.get_template_config("nonexistent")

    def test_needs_indexing_returns_true(self, config_queries):
        """Should return True when needs_indexing is True"""
        assert config_queries.needs_indexing("exam_variant") is True
    
    def test_needs_indexing_returns_false(self, config_queries):
        """Should return False when needs_indexing is False"""
        assert config_queries.needs_indexing("simple_card") is False
    
    def test_needs_indexing_defaults_to_false(self, config_queries):
        """Should default to False for missing config"""
        with pytest.raises(ValueError, match="Template 'nonexistent' not found in configuration"):
            config_queries.needs_indexing("nonexistent")
    
    def test_get_indexing_attribute_returns_attribute(self, config_queries):
        """Should return indexing attribute when present"""
        result = config_queries.get_indexing_attribute("exam_variant")
        assert result == "data-index"
    
    def test_get_indexing_attribute_returns_none(self, config_queries):
        """Should return None when indexing_attribute not present"""
        result = config_queries.get_indexing_attribute("simple_card")
        assert result is None
    
    def test_get_skip_indices_returns_list(self, config_queries):
        """Should return skip indices list when present"""
        result = config_queries.get_skip_indices("exam_variant")
        assert result == [2, 5, 7]
    
    def test_get_skip_indices_returns_none(self, config_queries):
        """Should return None when skip_indices not present"""
        result = config_queries.get_skip_indices("simple_card")
        assert result is None


# ==================== TEST SCHEMA QUERIES ====================

class TestSchemaQueries:
    """Tests for SchemaQueries class"""
    
    @pytest.fixture
    def sample_schema(self):
        """Sample schema structure"""
        return {
            "tag": "html",
            "description": "root",
            "children": [
                {
                    "tag": "body",
                    "description": "body",
                    "annotation": ["landmark_element"],
                    "children": [
                        {
                            "tag": "div",
                            "description": "container",
                            "repeat": {
                                "template": "exam_variant",
                                "count": 5
                            }
                        }
                    ]
                }
            ]
        }
    
    @pytest.fixture
    def schema_queries(self, sample_schema):
        """Create SchemaQueries instance"""
        return SchemaQueries(sample_schema)
    
    def test_get_repeat_info_with_repeat(self):
        """Should return repeat info when present"""
        schema_node = {
            "tag": "div",
            "repeat": {
                "template": "exam_variant",
                "count": 5
            }
        }
        queries = SchemaQueries({})
        
        result = queries.get_repeat_info(schema_node)
        assert result == {"template": "exam_variant", "count": 5}
    
    def test_get_repeat_info_without_repeat(self):
        """Should return None when no repeat present"""
        schema_node = {"tag": "div"}
        queries = SchemaQueries({})
        
        result = queries.get_repeat_info(schema_node)
        assert result is None
    
    def test_has_repeat_returns_true(self):
        """Should return True when repeat block exists"""
        schema_node = {"tag": "div", "repeat": {"template": "test", "count": 3}}
        queries = SchemaQueries({})
        
        assert queries.has_repeat(schema_node) is True
    
    def test_has_repeat_returns_false(self):
        """Should return False when no repeat block"""
        schema_node = {"tag": "div"}
        queries = SchemaQueries({})
        
        assert queries.has_repeat(schema_node) is False
    
    def test_has_children_returns_true_with_children(self):
        """Should return True when children array exists and has items"""
        schema_node = {
            "tag": "div",
            "children": [{"tag": "span"}]
        }
        queries = SchemaQueries({})
        
        assert queries.has_children(schema_node) is True
    
    def test_has_children_returns_false_with_empty_array(self):
        """Should return False when children array is empty"""
        schema_node = {"tag": "div", "children": []}
        queries = SchemaQueries({})
        
        assert queries.has_children(schema_node) is False
    
    def test_has_children_returns_false_without_children(self):
        """Should return False when no children key"""
        schema_node = {"tag": "div"}
        queries = SchemaQueries({})
        
        assert queries.has_children(schema_node) is False
    
    def test_get_children_returns_children_array(self):
        """Should return children array when present"""
        children = [{"tag": "div"}, {"tag": "span"}]
        schema_node = {"tag": "body", "children": children}
        queries = SchemaQueries({})
        
        result = queries.get_children(schema_node)
        assert result == children
    
    def test_get_children_returns_none_when_missing(self):
        """Should return None when children not present"""
        schema_node = {"tag": "div"}
        queries = SchemaQueries({})
        
        result = queries.get_children(schema_node)
        assert result is None
    
    def test_is_landmark_returns_true(self):
        """Should return True when landmark annotation present"""
        schema_node = {
            "tag": "div",
            "annotation": ["landmark_element"]
        }
        queries = SchemaQueries({})
        
        assert queries.is_landmark(schema_node) is True
    
    def test_is_landmark_returns_false_without_annotation(self):
        """Should return False when no annotation"""
        schema_node = {"tag": "div"}
        queries = SchemaQueries({})
        
        assert queries.is_landmark(schema_node) is False
    
    def test_is_landmark_returns_false_with_different_annotation(self):
        """Should return False when annotation is not landmark"""
        schema_node = {
            "tag": "div",
            "annotation": ["target_element"]
        }
        queries = SchemaQueries({})
        
        assert queries.is_landmark(schema_node) is False
    
    def test_is_target_returns_true(self):
        """Should return True when target annotation present"""
        schema_node = {
            "tag": "div",
            "annotation": ["target_element"]
        }
        queries = SchemaQueries({})
        
        assert queries.is_target(schema_node) is True
    
    def test_is_target_returns_false(self):
        """Should return False when target annotation not present"""
        schema_node = {"tag": "div"}
        queries = SchemaQueries({})
        
        assert queries.is_target(schema_node) is False
    
    def test_get_target_info_returns_target_dict(self):
        """Should return target info when present"""
        target_info = {
            "objective": "scrape",
            "types": ["country", "year"]
        }
        schema_node = {
            "tag": "div",
            "target": target_info
        }
        queries = SchemaQueries({})
        
        result = queries.get_target_info(schema_node)
        assert result == target_info
    
    def test_get_target_info_returns_none(self):
        """Should return None when target info not present"""
        schema_node = {"tag": "div"}
        queries = SchemaQueries({})
        
        result = queries.get_target_info(schema_node)
        assert result is None
    
    def test_get_target_type_returns_types_list(self):
        """Should return types list from target info"""
        schema_node = {
            "tag": "div",
            "target": {
                "objective": "scrape",
                "types": ["country", "year"]
            }
        }
        queries = SchemaQueries({})
        
        result = queries.get_target_type(schema_node)
        assert result == ["country", "year"]
    
    def test_get_target_type_returns_empty_string_when_no_target(self):
        """Should return empty string when no target info"""
        schema_node = {"tag": "div"}
        queries = SchemaQueries({})
        
        result = queries.get_target_type(schema_node)
        assert result == ""
    
    def test_get_target_objective_returns_objective(self):
        """Should return objective from target info"""
        schema_node = {
            "tag": "div",
            "target": {
                "objective": "scrape",
                "types": ["country"]
            }
        }
        queries = SchemaQueries({})
        
        result = queries.get_target_objective(schema_node)
        assert result == "scrape"
    
    def test_get_target_objective_returns_none(self):
        """Should return None when no target info"""
        schema_node = {"tag": "div"}
        queries = SchemaQueries({})
        
        result = queries.get_target_objective(schema_node)
        assert result is None
    
    def test_is_target_and_landmark_returns_true(self):
        """Should return True when both annotations present"""
        schema_node = {
            "tag": "div",
            "annotation": ["target_element", "landmark_element"]
        }
        queries = SchemaQueries({})
        
        assert queries.is_target_and_landmark(schema_node) is True
    
    def test_is_target_and_landmark_returns_false_only_target(self):
        """Should return False when only target annotation"""
        schema_node = {
            "tag": "div",
            "annotation": ["target_element"]
        }
        queries = SchemaQueries({})
        
        assert queries.is_target_and_landmark(schema_node) is False
    
    def test_is_target_and_landmark_returns_false_only_landmark(self):
        """Should return False when only landmark annotation"""
        schema_node = {
            "tag": "div",
            "annotation": ["landmark_element"]
        }
        queries = SchemaQueries({})
        
        assert queries.is_target_and_landmark(schema_node) is False
    
    def test_json_schema_has_repeat_returns_true(self):
        """Should return True when schema contains repeat anywhere"""
        schema = {
            "tag": "html",
            "children": [
                {
                    "tag": "body",
                    "children": [
                        {
                            "tag": "div",
                            "repeat": {"template": "test", "count": 5}
                        }
                    ]
                }
            ]
        }
        queries = SchemaQueries(schema)
        
        assert queries.json_schema_has_repeat() is True
    
    def test_json_schema_has_repeat_returns_false(self):
        """Should return False when no repeat in entire schema"""
        schema = {
            "tag": "html",
            "children": [
                {"tag": "body", "children": [{"tag": "div"}]}
            ]
        }
        queries = SchemaQueries(schema)
        
        assert queries.json_schema_has_repeat() is False


# ==================== TEST SCHEMA VALIDATOR ====================

class TestSchemaStructureValidator:
    """Tests for SchemaStructureValidator class"""
    
    @pytest.fixture
    def sample_schema(self):
        """Sample schema"""
        return {
            "tag": "html",
            "children": []
        }
    
    @pytest.fixture
    def mock_template_registry(self):
        """Mock TemplateRegistry"""
        mock = Mock(spec=TemplateRegistry)
        mock.template_exists.return_value = True
        return mock
    
    @pytest.fixture
    def mock_config_queries(self):
        """Mock ConfigQueries"""
        return Mock(spec=ConfigQueries)
    
    @pytest.fixture
    def mock_schema_queries(self):
        """Mock SchemaQueries"""
        mock = Mock(spec=SchemaQueries)
        mock.has_children.return_value = False
        mock.has_repeat.return_value = False
        mock.is_landmark.return_value = True
        return mock
    
    @pytest.fixture
    def validator(
        self,
        sample_schema,
        mock_template_registry,
        mock_config_queries,
        mock_schema_queries
    ):
        """Create SchemaStructureValidator instance"""
        return SchemaStructureValidator(
            sample_schema,
            mock_template_registry,
            mock_config_queries,
            mock_schema_queries
        )
    
    def test_validate_schema_with_valid_dict(self, validator):
        """Should not raise error for valid schema dict"""
        validator.validate_schema()  # Should pass without exception
    
    def test_validate_schema_with_invalid_type(
        self,
        mock_template_registry,
        mock_config_queries,
        mock_schema_queries
    ):
        """Should raise ValidationError for non-dict schema"""
        invalid_schemas = ["string", 123, [], None]
        
        for invalid_schema in invalid_schemas:
            validator = SchemaStructureValidator(
                invalid_schema,
                mock_template_registry,
                mock_config_queries,
                mock_schema_queries
            )
            
            with pytest.raises(ValidationError, match="Schema must be a dictionary"):
                validator.validate_schema()
    
    def test_validate_repeat_block_with_valid_block(self, validator):
        """Should not raise error for valid repeat block"""
        repeat_block = {
            "template": "exam_variant",
            "count": 5
        }
        
        validator.validate_repeat_block(repeat_block)  # Should pass
    
    def test_validate_repeat_block_with_auto_count(self, validator):
        """Should accept 'auto' as valid count"""
        repeat_block = {
            "template": "exam_variant",
            "count": "auto"
        }
        
        validator.validate_repeat_block(repeat_block)  # Should pass
    
    def test_validate_repeat_block_missing_template(self, validator):
        """Should raise ValidationError when template missing"""
        repeat_block = {"count": 5}
        
        with pytest.raises(ValidationError, match="Missing 'template'"):
            validator.validate_repeat_block(repeat_block)
    
    def test_validate_repeat_block_missing_count(self, validator):
        """Should raise ValidationError when count missing"""
        repeat_block = {"template": "exam_variant"}
        
        with pytest.raises(ValidationError, match="Missing 'count'"):
            validator.validate_repeat_block(repeat_block)
    
    def test_validate_repeat_block_with_zero_count(self, validator):
        """Should raise ValidationError for zero count"""
        repeat_block = {"template": "test", "count": 0}
        
        with pytest.raises(ValidationError, match="Count must be a positive integer"):
            validator.validate_repeat_block(repeat_block)
    
    def test_validate_repeat_block_with_negative_count(self, validator):
        """Should raise ValidationError for negative count"""
        repeat_block = {"template": "test", "count": -5}
        
        with pytest.raises(ValidationError, match="Count must be a positive integer"):
            validator.validate_repeat_block(repeat_block)
    
    def test_validate_repeat_block_parent_is_landmark(self, validator):
        """Should pass when parent of repeat is landmark"""
        schema_node = {
            "tag": "div",
            "annotation": ["landmark_element"],
            "children": [
                {"tag": "span", "repeat": {"template": "test", "count": 3}}
            ]
        }
        
        validator._schema_queries.has_children.return_value = True
        validator._schema_queries.get_children.return_value = schema_node["children"]
        validator._schema_queries.has_repeat.return_value = True
        validator._schema_queries.is_landmark.return_value = True
        
        validator.validate_repeat_block_paren(schema_node)  # Should pass
    
    def test_validate_repeat_block_parent_not_landmark(self, validator):
        """Should raise ValidationError when parent is not landmark"""
        schema_node = {
            "tag": "div",
            "children": [
                {"tag": "span", "repeat": {"template": "test", "count": 3}}
            ]
        }
        
        validator._schema_queries.has_children.return_value = True
        validator._schema_queries.get_children.return_value = schema_node["children"]
        validator._schema_queries.has_repeat.return_value = True
        validator._schema_queries.is_landmark.return_value = False
        
        with pytest.raises(ValidationError, match="Parent of repeat block must be a landmark"):
            validator.validate_repeat_block_paren(schema_node)
    
    def test_validate_repeat_block_parent_no_children(self, validator):
        """Should pass when parent has no children"""
        schema_node = {
            "tag": "div",
            "annotation": ["landmark_element"]
        }
        
        validator._schema_queries.has_children.return_value = False
        
        validator.validate_repeat_block_paren(schema_node)  # Should pass
    
    def test_validate_repeat_block_parent_children_no_repeat(self, validator):
        """Should pass when children have no repeat blocks"""
        schema_node = {
            "tag": "div",
            "children": [
                {"tag": "span"},
                {"tag": "p"}
            ]
        }
        
        validator._schema_queries.has_children.return_value = True
        validator._schema_queries.get_children.return_value = schema_node["children"]
        validator._schema_queries.has_repeat.return_value = False
        
        validator.validate_repeat_block_paren(schema_node)  # Should pass
    
    def test_validate_root_has_no_annotation_passes(
        self,
        mock_template_registry,
        mock_config_queries,
        mock_schema_queries
    ):
        """Should pass when root has no annotation"""
        schema = {"tag": "html", "children": []}
        
        validator = SchemaStructureValidator(
            schema,
            mock_template_registry,
            mock_config_queries,
            mock_schema_queries
        )
        
        validator.validate_root_has_no_annotation()  # Should pass
    
    def test_validate_root_has_no_annotation_fails(
        self,
        mock_template_registry,
        mock_config_queries,
        mock_schema_queries
    ):
        """Should raise ValidationError when root has annotation"""
        schema = {
            "tag": "html",
            "annotation": ["landmark_element"],
            "children": []
        }
        
        validator = SchemaStructureValidator(
            schema,
            mock_template_registry,
            mock_config_queries,
            mock_schema_queries
        )
        
        with pytest.raises(ValidationError, match="Root node must not have 'annotation' field"):
            validator.validate_root_has_no_annotation()
    
    def test_validate_target_info_with_valid_target(self, validator):
        """Should pass with valid target info"""
        schema_node = {
            "tag": "div",
            "annotation": ["target_element"],
            "target": {
                "objective": "scrape",
                "types": ["country", "year"]
            }
        }
        
        validator._schema_queries.get_target_info.return_value = schema_node["target"]
        
        validator.validate_target_info(schema_node)  # Should pass
    
    def test_validate_target_info_with_debug_objective(self, validator):
        """Should pass with debug objective"""
        schema_node = {
            "tag": "div",
            "annotation": ["target_element"],
            "target": {
                "objective": "debug",
                "types": ["exam_url"]
            }
        }
        
        target = validator._schema_queries.get_target_info.return_value = schema_node["target"]
        
        validator.validate_target_info(target)  # Should pass
    
    def test_validate_target_info_missing_objective(self, validator):
        """Should raise ValidationError when objective missing"""
        schema_node = {
            "tag": "div",
            "annotation": ["target_element"],
            "target": {
                "types": ["country"]
            }
        }
        
        validator._schema_queries.get_target_info.return_value = schema_node["target"]
        
        with pytest.raises(ValidationError, match="Target element must have 'objective' and 'types'"):
            validator.validate_target_info(schema_node)
    
    def test_validate_target_info_missing_types(self, validator):
        """Should raise ValidationError when types missing"""
        schema_node = {
            "tag": "div",
            "annotation": ["target_element"],
            "target": {
                "objective": "scrape"
            }
        }
        
        validator._schema_queries.get_target_info.return_value = schema_node["target"]
        
        with pytest.raises(ValidationError, match="Target element must have 'objective' and 'types'"):
            validator.validate_target_info(schema_node)
    
    def test_validate_target_info_types_not_list(self, validator):
        """Should raise ValidationError when types is not a list"""
        schema_node = {
            "tag": "div",
            "annotation": ["target_element"],
            "target": {
                "objective": "scrape",
                "types": "country"  # Should be a list
            }
        }
        
        validator._schema_queries.get_target_info.return_value = schema_node["target"]
        
        with pytest.raises(ValidationError, match="Target element must have 'objective' and 'types'"):
            validator.validate_target_info(schema_node)
    
    def test_validate_target_info_invalid_objective(self, validator):
        """Should raise ValidationError for invalid objective"""
        schema_node = {
            "tag": "div",
            "annotation": ["target_element"],
            "target": {
                "objective": "invalid_objective",
                "types": ["country"]
            }
        }
        
        validator._schema_queries.get_target_info.return_value = schema_node["target"]
        
        with pytest.raises(ValidationError, match="Invalid objective"):
            validator.validate_target_info(schema_node)
    
    def test_validate_target_info_invalid_type(self, validator):
        """Should raise ValidationError for invalid target type"""
        schema_node = {
            "tag": "div",
            "annotation": ["target_element"],
            "target": {
                "objective": "scrape",
                "types": ["country", "invalid_type"]
            }
        }
        
        validator._schema_queries.get_target_info.return_value = schema_node["target"]
        
        with pytest.raises(ValidationError, match="Invalid target types"):
            validator.validate_target_info(schema_node)
    
    def test_validate_target_info_no_target_field(self, validator):
        """Should pass when schema node has no target field"""
        schema_node = {
            "tag": "div"
        }
        
        validator._schema_queries.get_target_info.return_value = None
        
        validator.validate_target_info(schema_node)  # Should pass
    
    def test_validate_template_exists_when_exists(self, validator):
        """Should pass when template exists"""
        validator._template_registry.template_exists.return_value = True
        
        validator.validate_template_exists("exam_variant")  # Should pass
    
    def test_validate_template_exists_when_not_exists(self, validator):
        """Should raise ValidationError when template doesn't exist"""
        validator._template_registry.template_exists.return_value = False
        
        with pytest.raises(ValidationError, match="Template 'missing_template' does not exist"):
            validator.validate_template_exists("missing_template")
    
    def test_validate_config_passes(self, validator):
        """Should pass validation (currently no-op)"""
        validator.validate_config()  # Should pass
    
    def test_target_info_exist_returns_true(self, validator):
        """Should return True when target field exists"""
        schema_node = {
            "tag": "div",
            "target": {"objective": "scrape", "types": ["country"]}
        }
        
        result = validator.target_info_exist(schema_node)
        
        assert result is True
    
    def test_target_info_exist_returns_false(self, validator):
        """Should return False when target field doesn't exist"""
        schema_node = {
            "tag": "div"
        }
        
        result = validator.target_info_exist(schema_node)
        
        assert result is False