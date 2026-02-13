from pathlib import Path
from typing import Tuple

from dom.selenium_driver import SeleniumDriver
from dom_processing.config.scraper_config import ScraperConfig
from dom_processing.dom_tree_builder.tree_building.tree_building_entry_point import BuildTree
from dom_processing.dom_tree_builder.tree_annotation.annotate_tree import AnnotateTree
from dom_processing.dom_tree_builder.caching.cache import HandleCaching
from dom_processing.dom_tree_builder.caching.coordinators import CachingCoordinator
from dom_processing.dom_tree_builder.caching.finders import SeleniumElementFinder
from dom_processing.dom_tree_builder.caching.selectors import SelectorBuilder
from dom_processing.json_parser import ConfigQueries, SchemaQueries, TemplateRegistry
from dom_processing.my_scraper.interfaces import DocumentRetriever
from dom_processing.my_scraper.interfaces_implementations import ChineseTextParser
from dom_processing.my_scraper.document_retriever_implementations import (ChineseDirectLinkDocumentRetriever,
    ChineseReferenceBasedDocumentRetriever)
from dom_processing.my_scraper.instance_assembler import InstanceAssembler
from dom_processing.my_scraper.models import Instance
from utils import load_json_from_project



# Configuration Loading

class QueryServices:
    """Loads and manages scraper configuration and schemas."""
    
    PROJECT_ROOT = Path("C:/Users/user/Desktop/CEE/SeleniumBot/json_schemas")
    
    def __init__(self, config_path: str):
        self.config_path = config_path
        self.page_url = None
        self.schema_queries = None
        self.config_queries = None
        self.template_registry = None
    
    def initialize_query_services(self) -> 'QueryServices':
        """Load all configuration and schema files."""
        try:
            scraper_config = ScraperConfig(self.config_path)
            scraper_config.load_config()
            
            self.page_url = scraper_config.get_page_url()
            if not self.page_url:
                raise ValueError(f"Page URL not found in config file: {self.config_path}")
            
            schema_paths = scraper_config.get_schema_paths()
            if not schema_paths:
                raise ValueError(f"Schema paths not found in config file: {self.config_path}")
            
            # Load schemas
            if "page_schema" not in schema_paths:
                raise KeyError(f"'page_schema' key missing in schema_paths from config: {self.config_path}")
            
            try:
                page_schema = load_json_from_project(
                    schema_paths["page_schema"],
                    str(self.PROJECT_ROOT)
                )
            except FileNotFoundError:
                raise FileNotFoundError(
                    f"Page schema file not found: {schema_paths['page_schema']} "
                    f"(Project root: {self.PROJECT_ROOT})"
                )
            except Exception as e:
                raise RuntimeError(f"Failed to load page schema from {schema_paths['page_schema']}: {e}")

            try:
                self.schema_queries = SchemaQueries(page_schema)
            except Exception as e:
                raise RuntimeError(f"Failed to initialize SchemaQueries with page schema: {e}")

            if "templates_config" in schema_paths:
                try:
                    config_schema = load_json_from_project(
                        schema_paths["templates_config"],
                        str(self.PROJECT_ROOT)
                    )
                    self.config_queries = ConfigQueries(config_schema)
                except FileNotFoundError:
                    raise FileNotFoundError(
                        f"Templates config file not found: {schema_paths['templates_config']} "
                        f"(Project root: {self.PROJECT_ROOT})"
                    )
                except Exception as e:
                    raise RuntimeError(f"Failed to load templates config from {schema_paths['templates_config']}: {e}")

            if "templates" in schema_paths:
                try:
                    templates_schema = load_json_from_project(
                        schema_paths["templates"],
                        str(self.PROJECT_ROOT)
                    )
                    self.template_registry = TemplateRegistry(templates_schema)
                except FileNotFoundError:
                    raise FileNotFoundError(
                        f"Templates file not found: {schema_paths['templates']} "
                        f"(Project root: {self.PROJECT_ROOT})"
                    )
                except Exception as e:
                    raise RuntimeError(f"Failed to load templates from {schema_paths['templates']}: {e}")
                
            return self
        except (FileNotFoundError, ValueError, KeyError, RuntimeError):
            raise
        except Exception as e:
            raise RuntimeError(f"Unexpected error initializing query services from {self.config_path}: {type(e).__name__}: {e}")


# Factory Functions

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


# Core Processing Classes

class PageProcessor:
    """Processes a page by building and annotating its DOM tree."""
    
    def __init__(self, query_services: QueryServices):
        if not query_services:
            raise ValueError("query_services cannot be None")
        if not query_services.schema_queries:
            raise ValueError("query_services.schema_queries cannot be None")
        
        self.query_services = query_services
        self.tree_builder = BuildTree()
    
    def process(self, driver: SeleniumDriver):
        """Build and return annotated DOM tree."""
        if not driver:
            raise ValueError("driver cannot be None")
        
        try:
            return self.tree_builder.build(
                driver,
                self.query_services.schema_queries,
                self.query_services.config_queries,
                self.query_services.template_registry
            )
        except Exception as e:
            raise RuntimeError(f"Failed to build DOM tree: {type(e).__name__}: {e}")


class PageScraper:
    
    def __init__(self, document_query_services: QueryServices,document_retriever:DocumentRetriever): # here we specify the technique
        if not document_query_services:
            raise ValueError("document_query_services cannot be None")
        
        self.document_query_services = document_query_services
        try:
            self.instance_assembler = create_instance_assembler(
                document_query_services.schema_queries,document_retriever
            )
        except Exception as e:
            raise RuntimeError(f"Failed to initialize PageScraper: {e}")
 
    
    def scrape_page(self, url: str, document_tree, state, instance: Instance) -> Instance:
        if not url:
            raise ValueError("URL cannot be empty")
        if not document_tree:
            raise ValueError("document_tree cannot be None")
        if state not in ["exam", "solution"]:
            raise ValueError(f"Invalid state '{state}': must be 'exam' or 'solution'")
        if not instance:
            raise ValueError("instance cannot be None")
        
        document_page_driver = None
        try:
            document_page_driver = create_driver(url)
            
            # Annotate tree with current page
            try:
                self._annotate_tree(document_page_driver, document_tree)
            except Exception as e:
                raise RuntimeError(f"Failed to annotate tree: {e}")
            
            instance_document_url_name = state + "_url"
            setattr(instance.documents, instance_document_url_name, url)
            
            if state == "exam":
                try:
                    self.instance_assembler.set_instance_metadata_attributes(
                        document_tree, instance, document_page_driver
                    )
                except Exception as e:
                    raise RuntimeError(f"Failed to assemble metadata attributes for {url}: {e}")
            
            try:
                self.instance_assembler.set_instance_document_attributes(
                    document_tree, instance, state, document_page_driver
                )
            except Exception as e:
                raise RuntimeError(f"Failed to assemble document attributes for {url} (state={state}): {e}")
            
            # Success - return instance
            return instance
        
        finally:
            # CRITICAL: Always close driver (success or failure)
            if document_page_driver:
                try:
                    document_page_driver.close()
                except:
                    pass  # Silent close


    def _annotate_tree(self, driver: SeleniumDriver, tree):
        """Annotate DOM tree with current driver."""
        if not driver:
            raise ValueError("driver cannot be None")
        if not tree:
            raise ValueError("tree cannot be None")
        
        print(f"DEBUG: Annotating tree with driver session (checking driver object)")
        
        try:
            annotator, coordinator = create_tree_annotator(
                self.document_query_services.template_registry,
                self.document_query_services.config_queries,
                self.document_query_services.schema_queries
            )
        except Exception as e:
            raise RuntimeError(f"Failed to create tree annotator: {e}")
        
        try:
            annotator.annotate_tree(
                driver,
                tree,
                coordinator,
                self.document_query_services.schema_queries,
                self.document_query_services.config_queries,
                self.document_query_services.template_registry
            )
            print(f"DEBUG: Tree annotation completed")
        except Exception as e:
            raise RuntimeError(f"Failed to annotate tree: {type(e).__name__}: {e}")


class SubjectNavigator:
    """Navigates through subjects and extracts exam URLs."""
    
    @staticmethod
    def get_documents_url(subject_node) -> dict:
        """Extract exam and solution URLs from subject node.
        
        Returns:
            Dictionary with 'exam_page_url' and/or 'solution_page_url' keys
        """
        if not subject_node:
            raise ValueError("subject_node cannot be None")
        
        try:
            a_nodes = subject_node.find_in_node("tag", "a", True) #hardcoded
        except Exception as e:
            raise RuntimeError(f"Failed to find <a> tags in subject node: {type(e).__name__}: {e}")
        
        if not a_nodes:
            return {}
        
        document_urls = {}
        
        for node in a_nodes:
            try:
                if not hasattr(node, 'target_types'):
                    continue
                
                if "exam" in node.target_types:
                    if not hasattr(node, 'web_element'):
                        print(f"Warning: Node with 'exam' target_type has no web_element attribute")
                        continue
                    try:
                        href = node.web_element.get_attribute("href")
                        if href:
                            document_urls["exam_page_url"] = href
                    except Exception as e:
                        print(f"Warning: Failed to get href for exam node: {e}")
                
                if "solution" in node.target_types:
                    if not hasattr(node, 'web_element'):
                        print(f"Warning: Node with 'solution' target_type has no web_element attribute")
                        continue
                    try:
                        href = node.web_element.get_attribute("href")
                        if href:
                            document_urls["solution_page_url"] = href
                    except Exception as e:
                        print(f"Warning: Failed to get href for solution node: {e}")
            except Exception as e:
                print(f"Warning: Error processing node for URLs: {e}")
                continue
        
        return document_urls


# Main Orchestrator

class ScraperOrchestrator:
    """Orchestrates the complete exam scraping workflow."""
    
    def __init__(
        self,
        main_scraper_config_path: str,
        document_scraper_config_path: str,
        fallback_document_scraper_config_path:str,
    ):
        if not main_scraper_config_path:
            raise ValueError("main_scraper_config_path cannot be empty")
        if not document_scraper_config_path:
            raise ValueError("document_scraper_config_path cannot be empty")
        
        try:
            self.main_query_services = QueryServices(main_scraper_config_path).initialize_query_services()
        except Exception as e:
            raise RuntimeError(f"Failed to initialize main query services from '{main_scraper_config_path}': {e}")
        
        try:
            self.document_query_services = QueryServices(document_scraper_config_path).initialize_query_services()
        except Exception as e:
            raise RuntimeError(f"Failed to initialize document query services from '{document_scraper_config_path}': {e}")
        
        try:
            self.fallback_document_query_services = QueryServices(fallback_document_scraper_config_path).initialize_query_services()
        except Exception as e:
            raise RuntimeError(f"Failed to initialize document query services from '{fallback_document_scraper_config_path}': {e}")
        
        self.subject_navigator = SubjectNavigator()
    
    def run(self):
        """Execute the complete scraping workflow."""
        main_driver = None
        document_driver = None
        fallback_document_driver = None
        
        try:
            # Build main page tree
            try:
                main_driver = create_driver(self.main_query_services.page_url)
            except Exception as e:
                raise RuntimeError(f"Failed to create main driver for URL '{self.main_query_services.page_url}': {e}")
            
            try:
                main_processor = PageProcessor(self.main_query_services)
                main_tree = main_processor.process(main_driver) #build main trree
            except Exception as e:
                raise RuntimeError(f"Failed to process main page tree: {e}")
            
            main_tree.print_dom_tree()
            
            # Build document page tree template (this is the default)
            try:
                document_driver = create_driver(self.document_query_services.page_url)
            except Exception as e:
                raise RuntimeError(f"Failed to create document driver for URL '{self.document_query_services.page_url}': {e}")
            
            try:
                document_processor = PageProcessor(self.document_query_services)
                document_tree = document_processor.process(document_driver) #build document tree
                document_driver.close()
            except Exception as e:
                raise RuntimeError(f"Failed to process document page tree: {e}")
            
            # build fallback document page tree
            try:
                fallback_document_driver = create_driver(self.fallback_document_query_services.page_url)
            except Exception as e:
                raise RuntimeError(f"Failed to create document driver for URL '{self.fallback_document_query_services.page_url}': {e}")
            
            try:
                fallback_document_processor = PageProcessor(self.fallback_document_query_services)
                fallback_document_tree = fallback_document_processor.process(fallback_document_driver) #build document tree
                fallback_document_driver.close()
            except Exception as e:
                raise RuntimeError(f"Failed to process document page tree: {e}")

            
            # Process each subject type branch
            try:
                subject_type_branches = main_tree.find_in_node("id", "st{1-33!2,4}", True)
            except Exception as e:
                raise RuntimeError(f"Failed to find subject type branches in main tree: {e}")
            
            if not subject_type_branches:
                print("Warning: No subject type branches found matching pattern 'st{1-33!2,4}'")
                return
            
            for i, branch in enumerate(subject_type_branches, 1):
                try:
                    self._process_branch(branch, main_driver,main_tree, document_tree,fallback_document_tree)
                except Exception as e:
                    print(f"Error processing branch {i}/{len(subject_type_branches)}: {type(e).__name__}: {e}")
                    continue
        finally:
            if main_driver:
                try:
                    main_driver.close()
                except Exception as e:
                    print(f"Warning: Failed to close main driver: {e}")
            if document_driver:
                try:
                    document_driver.close()
                except Exception as e:
                    print(f"Warning: Failed to close document driver: {e}")



    
    def _process_branch(self, branch_node, main_driver, main_tree,document_tree,fallback_document_tree):
        """Process a single subject type branch."""
        if not branch_node:
            raise ValueError("branch_node cannot be None")
        if not main_driver:
            raise ValueError("main_driver cannot be None")
        if not main_tree:
            raise ValueError("main_tree cannot be None")
        
        # Annotate branch
        try:
            annotator, coordinator = create_tree_annotator(
                self.main_query_services.template_registry,
                self.main_query_services.config_queries,
                self.main_query_services.schema_queries
            )
        except Exception as e:
            raise RuntimeError(f"Failed to create tree annotator for branch: {e}")
        
        try:
            annotator.annotate_tree(
                main_driver, branch_node, coordinator,
                self.main_query_services.schema_queries,
                self.main_query_services.config_queries,
                self.main_query_services.template_registry
            )
        except Exception as e:
            raise RuntimeError(f"Failed to annotate branch tree: {type(e).__name__}: {e}")
        
        # Process each subject
        try:
            subject_nodes = branch_node.find_in_node("tag", "li", True)
        except Exception as e:
            raise RuntimeError(f"Failed to find subject nodes in branch: {e}")
        
        if not subject_nodes:
            print("Warning: No subject nodes (<li> tags) found in branch")
            return
        
        for i, subject_node in enumerate(subject_nodes, 1):
                try:
                    documents_url_dict = self.subject_navigator.get_documents_url(subject_node)
                except Exception as e:
                    print(f"Error extracting URLs from subject node {i}/{len(subject_nodes)}: {e}")
                    continue
                
                if not documents_url_dict:
                    print(f"Info: No URLs found for subject node {i}/{len(subject_nodes)}")
                    continue
                
                has_exam = "exam_page_url" in documents_url_dict
                has_solution = "solution_page_url" in documents_url_dict
                
                # Create ONE instance for both exam and solution
                
                
                if has_exam:

                    max_retries = 2
                    exam_success = False
                    
                    for attempt in range(max_retries):
                        instance = Instance()
                        try:
                            if attempt == 0:
                                # First attempt: Use primary scraper and tree
                                print(f"DEBUG: Exam attempt {attempt + 1}/{max_retries} with primary tree")
                                document_retriever_strategy = ChineseReferenceBasedDocumentRetriever()
                                document_page_scraper = PageScraper(self.document_query_services,document_retriever_strategy)
                                exam_tree_copy = clone_tree_structure(document_tree)
                                exam_page_url = self.document_query_services.page_url

                            else:
                                # Second attempt: Use fallback scraper and tree
                                print(f"DEBUG: Exam attempt {attempt + 1}/{max_retries} with fallback tree")
                                document_retriever_strategy = ChineseDirectLinkDocumentRetriever()

                                document_page_scraper = PageScraper(self.fallback_document_query_services,document_retriever_strategy)
                                exam_tree_copy = clone_tree_structure(fallback_document_tree)
                            
                                exam_page_url = self.fallback_document_query_services.page_url
                            
                            document_page_scraper.scrape_page(
                                exam_page_url,
                                exam_tree_copy,
                                "exam",
                                instance
                            )
                            print(f"DEBUG: Exam scraped successfully for subject {i}/{len(subject_nodes)}")
                            exam_success = True
                            break  # Success, exit retry loop
                            
                        except RuntimeError as e:
                            error_msg = str(e).lower()  # Convert to lowercase for easier matching
                            
                            # Check if it's any kind of retryable error (schema mismatch)
                            retryable_errors = [
                                "failed to annotate tree",
                                "failed to assemble document attributes",
                                "failed to assemble metadata attributes",
                                "web element didn't get assigned",
                                "element not found on page",
                                "web_element is none"
                            ]
                            
                            is_retryable = any(err in error_msg for err in retryable_errors)
                            
                            if is_retryable:
                                if attempt < max_retries - 1:
                                    print(f"Warning: Exam scraping failed on attempt {attempt + 1}, retrying with fallback")
                                    print(f"  Error: {e}")
                                    continue  # Try again with fallback
                                else:
                                    # Final attempt failed
                                    print(f"Error: Exam scraping failed after {max_retries} attempts")
                                    print(f"  URL: {exam_page_url}")
                                    print(f"  Error: {e}")
                                    break
                            else:
                                # Different RuntimeError, don't retry (e.g., validation error)
                                print(f"Error: Non-retryable RuntimeError occurred: {e}")
                                raise
                        
                        except Exception as e:
                            # Unexpected error (network, permission, etc.)
                            print(f"Error: Unexpected error on attempt {attempt + 1}: {type(e).__name__}: {e}")
                            raise
                    if exam_success:
                        print("\n✓ SUCCESS: Exam scraped successfully")
                        print(f"Instance: {instance}")
                    else:
                        print("\n✗ FAILURE: Could not scrape exam after all attempts")
            
                if has_solution:
                    max_retries = 2
                    solution_success = False
                    
                    for attempt in range(max_retries):
                        try:
                            if attempt == 0:
                                # First attempt: Use primary scraper and tree
                                print(f"DEBUG: Solution attempt {attempt + 1}/{max_retries} with primary tree")
                                document_retriever_strategy = ChineseReferenceBasedDocumentRetriever()
                                document_page_scraper = PageScraper(self.document_query_services,document_retriever_strategy)
                                solution_tree_copy = clone_tree_structure(document_tree)
                                solution_page_url = self.document_query_services.page_url

                            else:
                                # Second attempt: Use fallback scraper and tree
                                print(f"DEBUG: Solution attempt {attempt + 1}/{max_retries} with fallback tree")
                                document_retriever_strategy = ChineseDirectLinkDocumentRetriever() #  to develop
                                document_page_scraper = PageScraper(self.fallback_document_query_services,document_retriever_strategy)
                                solution_tree_copy = clone_tree_structure(fallback_document_tree)
                                solution_page_url = self.fallback_document_query_services.page_url

                            document_page_scraper.scrape_page(
                                solution_page_url,
                                solution_tree_copy,
                                "solution",
                                instance
                            )
                            print(f"DEBUG: Solution scraped successfully for subject {i}/{len(subject_nodes)}")
                            solution_success = True
                            break  # Success, exit retry loop
                            
                        except RuntimeError as e:
                            error_msg = str(e).lower()  # Convert to lowercase for easier matching
                            
                            # Check if it's any kind of retryable error (schema mismatch)
                            retryable_errors = [
                                "failed to annotate tree",
                                "failed to assemble document attributes",
                                "failed to assemble metadata attributes",
                                "web element didn't get assigned",
                                "element not found on page",
                                "web_element is none"
                            ]
                            
                            is_retryable = any(err in error_msg for err in retryable_errors)
                            
                            if is_retryable:
                                if attempt < max_retries - 1:
                                    print(f"Warning: Exam scraping failed on attempt {attempt + 1}, retrying with fallback")
                                    print(f"  Error: {e}")
                                    continue  # Try again with fallback
                                else:
                                    # Final attempt failed
                                    print(f"Error: Exam scraping failed after {max_retries} attempts")
                                    print(f"  URL: {exam_page_url}")
                                    print(f"  Error: {e}")
                                    break
                            else:
                                # Different RuntimeError, don't retry (e.g., validation error)
                                print(f"Error: Non-retryable RuntimeError occurred: {e}")
                                raise
                        
                        except Exception as e:
                            # Unexpected error (network, permission, etc.)
                            print(f"Error: Unexpected error on attempt {attempt + 1}: {type(e).__name__}: {e}")
                            raise
                    if solution_success:
                        print("\n✓ SUCCESS: Exam scraped successfully")
                        print(f"Instance: {instance}")
                    else:
                        print("\n✗ FAILURE: Could not scrape exam after all attempts")

# Entry Point
def clone_tree_structure(node):
    """Recursively clone tree structure without web elements."""
    import copy
    
    # Create a shallow copy of the node
    new_node = copy.copy(node)
    
    # Clear the web_element reference (will be refilled during annotation)
    if hasattr(new_node, 'web_element'):
        new_node.web_element = None
    
    # Recursively clone children
    if hasattr(node, 'children') and node.children:
        new_node.children = [clone_tree_structure(child) for child in node.children]
    
    return new_node
def main():
    try:
        orchestrator = ScraperOrchestrator(
            main_scraper_config_path="dom_processing/config/main_scraper_config.json",
            document_scraper_config_path="dom_processing/config/document_scraper_config.json",
            fallback_document_scraper_config_path="dom_processing/config/fallback_document_scraper_config.json"
        )
        orchestrator.run()
    except Exception as e:
        print(f"Fatal error in main: {type(e).__name__}: {e}")
        raise


if __name__ == "__main__":
    main()