import json
from selenium.webdriver.common.by import By
from dom.selenium_driver import SeleniumDriver
from dom_processing.dom_tree_builder.caching.cache import HandleCaching
from dom_processing.dom_tree_builder.caching.coordinators import CachingCoordinator
from dom_processing.dom_tree_builder.caching.finders import SeleniumElementFinder
from dom_processing.dom_tree_builder.caching.selectors import SelectorBuilder
from dom_processing.dom_tree_builder.tree_building.tree_building_strategies import RepeatTreeBuilderStrategy, SimpleTreeBuilderStrategy
from dom_processing.json_parser import ConfigQueries, SchemaQueries, TemplateRegistry

class BuildTree:
    def get_schemas_paths(self, schema_files_paths_dict: dict) -> dict:
        schemas = {}
        for name, path in schema_files_paths_dict.items():
            with open(path, "r", encoding="utf-8") as f:
                schemas[name] = json.load(f)
        return schemas


    

    def decide_strategy(self, schema_queries: SchemaQueries):
        if RepeatTreeBuilderStrategy.should_apply(schema_queries):
            return RepeatTreeBuilderStrategy()
        return SimpleTreeBuilderStrategy()

    def create_caching_coordinator(self,
        schema_queries: SchemaQueries,
        config_queries: ConfigQueries,
        template_registry: TemplateRegistry
    ) -> CachingCoordinator:
        element_finder = SeleniumElementFinder()
        cache_handler = HandleCaching(element_finder=element_finder)
        selector_builder = SelectorBuilder(
            template_registry=template_registry,
            config_queries=config_queries
        )
        return CachingCoordinator(
            cache_handler=cache_handler,
            selector_builder=selector_builder,
            schema_queries=schema_queries
        )
    @staticmethod
    def get_root_web_element(
        selenium_driver: SeleniumDriver,
        schema_queries: SchemaQueries
    ):
        root_selector = schema_queries.form_selector_from_schema(
            schema_queries._schema["main_schema"],
            schema_queries.get_invariant_characteristics(schema_queries._schema["main_schema"])
        )
        return selenium_driver.driver.find_element(By.CSS_SELECTOR, root_selector)

    def build_tree(self,
        strategy,
        schema_queries: SchemaQueries,
        config_queries: ConfigQueries,
        template_registry: TemplateRegistry,
        caching_coordinator: CachingCoordinator
    ):
        if isinstance(strategy, RepeatTreeBuilderStrategy):
            return strategy.build_node_tree_from_top(
                schema_queries=schema_queries,
                config_queries=config_queries,
                template_registry=template_registry,
                caching_coordinator=caching_coordinator
            )
        elif isinstance(strategy, SimpleTreeBuilderStrategy):
            return strategy.build_node_tree_from_top(
                schema_queries=schema_queries
            )
        raise ValueError("Unknown strategy")


    def build(self,driver, schema_queries,
                                config_queries,
                                template_registry):
        caching_coordinator = self.create_caching_coordinator(
            schema_queries,
            config_queries,
            template_registry
        )
        #here we call the driver: setting up 
        root_element = self.get_root_web_element( driver, schema_queries)
        caching_coordinator.initialize_with_root(root_element)
        strategy = self.decide_strategy(schema_queries)

        tree_root = self.build_tree(
            strategy=strategy,
            schema_queries=schema_queries,
            config_queries=config_queries,
            template_registry=template_registry,
            caching_coordinator=caching_coordinator
        )
        

        return tree_root

