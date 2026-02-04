"""
Web scraper for exam and solution pages.

Extracts metadata, downloads images, converts to PDF, and populates dataclasses.
Designed for extensibility and testing.
"""

import re
import os
from pathlib import Path
from typing import Union, Optional, Dict, List
from dataclasses import dataclass
import random

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from PIL import Image

from db.my_dataclasses import Exam, Solution
from dom_processing.english_translation import translate_to_english


@dataclass
class PageMetadata:
    """Structured page metadata"""
    year: str
    exam_variant: str
    subject: str
    page_count: int


class MetadataExtractor:
    """Extracts and parses page metadata"""
    
    def __init__(self, driver, root_node):
        self.driver = driver
        self.root_node = root_node
    
    def extract(self) -> Optional[PageMetadata]:
        """Extract metadata from page title"""
        metadata_node = self.root_node.find_in_node("class", "title")
        if not metadata_node or not metadata_node.web_element:
            return None
        
        metadata_text = metadata_node.web_element.text
        parsed = self._parse_title(metadata_text)
        page_count = self._get_page_count()
        
        return PageMetadata(
            year=parsed["year"],
            exam_variant=parsed["exam_variant"],
            subject=parsed["subject"],
            page_count=page_count
        )
    
    def _parse_title(self, title: str) -> Dict[str, str]:
        """Parse title: '2025年高考全国一卷英语试题' → {year, variant, subject}"""
        year = title.split("年")[0]
        variant_part = title.split("高考")[1]
        subject_with_suffix = variant_part.split("试题")[0]
        
        return {
            "year": year,
            "exam_variant": subject_with_suffix[:-2],
            "subject": subject_with_suffix[-2:]
        }
    
    def _get_page_count(self) -> int:
        """Get page count from JS variable"""
        return self.driver.execute_script("return _PAGE_COUNT;")


class URLExtractor:
    """Extracts and generates image URLs"""
    
    def __init__(self, root_node):
        self.root_node = root_node
    
    def extract_base_url(self) -> tuple[Optional[str], Optional[str]]:
        """
        Extract base URL and raw URL from first image.
        
        Returns:
            (base_url, raw_url) or (None, None)
        """
        img_node = self.root_node.find_in_node("tag", "img")
        if not img_node or not img_node.web_element:
            return None, None
        
        link = img_node.web_element.get_attribute("src")
        if not link:
            return None, None
        
        # Handle data URLs
        if link.startswith("data:"):
            return None, link
        
        base = link.rsplit("/", 1)[0] + "/"
        return base, link
    
    def generate_image_urls(self, base_url: str, raw_url: str, page_count: int) -> List[str]:
        """Generate all image URLs from base and page count"""
        if not base_url or raw_url.startswith("data:"):
            return []
        
        suffix, start_idx = self._extract_suffix(raw_url)
        if not suffix or not start_idx:
            return []
        
        return [
            f"{base_url}{suffix}{i:02d}.png"
            for i in range(int(start_idx), page_count + 1)
        ]
    
    def _extract_suffix(self, url: str) -> tuple[str, str]:
        """Extract 'abc' and '01' from 'image_abc01.png'"""
        filename = url.split("/")[-1].split(".")[0]
        match = re.match(r"([a-zA-Z]+)(\d+)", filename)
        return (match.group(1), match.group(2)) if match else ("", "")


class ImageDownloader:
    """Downloads images with retry and proxy rotation"""
    
    PROXIES = [
        "http://fdkvhhhe:42jcljcpj8e6@142.111.48.253:7030",
        "http://fdkvhhhe:42jcljcpj8e6@31.59.20.176:6754",
        "http://fdkvhhhe:42jcljcpj8e6@23.95.150.145:6114",
        "http://fdkvhhhe:42jcljcpj8e6@198.23.239.134:6540",
        "http://fdkvhhhe:42jcljcpj8e6@107.172.163.27:6543",
        "http://fdkvhhhe:42jcljcpj8e6@198.105.121.200:6462",
        "http://fdkvhhhe:42jcljcpj8e6@64.137.96.74:6641",
        "http://fdkvhhhe:42jcljcpj8e6@84.247.60.125:6095",
        "http://fdkvhhhe:42jcljcpj8e6@216.10.27.159:6837",
        "http://fdkvhhhe:42jcljcpj8e6@142.111.67.146:5611",
    ]
    
    USER_AGENTS = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/122.0.0.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 Safari/605.1.15",
        "Mozilla/5.0 (Linux; Android 10) AppleWebKit/537.36 Chrome/119.0.0.0 Mobile",
    ]
    
    def download_all(self, urls: List[str], output_dir: Path, filename_template: str):
        """Download all URLs to output directory"""
        output_dir.mkdir(parents=True, exist_ok=True)
        
        session = self._create_session()
        
        for idx, url in enumerate(urls, start=1):
            filename = filename_template.format(index=idx)
            save_path = output_dir / filename
            self._download_single(url, save_path, session)
        
        session.close()
    
    def _create_session(self) -> requests.Session:
        """Create session with retry strategy"""
        session = requests.Session()
        retry = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET"]
        )
        session.mount("http://", HTTPAdapter(max_retries=retry))
        session.mount("https://", HTTPAdapter(max_retries=retry))
        return session
    
    def _download_single(self, url: str, save_path: Path, session: requests.Session):
        """Download single image with proxy rotation"""
        proxy = random.choice(self.PROXIES)
        headers = {
            "User-Agent": random.choice(self.USER_AGENTS),
            "Accept": "image/avif,image/webp,image/apng,image/*,*/*;q=0.8",
            "Referer": url
        }
        
        try:
            response = session.get(
                url,
                headers=headers,
                proxies={"http": proxy, "https": proxy},
                timeout=3
            )
            response.raise_for_status()
            save_path.write_bytes(response.content)
        except Exception:
            # Save blank A4 on failure
            self._save_blank_a4(save_path)
    
    def _save_blank_a4(self, path: Path):
        """Save blank A4 page at 300 DPI"""
        img = Image.new("RGB", (2480, 3508), "white")
        img.save(path, "JPEG", quality=95)


class PDFConverter:
    """Converts images to PDF"""
    
    def convert(self, image_dir: Path, output_name: str):
        """Convert all JPGs in directory to single PDF"""
        image_files = sorted(
            image_dir.glob("*.jpg"),
            key=lambda f: int(f.stem.rsplit("_", 1)[-1])
        )
        
        if not image_files:
            return
        
        images = [self._load_image(f) for f in image_files]
        pdf_path = image_dir / f"{output_name}.pdf"
        
        images[0].save(pdf_path, save_all=True, append_images=images[1:])
        
        # Delete source images
        for img_file in image_files:
            img_file.unlink()
    
    def _load_image(self, path: Path) -> Image.Image:
        """Load image and ensure RGB mode"""
        img = Image.open(path)
        return img.convert('RGB') if img.mode != 'RGB' else img


class Scraper:
    """Main scraper orchestrator"""
    
    def __init__(
        self,
        driver,
        root,
        state: str,
        exam_solution: Union[Exam, Solution] = None,
        tracker = None
    ):
        self.driver = driver
        self.root_node = root
        self.state = state  # "exam" or "solution"
        self.exam_solution = exam_solution
        self.tracker = tracker
        
        # Components
        self.metadata_extractor = MetadataExtractor(driver, root)
        self.url_extractor = URLExtractor(root)
        self.downloader = ImageDownloader()
        self.pdf_converter = PDFConverter()
        
        # State
        self.metadata: Optional[PageMetadata] = None
        self.base_url: Optional[str] = None
        self.raw_url: Optional[str] = None
        self.image_urls: List[str] = []
        self.output_dir: Optional[Path] = None
    
    def run(self) -> bool:
        """
        Execute complete scraping workflow.
        
        Returns:
            True if successful
        """
        try:
            # Extract metadata
            self.metadata = self.metadata_extractor.extract()
            if not self.metadata:
                return False
            
            # Setup output
            self.output_dir = self._get_output_dir()
            
            # Extract URLs
            self.base_url, self.raw_url = self.url_extractor.extract_base_url()
            if not self.base_url:
                return False
            
            # Generate image URLs
            self.image_urls = self.url_extractor.generate_image_urls(
                self.base_url,
                self.raw_url,
                self.metadata.page_count
            )
            if not self.image_urls:
                return False
            
            # Download and convert
            filename_template = self._get_filename_template()
            self.downloader.download_all(
                self.image_urls,
                self.output_dir,
                filename_template
            )
            
            pdf_name = self._get_pdf_name()
            self.pdf_converter.convert(self.output_dir, pdf_name)
            
            # Populate dataclass
            self._populate_dataclass()
            
            return True
            
        except Exception:
            return False
    
    def get_metadata(self) -> Optional[Dict[str, str]]:
        """Get metadata as dict (for backward compatibility)"""
        if not self.metadata:
            self.metadata = self.metadata_extractor.extract()
        
        if not self.metadata:
            return None
        
        return {
            "year": self.metadata.year,
            "exam_variant": self.metadata.exam_variant,
            "subject": self.metadata.subject,
            "page_count": self.metadata.page_count
        }
    
    def _get_output_dir(self) -> Path:
        """Build output directory path"""
        root_path = Path(os.getenv("SAVE_PATH", "./downloads/"))
        
        parts = [
            "china",
            self.metadata.year,
            translate_to_english.get(self.metadata.exam_variant, "unknown"),
            translate_to_english.get(self.metadata.subject, "unknown")
        ]
        
        return root_path / "_".join(parts)
    
    def _get_filename_template(self) -> str:
        """Generate filename template with {index} placeholder"""
        return (
            f"{self.metadata.year}_"
            f"{self.metadata.exam_variant}_"
            f"{self.metadata.subject}_"
            f"{self.state}_{{index}}.jpg"
        )
    
    def _get_pdf_name(self) -> str:
        """Generate PDF filename"""
        return (
            f"{self.metadata.year}_"
            f"{self.metadata.exam_variant}_"
            f"{self.metadata.subject}_"
            f"{self.state}"
        )
    
    def _populate_dataclass(self):
        """Populate Exam or Solution dataclass"""
        if isinstance(self.exam_solution, Exam):
            self.exam_solution.year = self.metadata.year
            self.exam_solution.exam_variant = self.metadata.exam_variant
            self.exam_solution.subject = self.metadata.subject
            self.exam_solution.exam_url = self.raw_url
        elif isinstance(self.exam_solution, Solution):
            self.exam_solution.solution_url = self.raw_url
    
    # Legacy methods for backward compatibility
    def scraper_orchestrator(self) -> bool:
        """Alias for run()"""
        return self.run()