
from pathlib import Path
from dom_processing.my_scraper.interfaces import DocumentRetriever
from dom_processing.my_scraper.interfaces_implementations import ChineseContentTransformer, ChineseDriverOperations, ChineseImageURLPattern
from dom_processing.my_scraper.models import Instance
from dom_processing.my_scraper.services import MetadataProcessing, PDFConverter, PageDownloader


class ChineseDirectLinkDocumentRetriever(DocumentRetriever):

    def __init__(self, ) -> None:
        """Initialize with service dependencies."""
        try:
            self.image_patterns = ChineseImageURLPattern()
            self.metadata_processing = MetadataProcessing()
            self.page_downloader = PageDownloader()
            self.pdf_converter = PDFConverter()
            self.content_transformer = ChineseContentTransformer()
        except Exception as e:
            raise RuntimeError(f"Failed to initialize ChineseDirectLinkDocumentRetriever: {type(e).__name__}: {e}")
        
    def construct_document(
        self,
        doc_nodes,  # Can be a single node or list of nodes
        root_node,
        instance: Instance,
        state,
        driver,
    ) -> Path:
        """Construct document by downloading and converting to PDF.
        
        Args:
            doc_nodes: Single DOM node or list of nodes containing document links
            root_node: Root DOM node for page count extraction
            instance: Instance with metadata and config
            state: Document state ('exam' or 'solution')
            driver: Selenium driver for JavaScript execution
            
        Returns:
            Path to saved document
        """
        # Validate inputs
        if not doc_nodes:
            raise ValueError("doc_nodes cannot be None or empty")
        if not root_node:
            raise ValueError("root_node cannot be None")
        if not instance:
            raise ValueError("instance cannot be None")
        if state not in ["exam", "solution"]:
            raise ValueError(f"Invalid state '{state}': must be 'exam' or 'solution'")
        if not driver:
            raise ValueError("driver cannot be None")
        if not hasattr(instance, 'metadata'):
            raise AttributeError(f"Instance missing 'metadata' attribute. Instance type: {type(instance).__name__}")
        
        # Normalize input: convert single node to list
        if not isinstance(doc_nodes, list):
            doc_nodes = [doc_nodes]
        
        # Process metadata once (same for all nodes)
        content_transformation_config = {
            "need_year_conversion": False,
            "need_translation": True
        }
        
        try:
            processed_metadata = self.metadata_processing.process_metadata(
                instance,
                self.content_transformer, 
                content_transformation_config
            )
        except Exception as e:
            raise RuntimeError(f"Failed to process metadata for state '{state}': {e}")
        
        if not isinstance(processed_metadata, dict):
            raise ValueError(f"processed_metadata has the wrong type: expected dict, got {type(processed_metadata).__name__}")

        try:
            save_path = self.metadata_processing.build(processed_metadata, state)
        except Exception as e:
            raise RuntimeError(f"Failed to build save path for state '{state}': {e}")
        
        try:
            self.metadata_processing.ensure(save_path)
        except Exception as e:
            raise RuntimeError(f"Failed to create directory '{save_path}': {e}")
        
        # Initialize session and user agents once
        try:
            session = self.page_downloader._create_session_with_retry()
        except Exception as e:
            raise RuntimeError(f"Failed to create HTTP session: {type(e).__name__}: {e}")
        
        try:
            user_agents = self.page_downloader._get_user_agent_pool()
        except Exception as e:
            raise RuntimeError(f"Failed to initialize user-agent pool: {type(e).__name__}: {e}")
        
        # Download all pages
        for i, target_node in enumerate(reversed(doc_nodes),start=1):
            # Validate node structure
            if not hasattr(target_node, 'target_types'):
                print(f"Warning: Document node {i} missing 'target_types' attribute, skipping")
                continue
            
            if not target_node.target_types:
                continue
            
            # Process each target type
            for target_type in target_node.target_types:
                if not isinstance(target_type, str):
                    print(f"Warning: target_type is not a string (got {type(target_type).__name__}), skipping")
                    continue
                
                if not target_type.endswith("_url"):
                    continue  # Only process URL types in document processing
                
                # Extract image URL
                try:
                    image_url = self.image_patterns.get_raw_url(target_node)
                except Exception as e:
                    raise RuntimeError(f"Failed to get raw URL from node {i}: {e}")
                
                # Download page
                try: 
                    self.page_downloader.download_single_page(
                        index=i,
                        url=image_url,
                        session=session,
                        user_agents=user_agents,
                        save_path=save_path,
                        metadata=processed_metadata,
                        state=state,
                    )
                except Exception as e:
                    raise RuntimeError(f"Failed to download page {i} from {image_url}: {e}")
        
        # Convert all downloaded images to PDF
        try:
            self.pdf_converter.convert_document_pdf(str(save_path))
        except Exception as e:
            raise RuntimeError(
                f"Failed to convert images to PDF in '{save_path}' (state={state}): {e}"
            )
        
        return save_path
            



class ChineseReferenceBasedDocumentRetriever(DocumentRetriever):
    """Document retriever for Chinese exam websites."""
    
    def __init__(self, selenium_driver=None) -> None:
        """Initialize with service dependencies."""
        try:
            self.image_patterns = ChineseImageURLPattern()
            self.driver_ops = ChineseDriverOperations(selenium_driver)
            self.metadata_processing = MetadataProcessing()
            self.page_downloader = PageDownloader()
            self.pdf_converter = PDFConverter()
            self.content_transformer = ChineseContentTransformer()
        except Exception as e:
            raise RuntimeError(f"Failed to initialize ChineseReferenceBasedDocumentRetriever: {type(e).__name__}: {e}")

    def construct_document(
    self,
    download_node,
    root_node,
    instance: Instance,
    state,
    driver,
) -> Path:
        """Construct document by downloading and converting to PDF.
        
        Args:
            download_node: DOM node containing document link
            root_node: Root DOM node for page count extraction
            instance: Instance with metadata and config
            state: Document state ('exam' or 'solution')
            driver: Selenium driver for JavaScript execution
            
        Returns:
            Path to saved document
        """
        # Validate inputs
        if not download_node:
            raise ValueError("download_node cannot be None")
        if not root_node:
            raise ValueError("root_node cannot be None")
        if not instance:
            raise ValueError("instance cannot be None")
        if state not in ["exam", "solution"]:
            raise ValueError(f"Invalid state '{state}': must be 'exam' or 'solution'")
        if not driver:
            raise ValueError("driver cannot be None")
        
        # Validate node structure
        if not hasattr(download_node, 'target_types'):
            raise AttributeError("download_node missing 'target_types' attribute")
        
        if not download_node.target_types:
            raise ValueError("download_node.target_types is empty")

        if not isinstance(download_node.target_types, list):
            raise TypeError(f"target_types must be a list, got {type(download_node.target_types).__name__}")
        
        # Check first target type ends with "_url"
        if not any(t.endswith("_url") for t in download_node.target_types):
            raise ValueError("No URL target_type found in download_node")
        
        # Validate instance structure
        if not hasattr(instance, 'metadata'):
            raise AttributeError(f"Instance missing 'metadata' attribute. Instance type: {type(instance).__name__}")
        
        if not hasattr(instance.metadata, 'model_dump'):
            raise AttributeError(
                f"instance.metadata missing 'model_dump' method. "
                f"Metadata type: {type(instance.metadata).__name__}"
            )
        
        # Process metadata and build save path
        content_transformation_config = {
            "need_year_conversion": False,
            "need_translation": True
        }
        
        try:
            processed_metadata = self.metadata_processing.process_metadata(
                instance,
                self.content_transformer, 
                content_transformation_config
            )
        except Exception as e:
            raise RuntimeError(f"Failed to process metadata for state '{state}': {e}")
        
        try:
            save_path = self.metadata_processing.build(processed_metadata, state)
        except Exception as e:
            raise RuntimeError(f"Failed to build save path for state '{state}': {e}")
        
        try:
            self.metadata_processing.ensure(save_path)
        except Exception as e:
            raise RuntimeError(f"Failed to create directory '{save_path}': {e}")

        # Extract URL information from download node
        try:
            image_url_example = self.image_patterns.get_raw_url(download_node)
        except Exception as e:
            raise RuntimeError(f"Failed to get raw URL from download node (state={state}): {e}")
        
        try:
            suffix, start_index = self.image_patterns.extract_url_info(image_url_example)
        except Exception as e:
            raise RuntimeError(f"Failed to extract URL info from '{image_url_example}' (state={state}): {e}")

        try:
            extension = image_url_example.split('.')[-1]  # Gets "png" or "jpg"
            print(f"DEBUG: Detected extension: {extension}")
        except Exception as e:
            extension = "png"  # Default fallback
            print(f"DEBUG: Could not detect extension, using default: {extension}")

        try:
            base_url = self.image_patterns.get_url_base(image_url_example)
        except Exception as e:
            raise RuntimeError(f"Failed to get base URL from '{image_url_example}' (state={state}): {e}")

        # Get page count from driver
        try:
            page_count = self.driver_ops.get_page_count(driver)
            print(f"DEBUG: Retrieved page_count={page_count} for state={state}")
        except Exception as e:
            raise RuntimeError(f"Failed to get page count from driver (state={state}): {e}")

        # Build all image URLs
        try:
            start_index_int = int(start_index)
            all_images_urls = self.image_patterns.build_image_urls(
                suffix=suffix,
                start_index=start_index_int,
                base_url=base_url,
                page_count=page_count,
                extension=extension
            )
            print(f"DEBUG: Built {len(all_images_urls)} image URLs for state={state} (pages {start_index_int} to {page_count})")
        except Exception as e:
            raise RuntimeError(
                f"Failed to build image URLs (suffix={suffix}, start={start_index}, "
                f"base={base_url}, count={page_count}, state={state}): {e}"
            )

        # Prepare metadata for download

        
        # Download all pages
        try:
            self.page_downloader.download_document_pages(
                save_path=save_path,
                page_urls=all_images_urls,
                metadata=processed_metadata,
                state=state
            )
        except Exception as e:
            raise RuntimeError(
                f"Failed to download document pages to '{save_path}' (state={state}): {e}"
            )

        # Convert to PDF
        try:
            self.pdf_converter.convert_document_pdf(str(save_path))
        except Exception as e:
            raise RuntimeError(
                f"Failed to convert images to PDF in '{save_path}' (state={state}): {e}"
            )
        
        return save_path