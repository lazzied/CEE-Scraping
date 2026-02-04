"""
Abstract interfaces for the scraping system.
"""

from abc import ABC, abstractmethod
from typing import Any
from pathlib import Path

from dom.node import DOMNode
from models import Instance


class TextParser(ABC):
    """Interface for parsing text content to extract metadata."""
    
    @abstractmethod
    def get_single_metadata_value(self, text: str, metadata_type: str) -> Any:
        """Extract a single metadata value from text."""
        pass

    @abstractmethod
    def get_multiple_metadata_values(self, text: str, metadata_types: list) -> dict:
        """Extract multiple metadata values from text."""
        pass


class ContentTransformer(ABC):
    """Interface for transforming content (translation, conversion)."""
    
    @abstractmethod
    def translate_to_english(self, text: str) -> str:
        """Translate text to English."""
        pass

    @abstractmethod
    def convert_year(self, year_str: str) -> str:
        """Convert year format."""
        pass


class ImageURLPattern(ABC):
    """Interface for parsing and generating image URLs."""
    
    @abstractmethod
    def extract_url_info(self, raw_url: str):
        """Extract pattern information from URL."""
        pass

    @abstractmethod
    def build_image_urls(
        self, suffix: str, start_index: int, base_url: str, page_count: int
    ) -> list[str]:
        """Build list of image URLs from pattern info."""
        pass


class DocumentRetriever(ABC):
    """Interface for retrieving and constructing documents."""
    
    @abstractmethod
    def construct_document(self, node: DOMNode, instance: Instance, schema_queries) -> Path:
        """Construct document from node and instance data."""
        pass