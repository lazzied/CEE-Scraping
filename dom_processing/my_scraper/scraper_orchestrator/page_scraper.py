from dom.selenium_driver import SeleniumDriver
from dom_processing.dom_tree_builder.tree_building.tree_building_entry_point import BuildTree
from dom_processing.my_scraper.document_retriever_implementations import ChineseDirectLinkDocumentRetriever, ChineseReferenceBasedDocumentRetriever
from dom_processing.my_scraper.interfaces import DocumentRetriever
from dom_processing.my_scraper.models import Instance
from dom_processing.my_scraper.scraper_orchestrator.factory_functions import FactoryFunctions
from dom_processing.my_scraper.scraper_orchestrator.query_services import QueryServices
from dom_processing.my_scraper.scraper_orchestrator.tree_utils import clone_tree_structure




class PageScraper:
    
    def __init__(self, document_query_services: QueryServices,document_retriever:DocumentRetriever): # here we specify the technique
        if not document_query_services:
            raise ValueError("document_query_services cannot be None")
        
        self.document_query_services = document_query_services
        self.factory_functions = FactoryFunctions()
        try:
            self.instance_assembler = self.factory_functions.create_instance_assembler(
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
            document_page_driver = self.factory_functions.create_driver(url)
            
            # Annotate tree with current page
            try:
                self._annotate_tree(document_page_driver, document_tree)
            except Exception as e:
                raise RuntimeError(f"Failed to annotate tree: {e}")
            
            instance_document_url_name = state + "_entry_page_url"
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
            annotator, coordinator = self.factory_functions.create_tree_annotator(
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

    