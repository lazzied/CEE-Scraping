from typing import List, Dict, Optional, Literal, Any
from dom.my_stack import Stack
from enum import Enum


VALID_HTML_TAGS = {
    "html", "head", "body", "title", "meta", "link", "base", "style",
    "header", "nav", "main", "section", "article", "aside", "footer",
    "div", "span",
    "p", "h1", "h2", "h3", "h4", "h5", "h6",
    "br", "hr", "pre", "blockquote",
    "ol", "ul", "li", "dl", "dt", "dd",
    "figure", "figcaption",
    "a", "em", "strong", "small", "s", "cite", "q", "abbr", "time",
    "code", "var", "samp", "kbd", "sub", "sup", "i", "b", "u", "mark",
    "img", "audio", "video", "source", "track", "picture",
    "iframe", "embed", "object", "param",
    "canvas", "svg", "math",
    "table", "caption", "thead", "tbody", "tfoot",
    "tr", "th", "td", "colgroup", "col",
    "form", "input", "textarea", "button", "select",
    "option", "optgroup", "label", "fieldset", "legend",
    "datalist", "output", "progress", "meter",
    "details", "summary", "dialog",
    "script", "noscript", "template", "slot"
}

TargetTypes = [
    "country",
    "province", 
    "subject",
    "year",
    "exam_variant",
    "exam_url",
    "solution_url",
    "page_number",
]

class AnnotationType(Enum):
    LANDMARK = "landmark_element"
    TARGET = "target_element"


class ValidationError(Exception):
    """Simple validation error with message"""
    
    def __init__(self, message: str):
        self.message = message
        super().__init__(self.message)


# ==================== UTILITY CLASSES ====================

class HtmlValidator:
    """Utility class for HTML validation"""
    
    @staticmethod
    def is_valid_html_tag(tag: str) -> bool:
        """
        Input: tag (str)
        Functionality: Verify if a specific tag is a valid HTML tag
        Output: bool
        """
        return isinstance(tag, str) and tag.lower() in VALID_HTML_TAGS


class AttributeFormatter:
    """Handles attribute formatting and placeholder substitution"""
    
    #this is doomed to break
    @staticmethod
    def format_dynamic_attributes(
    attributes: Dict[str, Any],
    indexing_attribute: str,
    placeholder: str,
    value: Any
) -> Dict[str, Any]:
        
        formatted_attrs = {}
        for key, val in attributes.items():
            # Only process selected attributes and only if value is a string
            if key == indexing_attribute:
                new_value = val.replace(placeholder, str(value))
                formatted_attrs[key] = new_value
            else:
                formatted_attrs[key] = val

        return formatted_attrs


# ==================== REGISTRY CLASSES ====================

class TemplateRegistry:
    """Manages template definitions"""
    
    def __init__(self, templates: Dict):
        """
        Input: templates (dict) - Template definitions
        """
        self._templates = templates
    
    def get_template_schema(self, template_name: str) -> Dict:
        """
        Input: template_name (str) - Name of the template to retrieve
        Functionality: Extract specific template definition from templates
        Output: dict - The template schema definition
        """
        return self._templates.get(template_name)
    
    def get_all_template_names(self) -> List[str]:
        """
        Input: None
        Functionality: List all available template names
        Output: list[str]
        """
        return list(self._templates.keys())
    
    
    def template_exists(self, template_name: str) -> bool:
        """
        Input: template_name (str)
        Functionality: Check if referenced template is defined
        Output: bool
        """
        return template_name in self._templates

    def get_template_invariant_characteristics(self, template_name: str, template_config) -> List[str]:

        # currently the variable charcteristics are in the attributes only
        """
        Input: template_name (str)
        Functionality: Get characteristics that are consistent across all instances of a template
        Output: dict - Characteristics shared by all instances
        """

        template_schema = self.get_template_schema(template_name)

        # Start with 'classes' only if it exists in template schema
        result = ["tag"]
        if "classes" in template_schema:
            result.append("classes")

        # Add keys from attrs if any
        attrs_keys = list(template_schema.get("attrs", {}).keys())
        result.extend(attrs_keys)

        # Remove indexing attribute if needed
        if template_config.needs_indexing(template_name):
            indexing_attribute_key = template_config.get_indexing_attribute(template_name)
            if indexing_attribute_key in result:
                result.remove(indexing_attribute_key)

        return result


            # if indexing is needed, we cannot say anything is invariant

        # tag is always similar across instances
        # now we see class and id only if they are not dynamic means they need indexing
    def form_template_selector(self, template_name: str, invariant_chars: List[str]) -> str:
        """
        Forms a CSS selector from template characteristics
        Input: 
            - template_name (str)
            - invariant_chars (List[str]) - List of characteristics like ["tag", "classes", "id", "type"]
        Output: str - CSS selector like "div.class1.class2#my-id"
        """

        """
        # invariant_chars = ["tag", "classes", "id"]
        # Template: tag="div", classes=["card", "item"], attrs={"id": "main"}
        # Result: "div.card.item#main"

        # invariant_chars = ["tag", "id"]
        # Template: tag="button", attrs={"id": "submit", "type": "button"}
        # Result: "button#submit"

        # invariant_chars = ["tag", "classes", "type"]
        # Template: tag="input", classes=["form-control"], attrs={"type": "text", "name": "user"}
        # Result: "input.form-control[type='text']"
        
        """
        template_schema = self.get_template_schema(template_name)
        
        selector = ""
        
        # Process each characteristic in order
        for char in invariant_chars:
            if char == "tag":
                tag = template_schema.get("tag", "")
                if not tag or not HtmlValidator.is_valid_html_tag(tag):
                    raise ValueError(f"Invalid or missing tag for template '{template_name}'")
                selector += tag
            
            elif char == "classes":
                classes = template_schema.get("classes", [])
                for cls in classes:
                    selector += f".{cls}"
            
            else:
                # It's an attribute from attrs
                attrs = template_schema.get("attrs", {})
                if char in attrs:
                    value = attrs[char]
                    
                    # Special handling for 'id' - uses # in CSS selector
                    if char == "id":
                        selector += f"#{value}"
                    else:
                        # Other attributes use [attr=value] syntax
                        selector += f"[{char}='{value}']"
        
        return selector



class ConfigQueries:
    """Handles configuration queries"""
    
    def __init__(self, config: Dict):
        """
        Input: config (dict) - Configuration settings
        """
        self._config = config

    def get_template_config(self, template_name: str, version_name: str = "") -> Dict:
        """
        Input: template_name (str) - Name of the template
            version_name (str) - Optional configuration version name
        Functionality: Get runtime configuration for template
        Output: dict - Template-specific configuration settings
        """
        if template_name not in self._config:
            raise ValueError(f"Template '{template_name}' not found in configuration")
        
        template_config = self._config.get(template_name)
        
        # If version is specified, return that version
        if version_name:
            if not self._is_versioned_template(template_config):
                # Template is not versioned, but version was requested
                raise ValueError(
                    f"Template '{template_name}' does not have configuration versions, "
                    f"but version '{version_name}' was requested"
                )
            
            if version_name not in template_config:
                raise ValueError(
                    f"Configuration version '{version_name}' not found for template '{template_name}'. "
                    f"Available versions: {list(template_config.keys())}"
                )
            return template_config.get(version_name)
        
        # No version specified
        if self._is_versioned_template(template_config):
            # For selector building (structure-based queries), return first version
            # Since all versions share the same template structure
            first_version = next(iter(template_config.values()))
            return first_version
        
        # Non-versioned template, return directly
        return template_config
    
    def _is_versioned_template(self, template_config: Dict) -> bool:
        """
        Check if a template config uses versioning structure
        Returns True if all values are dicts (indicating versions)
        """
        if not template_config:
            return False
        
        # Check if all top-level values are dictionaries
        # This indicates versioned structure like: {"v1": {...}, "v2": {...}}
        return all(isinstance(v, dict) for v in template_config.values())
    
    def has_versions(self, template_name: str) -> bool:
        """
        Check if a template has multiple versions
        """
        if template_name not in self._config:
            return False
        
        template_config = self._config.get(template_name)
        return self._is_versioned_template(template_config)
    
    def get_available_versions(self, template_name: str) -> List[str]:
        """
        Get list of available version names for a template
        """
        if not self.has_versions(template_name):
            return []
        
        return list(self._config.get(template_name).keys())
    
    def needs_indexing(self, template_name: str, version_name: str = "") -> bool:
        """
        Input: template_name (str), version_name (str)
        Functionality: Check if template requires index tracking
        Output: bool
        """
        config = self.get_template_config(template_name, version_name)
        return config.get("needs_indexing", False) is True
    
    def get_placeholder(self, template_name: str, version_name: str = "") -> str:
        """
        Input: template_name (str), version_name (str)
        Functionality: Get the index placeholder for the template
        Output: str
        """
        config = self.get_template_config(template_name, version_name)
        return config.get("placeholder", "")
    
    def get_indexing_attribute(self, template_name: str, version_name: str = "") -> str:
        """
        Input: template_name (str), version_name (str)
        Functionality: Get attribute used for indexing instances of the template
        Output: str
        """
        config = self.get_template_config(template_name, version_name)
        return config.get("indexing_attribute", "")
    
    def get_skip_indices(self, template_name: str, version_name: str = "") -> List[int]:
        """
        Input: template_name (str), version_name (str)
        Functionality: Get list of indices to skip during repeat
        Output: list[int]
        """
        config = self.get_template_config(template_name, version_name)
        return config.get("skip_indices", [])
    
    def get_starting_index(self, template_name: str, version_name: str = "") -> int:
        """
        Input: template_name (str), version_name (str)
        Functionality: Get starting index for the template
        Output: int
        """
        config = self.get_template_config(template_name, version_name)
        return config.get("starting_index", 1)
    
    def get_finish_index(self, template_name: str, version_name: str = "") -> int:
        """
        Input: template_name (str), version_name (str)
        Functionality: Get starting index for the template
        Output: int
        """
        config = self.get_template_config(template_name, version_name)
        return config.get("finish_index")
    
    def get_precache_bool(self,template_name):
        template_config = self.get_template_config(template_name)
        if "precache" in template_config:
            return template_config["precache"]



# ==================== SCHEMA QUERIES ====================

class SchemaQueries:
    """Queries schema structure; this is for template and schema; any json file that describes the html DOM structure"""
    """
        self._schema = root/full schema (entire document)
        schema_node parameter = specific node being queried (local operation)
    """
    def __init__(self, schema: Dict):
        """
        Input: schema (dict) - Schema definition

        this takes in the entire schema, and the methods operat on schema_nodes
        """
        self._schema = schema
    
    def get_repeat_info(self, schema_node: Dict) -> Optional[Dict]:
        """
        Input: schema_node (dict) - A schema node that may contain repeat block
        Functionality: Extract repeat block information (template name, count, type)
        Output: dict - {"template": str, "count": int|"auto"} or None
        """
        return schema_node.get("repeat")
    
    def get_static_schema_node_attrs(self, schema_node: Dict) -> Dict:
        """
        Input: schema_node (dict) - Schema containing attrs
        Functionality: Return attributes as-is without formatting
        Output: dict - Attributes
        """
        return schema_node.get("attrs", {}).copy()
    
    def get_dynamic_schema_node_attrs(
        self, 
        schema_node: Dict, 
        indexing_attribute: str,
        placeholder: str, 
        index: str
    ) -> Dict:
        """
        Input: 
            - schema_node (dict) - Schema containing attrs
            - placeholder (str) - Placeholder string to replace
            - index (int, optional) - Index for formatting placeholders
        Functionality: Handle attribute formatting, especially {index} placeholder substitution
        Output: dict - Processed attributes with formatted values
        """
    
        attributes = schema_node.get("attrs", {})
        return AttributeFormatter.format_dynamic_attributes(attributes, indexing_attribute, placeholder, index)
    
    #make query on the entire schema
    
    def json_schema_has_repeat(self) -> bool:
        """
        Input: None
        Functionality: Check if root schema or any descendant has repeat block
        Output: bool
        """
        current = self._schema.get("main_schema")
        stk = Stack()
        stk.push(current)
        
        while not stk.is_empty():
            current = stk.pop()
            
            if self.has_repeat(current):
                return True
            
            if "children" in current:
                for child in current["children"]:
                    stk.push(child)
        
        return False
    
    def is_root(self, schema_node: Dict) -> bool:
        """
        Input: schema_node (dict)
        Functionality: Check if the given schema node is the root node
        Output: bool
        """
        return schema_node["description"] == "root"
    
    def has_repeat(self, schema_node: Dict) -> bool:
        """
        Input: schema_node (dict)
        Functionality: Check if this specific schema node contains repeat block
        Output: bool
        """
        return "repeat" in schema_node
    
    def has_conditional(self, schema_node: Dict) -> bool:

        return "conditional" in schema_node
    

    def get_condition_id(self,schema_node: Dict):
        return schema_node["conditional"]["condition_id"]

    def has_children(self, schema_node: Dict) -> bool:
        """
        Input: schema_node (dict)
        Functionality: Check if schema has children array
        Output: bool
        """
        children = schema_node.get("children", [])
        return isinstance(children, list) and len(children) > 0
    
    def get_children(self, schema_node: Dict) -> List[Dict]:
        """
        Input: schema_node (dict)
        Functionality: Return children array from schema
        Output: list[dict]
        """
        return schema_node.get("children")
    
    def is_landmark(self, schema_node: Dict) -> bool:
        """
        Input: schema_node (dict)
        Functionality: Check if node is a landmark element for caching
        Output: bool
        """
        annotation = schema_node.get("annotation","")
        
        if annotation:
            return "landmark_element" in annotation
        else:
            return False
        
    
    def is_target(self, schema_node: Dict) -> bool:
        """
        Input: schema_node (dict)
        Functionality: Check if node is a target element 
        Output: bool
        """
        annotation = schema_node.get("annotation","")

        if annotation:
            return "target_element" in annotation
        else:
            return False
       
        
    
    def get_target_info(self, schema_node: Dict) -> Optional[Dict]:
        """
        Input: schema_node (dict)
        Functionality: Extract target information from schema node
        Output: dict or None
        """
        return schema_node.get("target")
    
    def get_target_type(self, schema_node: Dict) -> List["str"]:
        """
        Input: schema_node (dict)
        Functionality: Get target type from schema node
        Output: str
        """
        target_info = self.get_target_info(schema_node)
        if target_info and "types" in target_info:
            return target_info["types"]
        return ""
    
    def is_target_and_landmark(self, schema_node: Dict) -> bool:
        """
        Input: schema_node (dict)
        Functionality: Check if node is both target and landmark element
        Output: bool
        """
        return self.is_target(schema_node) and self.is_landmark(schema_node)
    
    def get_invariant_characteristics(self, schema: Dict[str, Any]) -> List[str]:
        """
        Get characteristics that are consistent for a schema.

        Args:
            schema (Dict): Schema containing 'tag', 'classes', 'attrs', etc.

        Returns:
            List[str]: Ordered list of characteristics, e.g. ['tag', 'classes', 'id', 'type']
        """
        result = ["tag"]

        if "classes" in schema and schema["classes"]:
            result.append("classes")

        attrs_keys = list(schema.get("attrs", {}).keys())
        result.extend(attrs_keys)

        return result
    
    def form_selector_from_schema(self, schema: Dict, invariant_chars: List[str]) -> str:
        """
        Forms a CSS selector from any schema characteristics.

        Args:
            schema (Dict): Any schema containing "tag", "classes", "attrs", etc.
            invariant_chars (List[str]): Characteristics to include, e.g. ["tag", "classes", "id", "type"]

        Returns:
            str: CSS selector like "div.card.item#main[type='text']"
        """

        selector = ""

        for char in invariant_chars:
            if char == "tag":
                tag = schema.get("tag", "")
                if not tag or not HtmlValidator.is_valid_html_tag(tag):
                    raise ValueError(f"Invalid or missing tag in schema: {schema}")
                selector += tag

            elif char == "classes":
                classes = schema.get("classes", [])
                for cls in classes:
                    selector += f".{cls}"

            else:
                attrs = schema.get("attrs", {})
                if char in attrs:
                    value = attrs[char]
                    if char == "id":
                        selector += f"#{value}"
                    else:
                        selector += f"[{char}='{value}']"

        return selector
    




class SchemaStructureValidator:
    """Validates schema, templates, and configuration"""

    #RULES FOR BUILDING SCHEMA:
    #the parent of the repeat block must be a LANDMARK ELEMENTS; will add that later
    
    def __init__(
        self,
        schema: Dict,
        template_registry: TemplateRegistry,
        config_queries: ConfigQueries,
        schema_queries: SchemaQueries
    ):
        """
        Input:
            - schema (dict) - Schema definition
            - template_registry (TemplateRegistry) - Template registry instance
            - config_queries (ConfigQueries) - Config queries instance
        """
        self._schema = schema
        self._template_registry = template_registry
        self._config_queries = config_queries
        self._schema_queries = schema_queries
    
    def validate_schema(self) -> None:
        """
        Input: None (uses self._schema)
        Functionality: Validate schema has required fields (tag, structure)
        Output: None
        Raises: ValidationError if invalid
        """
        if not isinstance(self._schema, dict):
            raise ValidationError("Schema must be a dictionary")
    
    def validate_config(self) -> None:
        """
        Input: None (uses self._config_queries)
        Functionality: Ensure config only references templates that exist
        Output: None
        Raises: ValidationError if invalid
        """
        # Config validation logic can be expanded here
        pass
    
    def validate_repeat_block(self, repeat_block: Dict) -> None:
        """
        Input: repeat_block (dict) - The repeat section from schema
        Functionality: Ensure repeat block has required fields (template, count)
        Output: None
        Raises: ValidationError if invalid
        """
        if "template" not in repeat_block:
            raise ValidationError("Missing 'template' in repeat block")
        
        if "count" not in repeat_block:
            raise ValidationError("Missing 'count' in repeat block")
        
        count = repeat_block["count"]
        if count != "auto" and (not isinstance(count, int) or count <= 0):
            raise ValidationError("Count must be a positive integer or 'auto'")
    
    def validate_repeat_block_paren(self, schema_node: Dict) -> None:
        # note in json schema, the parent child is a one way relationship, 
        """
        input: schema_node
        functionality: check if the schema node has children with repeat block, if yes, check if the schema_node is a landmark element
        output: None
        """
        if self._schema_queries.has_children(schema_node):
            children = self._schema_queries.get_children(schema_node)
            for child in children:
                if self._schema_queries.has_repeat(child):
                    if not self._schema_queries.is_landmark(schema_node):
                        raise ValidationError("Parent of repeat block must be a landmark element")
                    
    def validate_root_has_no_annotation(self) -> None:
        """
        Input: None (uses self._schema)
        Functionality: Ensure root node doesn't have annotation field
        Output: None
        Raises: ValidationError if root has annotation
        """
        if "annotation" in self._schema:
            raise ValidationError("Root node must not have 'annotation' field")
    
    def validate_target_info(self, schema_node: dict) -> None:
        """
        Input: target (dict) - Target element schema node
        Functionality: Ensure target elements have required target info (objective, types)
        Output: None
        Raises: ValidationError if invalid
        """
        def _validate_target_elements(target: dict) -> None:
            if "objective" not in target or "types" not in target or not isinstance(target["types"], list):
                raise ValidationError("Target element must have 'objective' and 'types' in target info")

            if target["objective"] not in ["debug", "scrape"]:
                raise ValidationError(f"Invalid objective: {target['objective']}")

            if not all(t in TargetTypes for t in target["types"]):
                raise ValidationError(f"Invalid target types: {target['types']}")

        target = self._schema_queries.get_target_info(schema_node)
        if target is not None:
            _validate_target_elements(target)

    
    def validate_template_exists(self, template_name: str) -> None:
        """
        Input: template_name (str)
        Functionality: Check if referenced template is defined
        Output: None
        Raises: ValidationError if template doesn't exist
        """
        if not self._template_registry.template_exists(template_name):
            raise ValidationError(f"Template '{template_name}' does not exist")

    
    def target_info_exist(self,schema_node: Dict) -> None:
        self._schema_queries.is_target(schema_node)
        return "target" in schema_node


class ConfigValidator:
    def __init__(self):
        pass


