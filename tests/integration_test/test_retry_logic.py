# Will scrape the exam page only, detect an error, and retry with the fallback
# Nevermind the main page traversing, only focus on the document

from dom_processing.my_scraper.document_retriever_implementations import ChineseDirectLinkDocumentRetriever, ChineseReferenceBasedDocumentRetriever
from dom_processing.my_scraper.models import Instance
from main import PageProcessor, PageScraper, QueryServices, clone_tree_structure, create_driver

# Config paths
document_scraper_config_path = "dom_processing/config/document_scraper_config.json"
fallback_document_scraper_config_path = "dom_processing/config/fallback_document_scraper_config.json"

# Initialize query services
document_query_services = QueryServices(document_scraper_config_path).initialize_query_services()
fallback_document_query_services = QueryServices(fallback_document_scraper_config_path).initialize_query_services()

# Build default document tree
document_driver = create_driver(document_query_services.page_url)
document_processor = PageProcessor(document_query_services)
document_tree = document_processor.process(document_driver)
document_driver.close()

# Build fallback document tree
fallback_document_driver = create_driver(fallback_document_query_services.page_url)
fallback_document_processor = PageProcessor(fallback_document_query_services)
fallback_document_tree = fallback_document_processor.process(fallback_document_driver)
fallback_document_driver.close()

# Retry logic\\\
max_retries = 2
exam_success = False

default_exam_page_url = document_query_services.page_url
fallback_exam_page_url = fallback_document_query_services.page_url

for attempt in range(max_retries):
    instance = Instance()  # Fresh instance for each attempt
    
    try:
        if attempt == 0:
            # First attempt: Use primary scraper and tree
            print(f"DEBUG: Exam attempt {attempt + 1}/{max_retries} with primary tree")
            document_retriever_strategy = ChineseReferenceBasedDocumentRetriever()
            document_page_scraper = PageScraper(document_query_services,document_retriever_strategy)

            exam_tree_copy = clone_tree_structure(document_tree)
            exam_page_url = fallback_exam_page_url
        else:
            # Second attempt: Use fallback scraper and tree
            print(f"DEBUG: Exam attempt {attempt + 1}/{max_retries} with fallback tree")
            document_retriever_strategy = ChineseDirectLinkDocumentRetriever()

            document_page_scraper = PageScraper(fallback_document_query_services,document_retriever_strategy)
            exam_tree_copy = clone_tree_structure(fallback_document_tree)
            exam_page_url = fallback_exam_page_url

            exam_tree_copy.print_dom_tree()
        
        # Try to scrape
        document_page_scraper.scrape_page(
            exam_page_url,
            exam_tree_copy,
            "exam",
            instance
        )
        
        # If we reach here, scraping succeeded
        print(f"DEBUG: Exam scraped successfully on attempt {attempt + 1}")
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

# Check final status
if exam_success:
    print("\n✓ SUCCESS: Exam scraped successfully")
    print(f"Instance: {instance}")
else:
    print("\n✗ FAILURE: Could not scrape exam after all attempts")