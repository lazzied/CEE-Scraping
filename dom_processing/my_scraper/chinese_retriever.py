"""
Chinese-specific implementations for document retrieval.
"""

import re
from pathlib import Path

from dom.node import DOMNode
from interfaces import ImageURLPattern, DocumentRetriever, TextParser
from services import MetadataProcessing, PageDownloader, PDFConverter
from models import Instance

class ChineseTextParser(TextParser):
        def get_multiple_metadata_values(self, title: str, types: list) -> dict:
            """
            Parse title to extract year, exam variant, and subject.
            
            Example format: "2025年高考全国一卷英语试题"
            
            Args:
                title: Title string from page
                
            Returns:
                Dictionary with year, exam_variant, and subject
            """
            year = title.split("年")[0]
            variant_part = title.split("高考")[1]
            subject_with_suffix = variant_part.split("试题")[0]
            
            exam_variant = subject_with_suffix[:-2]
            subject = subject_with_suffix[-2:]

            result ={
                "year": year,
                "exam_variant": exam_variant,
                "subject": subject
            }
        

            if self.validator(result,types):
                return result
            
        def validator(self, metadata: dict, types: list) -> bool:
            """
            Validate that metadata keys match exactly with the types list.
            
            Args:
                metadata: Dictionary returned from get_multiple_metadata_values
                types: List of expected metadata keys
                
            Returns:
                True if metadata keys match types exactly, False otherwise
            """
            metadata_keys = set(metadata.keys())
            expected_keys = set(types)
            
            return metadata_keys == expected_keys        



class ChineseImageURLPattern(ImageURLPattern):
    """Chinese exam website URL pattern parser."""
    
    def get_raw_url(self, node: DOMNode) -> str:
        """Extract raw URL from DOM node."""
        if node.tag == "img":
            url = node.web_element.get_attribute("src")
        elif node.tag == "a":
            url = node.web_element.get_attribute("href")
        else:
            raise ValueError("Node tag must be img or a")

        if url.startswith("data:"):
            raise ValueError("data URL not supported")

        return url

    def get_url_base(self, raw_url: str) -> str:
        """Extract base URL from full URL."""
        return raw_url.rsplit("/", 1)[0] + "/"

    def extract_url_info(self, raw_url: str) -> tuple[str, str]:
        """Extract suffix and starting index from URL.
        
        Example: image_abc01.png → ("abc", "01")
        """
        image_name = raw_url.split("/")[-1]
        stem = image_name.split(".")[0]
        match = re.match(r"([a-zA-Z]+)(\d+)", stem)
        if not match:
            raise ValueError("Match not found")
        return match.group(1), match.group(2)

    def build_image_urls(
        self, suffix: str, start_index: int, base_url: str, page_count: int
    ) -> list[str]:
        """Build list of image URLs from pattern."""
        urls = []
        for i in range(start_index, page_count + 1):
            suffix_num = f"{i:02d}"
            urls.append(f"{base_url}{suffix}{suffix_num}.png")
        return urls


class DriverOperations:
    """Base class for Selenium driver operations."""
    
    def __init__(self, selenium_driver=None):
        self.selenium_driver = selenium_driver


class ChineseDriverOperations(DriverOperations):
    """Chinese exam website driver operations."""
    
    def get_page_count(self, node) -> int:
        """Get page count from JavaScript variable."""
        target_node = node.find_in_node("tag","script")
        return target_node.web_element.execute_script("return _PAGE_COUNT;")


class ChineseDocumentRetriever(DocumentRetriever):
    """Document retriever for Chinese exam websites."""
    
    def __init__(self, selenium_driver=None) -> None:
        """Initialize with service dependencies."""
        self.image_patterns = ChineseImageURLPattern()
        self.driver_ops = ChineseDriverOperations(selenium_driver)
        self.metadata_processing = MetadataProcessing()
        self.page_downloader = PageDownloader()
        self.pdf_converter = PDFConverter()

    def get_document_content(self, node: DOMNode, schema_queries) -> str:
        """Get document content type from node.
        
        Returns:
            "exam" | "solution" | "exam_and_solution"
        """
        return schema_queries.get_document_content(node.schema_node)

    def construct_document(
        self,
        node: DOMNode,
        instance: Instance,
        schema_queries
    ) -> Path:
        """Construct document by downloading and converting to PDF.
        
        Args:
            node: DOM node containing document link
            instance: Instance with metadata and config
            schema_queries: Schema query service
            
        Returns:
            Path to saved document
        """
        # Build and create save path
        save_path = self.metadata_processing.build(instance.metadata)
        self.metadata_processing.ensure(save_path)

        # Extract URL information
        raw_url = self.image_patterns.get_raw_url(node)
        suffix, start_index = self.image_patterns.extract_url_info(raw_url)
        base_url = self.image_patterns.get_url_base(raw_url)

        # Get page count and build URLs

        page_count = self.driver_ops.get_page_count()
        urls = self.image_patterns.build_image_urls(
            suffix=suffix,
            start_index=int(start_index),
            base_url=base_url,
            page_count=page_count
        )

        # Determine document type
        document_content = self.get_document_content(node, schema_queries)

        # Download pages
        self.page_downloader.download_document_pages(
            save_path=save_path,
            page_urls=urls,
            metadata=instance.metadata.model_dump(),
            state=document_content
        )

        # Convert to PDF
        self.pdf_converter.convert_document_pdf(str(save_path))
        
        return save_path