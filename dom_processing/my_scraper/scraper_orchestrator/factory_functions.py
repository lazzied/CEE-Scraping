
from typing import Tuple
from dom.selenium_driver import SeleniumDriver
from dom_processing.dom_tree_builder.caching.cache import HandleCaching
from dom_processing.dom_tree_builder.caching.coordinators import CachingCoordinator
from dom_processing.dom_tree_builder.caching.finders import SeleniumElementFinder
from dom_processing.dom_tree_builder.caching.selectors import SelectorBuilder
from dom_processing.dom_tree_builder.tree_annotation.annotate_tree import AnnotateTree
from dom_processing.json_parser import ConfigQueries, SchemaQueries, TemplateRegistry
from dom_processing.my_scraper.instance_assembler import InstanceAssembler
from dom_processing.my_scraper.interfaces import DocumentRetriever
from dom_processing.my_scraper.interfaces_implementations import ChineseTextParser


class FactoryFunctions:
    @staticmethod
    def create_driver(url: str, headless: bool = True) -> SeleniumDriver:
        """Create and initialize a Selenium driver."""
        if not url:
            raise ValueError("URL cannot be empty")
        
        try:
            driver = SeleniumDriver(headless=headless)
        except Exception as e:
            raise RuntimeError(f"Failed to initialize SeleniumDriver (headless={headless}): {type(e).__name__}: {e}")
        
        try:
            driver.get(url)
            return driver
        except Exception as e:
            try:
                driver.close()
            except:
                pass
            raise RuntimeError(f"Failed to navigate to URL '{url}': {type(e).__name__}: {e}")

    @staticmethod
    def create_tree_annotator(
        template_registry: TemplateRegistry,
        config_queries: ConfigQueries,
        schema_queries: SchemaQueries
    ) -> Tuple[AnnotateTree, CachingCoordinator]:
        """Create tree annotator with its dependencies."""
        if not schema_queries:
            raise ValueError("schema_queries cannot be None")
        
        try:
            annotator = AnnotateTree()
            finder = SeleniumElementFinder()
            cache_handler = HandleCaching(finder)
            selector_builder = SelectorBuilder(template_registry, config_queries)
            caching_coordinator = CachingCoordinator(
                cache_handler,
                selector_builder,
                schema_queries
            )
            return annotator, caching_coordinator
        except Exception as e:
            raise RuntimeError(f"Failed to create tree annotator components: {type(e).__name__}: {e}")

    @staticmethod
    def create_instance_assembler(
        schema_queries: SchemaQueries,document_retriever: DocumentRetriever
    ) -> InstanceAssembler:
        """Create instance assembler with Chinese text processing."""
        if not schema_queries:
            raise ValueError("schema_queries cannot be None")
        
        try:
            text_parser = ChineseTextParser()
            return InstanceAssembler(text_parser, document_retriever, schema_queries)
        except Exception as e:
            raise RuntimeError(f"Failed to create instance assembler: {type(e).__name__}: {e}")
