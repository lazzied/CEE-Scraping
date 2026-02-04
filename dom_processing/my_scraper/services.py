"""
Service classes for path management, downloading, and PDF conversion.
"""

import os
import random
from pathlib import Path
from typing import List, Dict

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from PIL import Image

from models import InstanceMetadata, Instance
from interfaces import ContentTransformer


class OutputPath:
    """Service for building and creating output paths."""
    
    def build(self, metadata: InstanceMetadata) -> Path:
        """Build output path from metadata."""
        root = Path(os.getenv("SAVE_PATH", "./downloads"))
        return root / f"{metadata.year}_{metadata.exam_variant}_{metadata.subject}"

    def ensure(self, path: Path) -> None:
        """Ensure path exists, creating if necessary."""
        path.mkdir(parents=True, exist_ok=True)


class MetadataProcessing(OutputPath):
    """Service for processing and transforming metadata."""
    
    def process_metadata(
        self,
        instance: Instance,
        content_transformer: ContentTransformer
    ) -> dict:
        """Process instance metadata with optional transformation."""
        processed_metadata = {}

        if instance.scraping_config.need_year_conversion:
            year = content_transformer.convert_year(instance.year)
        else:
            year = instance.metadata.year

        processed_metadata["year"] = year

        if instance.scraping_config.need_translation:
            exam_variant = content_transformer.translate_to_english(instance.metadata.exam_variant)
            subject = content_transformer.translate_to_english(instance.metadata.subject)
        else:
            exam_variant = instance.metadata.exam_variant
            subject = instance.metadata.subject

        processed_metadata["exam_variant"] = exam_variant
        processed_metadata["subject"] = subject

        return processed_metadata


class PageDownloader:
    """Service for downloading document pages from URLs."""
    
    def download_document_pages(
        self,
        save_path: Path,
        page_urls: List[str],
        metadata: Dict[str, str],
        state: str,
    ) -> None:
        """Download all document pages with retry and proxy rotation."""
        os.makedirs(save_path, exist_ok=True)

        session = self._create_session_with_retry()
        proxies_pool = self._get_proxy_pool()
        user_agents = self._get_user_agent_pool()

        for index, url in enumerate(page_urls, start=1):
            self._download_single_page(
                index=index,
                url=url,
                session=session,
                proxies_pool=proxies_pool,
                user_agents=user_agents,
                save_path=save_path,
                metadata=metadata,
                state=state,
            )

        session.close()

    def _create_session_with_retry(self) -> requests.Session:
        """Create HTTP session with retry strategy."""
        session = requests.Session()

        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET"],
            raise_on_status=False,
        )

        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)

        return session

    def _get_proxy_pool(self) -> List[str]:
        """Get list of proxy URLs."""
        return [
            "http://fdkvhhhe:42jcljcpj8e6@142.111.48.253:7030",
            "http://fdkvhhhe:42jcljcpj8e6@31.59.20.176:6754",
            "http://fdkvhhhe:42jcljcpj8e6@23.95.150.145:6114",
            "http://fdkvhhhe:42jcljcpj8e6@198.23.239.134:6540",
            "http://fdkvhhhe:42jcljcpj8e6@107.172.163.27:6543",
        ]

    def _get_user_agent_pool(self) -> List[str]:
        """Get list of user agent strings."""
        return [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/122.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 Version/15.1 Safari/605.1.15",
            "Mozilla/5.0 (Linux; Android 10) AppleWebKit/537.36 Chrome/119.0.0.0 Mobile Safari/537.36",
        ]

    def _download_single_page(
        self,
        *,
        index: int,
        url: str,
        session: requests.Session,
        proxies_pool: List[str],
        user_agents: List[str],
        save_path: Path,
        metadata: Dict[str, str],
        state: str,
    ) -> None:
        """Download a single page with error handling."""
        proxy_url = random.choice(proxies_pool)
        proxies = {"http": proxy_url, "https": proxy_url}

        headers = {
            "User-Agent": random.choice(user_agents),
            "Accept": "*/*",
            "Referer": url,
        }

        try:
            response = session.get(
                url,
                headers=headers,
                proxies=proxies,
                timeout=5,
            )
            response.raise_for_status()

            content_type = response.headers.get("Content-Type", "").lower()

            if "pdf" in content_type or url.lower().endswith(".pdf"):
                ext = "pdf"
            else:
                ext = "jpg"

            filename = self._get_page_filename(index, metadata, state, ext)
            file_save_path = os.path.join(save_path, filename)

            with open(file_save_path, "wb") as f:
                f.write(response.content)

        except Exception:
            filename = self._get_page_filename(index, metadata, state, "jpg")
            file_save_path = os.path.join(save_path, filename)
            self._save_blank_a4(file_save_path)

    def _get_page_filename(
        self,
        index: int,
        metadata: Dict[str, str],
        state: str,
        extension: str,
    ) -> str:
        """Generate filename for a page."""
        return (
            f"{metadata['year']}_"
            f"{metadata['exam_variant']}_"
            f"{metadata['subject']}_"
            f"{state}_"
            f"{index}.{extension}"
        )

    def _save_blank_a4(self, path: str) -> None:
        """Save blank A4 page as fallback."""
        img = Image.new("RGB", (2480, 3508), "white")
        img.save(path, "JPEG", quality=95)


class PDFConverter:
    """Service for converting images to PDF."""
    
    def convert_document_pdf(self, save_path: str) -> None:
        """Convert all images in path to single PDF."""
        image_files = self._get_sorted_image_files(save_path)
        if not image_files:
            return
        
        images = self._load_images(save_path, image_files)
        stem = image_files[0].rsplit("_", 1)[0]
        self._save_as_pdf(save_path, images, stem)
        self._delete_images(save_path, image_files)

    def _get_sorted_image_files(self, save_path: str) -> List[str]:
        """Get sorted list of image files."""
        image_files = [
            f for f in os.listdir(save_path)
            if f.lower().endswith(".jpg")
        ]

        def extract_index(filename: str) -> int:
            return int(filename.rsplit("_", 1)[-1].split(".")[0])

        image_files.sort(key=extract_index)
        return image_files

    def _load_images(
        self,
        save_path: str,
        image_files: List[str]
    ) -> List[Image.Image]:
        """Load and convert images to RGB."""
        images = []
        for file in image_files:
            img_path = os.path.join(save_path, file)
            img = Image.open(img_path)
            if img.mode != "RGB":
                img = img.convert("RGB")
            images.append(img)
        return images

    def _save_as_pdf(
        self,
        save_path: str,
        images: List[Image.Image],
        stem: str
    ) -> str:
        """Save images as single PDF."""
        pdf_filename = f"{stem}.pdf"
        pdf_path = os.path.join(save_path, pdf_filename)
        images[0].save(pdf_path, save_all=True, append_images=images[1:])
        return pdf_path

    def _delete_images(
        self,
        save_path: str,
        image_files: List[str]
    ) -> None:
        """Delete image files after PDF creation."""
        for file in image_files:
            os.remove(os.path.join(save_path, file))