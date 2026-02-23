from datetime import datetime
from db.database_repo import DatabaseRepository
from db.mappers import InstanceToRecordMapper
from dom.selenium_driver import SeleniumDriver
from dom_processing.dom_tree_builder.tree_building.tree_building_entry_point import BuildTree
from dom_processing.instance_tracker import Tracker
from dom_processing.my_scraper.document_retriever_implementations import ChineseDirectLinkDocumentRetriever, ChineseReferenceBasedDocumentRetriever
from dom_processing.my_scraper.models import Instance
from dom_processing.my_scraper.scraper_orchestrator.factory_functions import FactoryFunctions
from dom_processing.my_scraper.scraper_orchestrator.page_scraper import  PageScraper
from dom_processing.my_scraper.scraper_orchestrator.query_services import QueryServices
from dom_processing.my_scraper.scraper_orchestrator.subject_navigator import SubjectNavigator
from dom_processing.my_scraper.scraper_orchestrator.tree_utils import clone_tree_structure


class ScraperOrchestrator:
    """Orchestrates the complete exam scraping workflow."""
    
    def __init__(
        self,
        main_scraper_config_path: str,
        document_scraper_config_path: str,
        fallback_document_scraper_config_path:str,
        database_repository: DatabaseRepository, # Add this parameter
        instance_tracker: Tracker

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
        self.factory_functions = FactoryFunctions()
        self.tree_builder = BuildTree()
        self.mapper = InstanceToRecordMapper()  # Initialize mapper
        self.database_repository = database_repository  # ← this line is absent
        self.instance_tracker = instance_tracker


    def _build_page_tree(self, query_services, description="page"):
        """
        Factory function to build a page tree.
        
        Args:
            query_services: Query services object containing page_url and other config
            description: Human-readable description for error messages
            
        Returns:
            tree: The built page tree (driver is automatically closed)
            
        Raises:
            RuntimeError: If driver creation or page processing fails
        """
        try:
            driver = self.factory_functions.create_driver(query_services.page_url)
        except Exception as e:
            raise RuntimeError(f"Failed to create driver for {description} URL '{query_services.page_url}': {e}")
        
        try:
            tree = self.build_process(driver,query_services)
            return tree,driver
        except Exception as e:
            raise RuntimeError(f"Failed to process {description} tree: {e}")
        
    def build_process(self, driver: SeleniumDriver,query_services:QueryServices):
        """Build and return annotated DOM tree."""
        if not driver:
            raise ValueError("driver cannot be None")
        
        try:
            return self.tree_builder.build(
                driver,
                query_services.schema_queries,
                query_services.config_queries,
                query_services.template_registry
            )
        except Exception as e:
            raise RuntimeError(f"Failed to build DOM tree: {type(e).__name__}: {e}")
        
    def run(self):
        """Execute the complete scraping workflow."""

        
        try:
            # Build main page tree
            main_tree,main_driver = self._build_page_tree(
                self.main_query_services, 
                "main page"
            )
            main_tree.print_dom_tree()

            # Build document page tree template
            document_tree,document_driver = self._build_page_tree(
                self.document_query_services,
                "document page"
            )
            document_driver.close()

            # Build fallback document page tree
            fallback_document_tree,fallback_document_driver = self._build_page_tree(
                self.fallback_document_query_services,
                "fallback document page"
            )
            fallback_document_driver.close()
            
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

    def scrape_document_with_retry(self, document_type, url, document_tree, fallback_document_tree, instance, subject_index, total_subjects):
        """
        Generic method to scrape a document (exam or solution) with retry logic.
        
        Args:
            document_type: String "exam" or "solution"
            url: The URL to scrape
            document_tree: Primary tree structure
            fallback_document_tree: Fallback tree structure
            instance: Instance object to populate
            subject_index: Current subject index for logging
            total_subjects: Total number of subjects for logging
        
        Returns:
            bool: True if successful, False otherwise
        """
        max_retries = 2
        
        for attempt in range(max_retries):
            try:
                if attempt == 0:
                    # First attempt: Use primary scraper and tree
                    print(f"DEBUG: {document_type.capitalize()} attempt {attempt + 1}/{max_retries} with primary tree")
                    document_retriever_strategy = ChineseReferenceBasedDocumentRetriever()
                    document_page_scraper = PageScraper(self.document_query_services, document_retriever_strategy)
                    tree_copy = clone_tree_structure(document_tree)
                else:
                    # Second attempt: Use fallback scraper and tree
                    print(f"DEBUG: {document_type.capitalize()} attempt {attempt + 1}/{max_retries} with fallback tree")
                    document_retriever_strategy = ChineseDirectLinkDocumentRetriever()
                    document_page_scraper = PageScraper(self.fallback_document_query_services, document_retriever_strategy)
                    tree_copy = clone_tree_structure(fallback_document_tree)
                
                document_page_scraper.scrape_page(url, tree_copy, document_type, instance)
                print(f"DEBUG: {document_type.capitalize()} scraped successfully for subject {subject_index}/{total_subjects}")
                return True  # Success
                
            except RuntimeError as e:
                error_msg = str(e).lower()
                
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
                        print(f"Warning: {document_type.capitalize()} scraping failed on attempt {attempt + 1}, retrying with fallback")
                        print(f"  Error: {e}")
                        continue  # Try again with fallback
                    else:
                        # Final attempt failed
                        print(f"Error: {document_type.capitalize()} scraping failed after {max_retries} attempts")
                        print(f"  URL: {url}")
                        print(f"  Error: {e}")
                        return False
                else:
                    # Different RuntimeError, don't retry
                    print(f"Error: Non-retryable RuntimeError occurred: {e}")
                    raise
            
            except Exception as e:
                # Unexpected error (network, permission, etc.)
                print(f"Error: Unexpected error on attempt {attempt + 1}: {type(e).__name__}: {e}")
                raise
        
        return False  # All retries exhausted
    
    def _determine_scraping_status(self, has_exam, has_solution, exam_success, solution_success):
        """
        Determine the final scraping status based on what was attempted and what succeeded.
        
        Returns:
            tuple: (status, error_message)
                status: "success", "partial", or "failed"
                error_message: Description of what failed, or None
        """
        if has_exam and has_solution:
            if exam_success and solution_success:
                return "success", None
            elif exam_success or solution_success:
                failed_type = "solution" if exam_success else "exam"
                return "partial", f"Failed to scrape {failed_type}"
            else:
                return "failed", "Failed to scrape both exam and solution"
        elif has_exam:
            return ("success", None) if exam_success else ("failed", "Failed to scrape exam")
        elif has_solution:
            return ("success", None) if solution_success else ("failed", "Failed to scrape solution")
        else:
            return "failed", "No exam or solution URLs found"
        
    def _process_branch(self, branch_node, main_driver, main_tree, document_tree, fallback_document_tree):
        """Process a single subject type branch."""
        if not branch_node:
            raise ValueError("branch_node cannot be None")
        if not main_driver:
            raise ValueError("main_driver cannot be None")
        if not main_tree:
            raise ValueError("main_tree cannot be None")

        # Annotate branch
        try:
            annotator, coordinator = self.factory_functions.create_tree_annotator(
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

            # Initialise defaults so they're always defined
            instance = Instance()
            exam_id = None
            exam_success = False
            solution_success = False

            if has_exam:
                exam_url = documents_url_dict["exam_page_url"]

                try:
                    already_visited = self.instance_tracker.check_entry_page_exists_in_visited_urls(exam_url)
                except Exception as e:
                    print(f"Error checking visited URLs for exam '{exam_url}': {e}")
                    pass

                if already_visited:
                    try:
                        exam_id = self.instance_tracker.get_exam_id_by_url(exam_url)
                    except Exception as e:
                        print(f"Error retrieving exam_id from tracker for '{exam_url}': {e}")
                        pass
                else:
                    try:
                        exists_in_db = self.instance_tracker.check_entry_page_exists_in_exam_db(exam_url)
                    except Exception as e:
                        print(f"Error checking exam DB for '{exam_url}': {e}")
                        pass

                    if exists_in_db:
                        try:
                            exam_id = self.instance_tracker.get_exam_id_by_url(exam_url)
                        except Exception as e:
                            print(f"Error retrieving exam_id from DB for '{exam_url}': {e}")
                            pass

                        try:
                            self.instance_tracker.add_exam_entry_page_to_visited_urls(exam_url)
                        except Exception as e:
                            print(f"Warning: Failed to cache exam URL '{exam_url}' in visited list: {e}")

                    else:
                        exam_success = self.scrape_document_with_retry(
                            document_type="exam",
                            url=exam_url,
                            document_tree=document_tree,
                            fallback_document_tree=fallback_document_tree,
                            instance=instance,
                            subject_index=i,
                            total_subjects=len(subject_nodes)
                        )

                        if exam_success:
                            print("\n✓ SUCCESS: Exam scraped successfully")
                            print(f"Instance: {instance}")
                            if len(instance.exam_variant) == 1:
                                exam_record = self.mapper.map_to_single_exam_record(instance)
                                exam_id = self.database_repository.insert_exam_record(exam_record)
                            else:
                                exam_records = self.mapper.map_to_multiple_exam_records(instance)
                                for exam_record in exam_records:
                                    exam_id = self.database_repository.insert_exam_record(exam_record)

                            try:
                                self.instance_tracker.add_exam_entry_page_to_visited_urls(exam_url)
                            except Exception as e:
                                print(f"Warning: Failed to cache exam URL '{exam_url}' in visited list: {e}")
                        else:
                            print("\n✗ FAILURE: Could not scrape exam after all attempts")

            if has_solution:
                solution_url = documents_url_dict["solution_page_url"]

                try:
                    already_visited = self.instance_tracker.check_entry_page_exists_in_visited_urls(solution_url)
                except Exception as e:
                    print(f"Error checking visited URLs for solution '{solution_url}': {e}")
                    already_visited = False

                if already_visited:
                    pass
                else:
                    try:
                        exists_in_db = self.instance_tracker.check_entry_page_exists_in_solution_db(solution_url)
                    except Exception as e:
                        print(f"Error checking solution DB for '{solution_url}': {e}")
                        exists_in_db = False

                    if exists_in_db:
                        try:
                            self.instance_tracker.add_solution_entry_page_to_visited_urls(solution_url)
                        except Exception as e:
                            print(f"Warning: Failed to cache solution URL '{solution_url}' in visited list: {e}")
                    else:
                        setattr(instance.documents, "solution_exists", True)
                        solution_success = self.scrape_document_with_retry(
                            document_type="solution",
                            url=solution_url,
                            document_tree=document_tree,
                            fallback_document_tree=fallback_document_tree,
                            instance=instance,
                            subject_index=i,
                            total_subjects=len(subject_nodes)
                        )

                        if solution_success:
                            print("\n✓ SUCCESS: Solution scraped successfully")
                            print(f"Instance: {instance}")
                            if exam_id is None:
                                print("Warning: solution scraped but no exam_id available — skipping DB insert")
                            else:
                                solution_record = self.mapper.map_to_solution_record(instance)
                                self.database_repository.insert_solution_record(solution_record, exam_id)

                            try:
                                self.instance_tracker.add_solution_entry_page_to_visited_urls(solution_url)
                            except Exception as e:
                                print(f"Warning: Failed to cache solution URL '{solution_url}' in visited list: {e}")
                        else:
                            print("\n✗ FAILURE: Could not scrape solution after all attempts")
            
            
            instance.scraping_status, instance.error_message = self._determine_scraping_status(
                has_exam, has_solution, exam_success, solution_success
            )
            instance.scraped_at = datetime.now()

            print(f"\n{'='*50}")
            print(f"Final Status: {instance.scraping_status.upper()}")
            if instance.error_message:
                print(f"Error: {instance.error_message}")
            print(f"{'='*50}\n")