from dom_processing.json_parser import ConfigQueries, TemplateRegistry


class SelectorBuilder:
    """Builds CSS selectors from templates - separated for testability"""
    
    def __init__(
        self,
        template_registry: TemplateRegistry,
        config_queries: ConfigQueries
    ):
        self._template_registry = template_registry
        self._config_queries = config_queries
    
    def build_selector_for_template(self, template_name: str) -> str:
        """
        Build CSS selector for a template
        
        Input: template_name
        Output: CSS selector string
        """
        invariant_chars = self._template_registry.get_template_invariant_characteristics(
            template_name,
            self._config_queries
        )
        return self._template_registry.form_template_selector(template_name, invariant_chars)