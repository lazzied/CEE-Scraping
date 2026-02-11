import json
from selenium.webdriver.common.by import By
from dom.selenium_driver import SeleniumDriver
from dom_processing.dom_tree_builder.caching.cache import HandleCaching
from dom_processing.dom_tree_builder.caching.coordinators import CachingCoordinator
from dom_processing.dom_tree_builder.caching.finders import SeleniumElementFinder
from dom_processing.dom_tree_builder.caching.selectors import SelectorBuilder
from dom_processing.dom_tree_builder.tree_building.tree_building_strategies import RepeatTreeBuilderStrategy, SimpleTreeBuilderStrategy
from dom_processing.json_parser import ConfigQueries, SchemaQueries, TemplateRegistry
from utils import load_json_from_project
import dom_processing.dom_tree_builder.tree_building.conditions


"""
example:

BASE_DIR = Path(__file__).resolve().parent

SCHEMA_FILES = {
    "main": BASE_DIR / "html_page.json",
    "templates": BASE_DIR / "html_page_templates.json",
    "config": BASE_DIR / "html_page_templates_config.json"
}

TEST_LINK = "http://127.0.0.1:5500/tests/integration_test/test.html"


"""

class BuildTree:
    def get_schemas_paths(self, schema_files_paths_dict: dict) -> dict:
        schemas = {}
        for name, path in schema_files_paths_dict.items():
            with open(path, "r", encoding="utf-8") as f:
                schemas[name] = json.load(f)
        return schemas


    def load_driver(self,link: str, headless: bool = True) -> SeleniumDriver:
        driver = SeleniumDriver(headless=headless)
        driver.get(link)
        return driver

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

    def get_root_web_element(self,
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


    def build(self,page_url: str, schema_queries,
                                config_queries,
                                template_registry):
        driver = self.load_driver(page_url)
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


"""
class BuildAndAnnotateTree:

    #this builds and annotate in one go, needed for schemas that don't have repeat and pages navigation
    def load_schemas(self, schema_files_paths_dict: dict) -> dict:
        schemas = {}
        for name, path in schema_files_paths_dict.items():
            with open(path, "r", encoding="utf-8") as f:
                schemas[name] = json.load(f)
        return schemas


    def load_driver(self,link: str, headless: bool = True) -> SeleniumDriver:
        driver = SeleniumDriver(headless=headless)
        driver.get(link)
        return driver

    def decide_strategy(self,schema: dict, schema_queries: SchemaQueries):
        if RepeatTreeBuilderStrategy.should_apply(schema_queries, schema):
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

    def get_root_web_element(self,
        schema: dict,
        selenium_driver: SeleniumDriver,
        schema_queries: SchemaQueries
    ):
        root_selector = schema_queries.form_selector_from_schema(
            schema,
            schema_queries.get_invariant_characteristics(schema)
        )
        return selenium_driver.driver.find_element(By.CSS_SELECTOR, root_selector)

    def build_tree(self,
        strategy,
        schema_node: dict,
        schema_queries: SchemaQueries,
        config_queries: ConfigQueries,
        template_registry: TemplateRegistry,
        caching_coordinator: CachingCoordinator
    ):
        if isinstance(strategy, RepeatTreeBuilderStrategy):
            return strategy.build_node_tree_from_top(
                schema_node=schema_node,
                schema_queries=schema_queries,
                config_queries=config_queries,
                template_registry=template_registry,
                caching_coordinator=caching_coordinator
            )
        elif isinstance(strategy, SimpleTreeBuilderStrategy):
            return strategy.build_node_tree_from_top(
                schema_node=schema_node,
                schema_queries=schema_queries
            )
        raise ValueError("Unknown strategy")

    def annotate_tree(self,
        annotate_tree_obj: AnnotateTree,
        tree_root,
        caching_coordinator: CachingCoordinator,
        schema_queries: SchemaQueries
    ):
        annotate_tree_obj.annotate_tree(
            tree_root=tree_root,
            caching_coordinator=caching_coordinator,
            schema_query=schema_queries
        )

    def build_and_annotate(self,page_url: str, schema_files_paths_dict:dict):
        schemas = self.load_schemas(schema_files_paths_dict)
        main_schema = schemas["main"]
        config_schema = schemas["config"]
        templates_schema = schemas["templates"]

        schema_queries = SchemaQueries(main_schema)
        config_queries = ConfigQueries(config_schema)
        template_registry = TemplateRegistry(templates_schema)

        driver = self.load_driver(page_url)
        caching_coordinator = self.create_caching_coordinator(
            schema_queries,
            config_queries,
            template_registry
        )
        #here we call the driver: setting up 
        root_element = self.get_root_web_element(main_schema, driver, schema_queries)
        caching_coordinator.initialize_with_root(root_element)
        strategy = self.decide_strategy(schema_queries, main_schema)

        tree_root = self.build_tree(
            strategy=strategy,
            schema_node=main_schema,
            schema_queries=schema_queries,
            config_queries=config_queries,
            template_registry=template_registry,
            caching_coordinator=caching_coordinator
        )
        

        annotator = AnnotateTree()

        self.annotate_tree(
            annotate_tree_obj=annotator,
            tree_root=tree_root,
            caching_coordinator=caching_coordinator,
            schema_queries=schema_queries
        )
        tree_root.print_dom_tree()

        return tree_root, driver
"""