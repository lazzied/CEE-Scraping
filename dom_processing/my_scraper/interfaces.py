"""
Abstract interfaces for the scraping system.
"""

from abc import ABC, abstractmethod
from typing import Any
from pathlib import Path

from dom.node import BaseDOMNode
from .models import Instance


class TextParser(ABC):
    """Interface for parsing text content to extract metadata."""
    
    @abstractmethod
    def get_metadata_value(self, target_node, target_type,driver) -> Any:
        """Extract a single metadata value from text."""
        pass


class ContentTransformer(ABC):
    """Interface for transforming content (translation, conversion)."""
    
    @abstractmethod
    def translate_to_english(self, text: str) -> str:
        """Translate text to English."""
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
    def construct_document(
    self,
    download_node: BaseDOMNode | list[BaseDOMNode],
    root_node: BaseDOMNode,
    instance: Instance,
    state: str,
    ) -> Path:
        pass