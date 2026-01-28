"""
Workflow:
Each year contains two pages: the exam page and the solution page.

The exam and solution pages have practically the same format, so we build two DOM trees:
one for the exam page and one for the solution page, each handling their own variations.

Error detection triggers when DOM structure changes, allowing blueprint updates.

The number of subjects can vary, so blueprints must be dynamic (count="auto" looks for 
actual children in the page and builds accordingly).

Scraping steps (sequential, parallelization explored later):
1. Load main page
2. Build DOM tree for main page based on blueprint
3. For each examType in examTypeContainer:
    - Locate container for examType
    - Extract type_text and year
    - Get subject elements
    - For each subject element:
        - Extract subject name
        - Build DOM tree for subject based on blueprint
        - For each exam variant in subject:
            - Extract exam variant info
            - Navigate to exam page
            - Build DOM tree for exam page based on blueprint
            - Scrape exam data
            - Navigate to solution page
            - Build DOM tree for solution page based on blueprint
            - Scrape solution data
            - Store data in database

For annotation, we use the shortest path to a landmark rather than always using root_node.
We compare parent/grandparent relationships and distance to target nodes for accuracy.
"""

import re
import requests
import os
from PIL import Image
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from typing import Union, Optional
import random

from db.my_dataclasses import Exam, Solution
from dom_processing.english_translation import translate_to_english
from dom_processing.instance_tracker import Tracker


class Scraper:
    
    def __init__(
        self, 
        driver, 
        root, 
        state: str, 
        ExamSol: Union[Exam, Solution] = None, 
        exam_table = None, 
        tracker = None
    ):
        """
        Initialize scraper.
        
        Args:
            driver: Selenium WebDriver instance
            root: Root DOM node
            state: Either "exam" or "solution"
            ExamSol: Exam or Solution dataclass instance
            exam_table: Database table for checking tracker
            tracker: Instance tracker for duplicate detection
        """
        self.root_node = root
        self.driver = driver
        self.state = state
        self.ExamSol = ExamSol
        self.exam_table = exam_table
        self.tracker = tracker
        
        self.base_url = None
        self.raw_url = None
        self.page_links = None
        self.metadata = None
        self.output_folder = None
    
    # ==================== METADATA EXTRACTION ====================
    
    def set_metadata(self) -> None:
        """Extract and parse metadata from page title."""
        metadata_node = self.root_node.find_in_node("class", "title")
        metadata_text = metadata_node.web_element.text
        
        parsed_data = self._parse_title(metadata_text)
        page_count = int(self._get_page_count())
        parsed_data["page_count"] = page_count
        
        self.metadata = parsed_data
    
    def _parse_title(self, title: str) -> dict:
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
        
        return {
            "year": year,
            "exam_variant": exam_variant,
            "subject": subject
        }
    
    def _get_page_count(self) -> int:
        """Get page count from JavaScript variable."""
        return self.driver.execute_script("return _PAGE_COUNT;")
    
    def get_metadata(self) -> dict:
        """Get metadata, setting it first if not already set."""
        if not self.metadata:
            self.set_metadata()
        return self.metadata
    
    # ==================== DATACLASS POPULATION ====================
    
    def set_examsol_values(self) -> None:
        """Populate Exam or Solution dataclass with scraped metadata."""
        if isinstance(self.ExamSol, Exam):
            self.ExamSol.year = self.metadata["year"]
            self.ExamSol.exam_variant = self.metadata["exam_variant"]
            self.ExamSol.subject = self.metadata["subject"]
            self.ExamSol.exam_url = self.raw_url
            
        elif isinstance(self.ExamSol, Solution):
            self.ExamSol.solution_url = self.raw_url
    
    # ==================== URL EXTRACTION ====================
    
    def set_base_link(self) -> None:
        """Extract base URL from first image source."""
        img_node = self.root_node.find_in_node("tag", "img")
        
        if not img_node or not img_node.web_element:
            self.base_url = None
            self.raw_url = None
            return
        
        link = img_node.web_element.get_attribute("src")
        
        if not link:
            self.base_url = None
            self.raw_url = None
            return
        
        if link.startswith("data:"):
            self.base_url = None
            self.raw_url = link
            return
        
        self.base_url = self._get_base_from_url(link)
        self.raw_url = link
    
    def _get_base_from_url(self, url: str) -> str:
        """Extract base URL from full image URL."""
        return url.rsplit("/", 1)[0] + "/"
    
    # ==================== LINK GENERATION ====================
    
    def generate_image_links(self) -> None:
        """Generate all image URLs based on base URL and page count."""
        if not self.base_url or self.raw_url.startswith("data:"):
            self.page_links = []
            return
        
        suffix, starting_index = self._extract_suffix_from_url(self.raw_url)
        
        if not suffix or not starting_index:
            self.page_links = []
            return
        
        self.page_links = self._build_image_urls(suffix, int(starting_index))
    
    def _extract_suffix_from_url(self, url: str) -> tuple[str, str]:
        """
        Extract letter suffix and starting number from URL.
        
        Example: "image_abc01.png" → ("abc", "01")
        
        Args:
            url: Image URL
            
        Returns:
            Tuple of (letter_suffix, starting_number)
        """
        filename = url.split("/")[-1]
        name = filename.split(".")[0]
        
        match = re.match(r"([a-zA-Z]+)(\d+)", name)
        if match:
            return match.group(1), match.group(2)
        
        return "", ""
    
    def _build_image_urls(self, suffix: str, start_index: int) -> list[str]:
        """Build list of image URLs from suffix and starting index."""
        links = []
        for i in range(start_index, self.metadata["page_count"] + 1):
            suffix_num = f"{i:02d}"
            links.append(f"{self.base_url}{suffix}{suffix_num}.png")
        return links
    
    # ==================== FILE OUTPUT ====================
    
    def set_output_folder(self) -> None:
        """Set output folder path based on metadata."""
        parts = [
            "china",
            self.metadata.get("year", "unknown"),
            translate_to_english.get(self.metadata.get("exam_variant", "unknown"), "unknown"),
            translate_to_english.get(self.metadata.get("subject", "unknown"), "unknown")
        ]
        
        root_path = os.getenv("SAVE_PATH", "./downloads/")
        self.output_folder = root_path + "_".join(parts)
    
    def create_output_folder(self) -> None:
        """Create output folder if it doesn't exist."""
        os.makedirs(self.output_folder, exist_ok=True)
    
    # ==================== IMAGE DOWNLOAD ====================
    
    def download_document_pages(self) -> None:
        """Download all document pages as images with retry logic and proxy rotation."""
        os.makedirs(self.output_folder, exist_ok=True)
        
        session = self._create_session_with_retry()
        proxies_pool = self._get_proxy_pool()
        user_agents = self._get_user_agent_pool()
        
        for index, link in enumerate(self.page_links, start=1):
            self._download_single_page(
                index, link, session, proxies_pool, user_agents
            )
        
        session.close()
    
    def _create_session_with_retry(self) -> requests.Session:
        """Create requests session with retry strategy."""
        session = requests.Session()
        
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET"],
            raise_on_status=False
        )
        
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        return session
    
    def _get_proxy_pool(self) -> list[str]:
        """Get list of authenticated proxies."""
        return [
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
    
    def _get_user_agent_pool(self) -> list[str]:
        """Get list of user agents for rotation."""
        return [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/122.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 Version/15.1 Safari/605.1.15",
            "Mozilla/5.0 (Linux; Android 10) AppleWebKit/537.36 Chrome/119.0.0.0 Mobile Safari/537.36",
        ]
    
    def _download_single_page(
        self, 
        index: int, 
        link: str, 
        session: requests.Session,
        proxies_pool: list[str],
        user_agents: list[str]
    ) -> None:
        """Download a single page image."""
        filename = self._get_page_filename(index)
        save_path = os.path.join(self.output_folder, filename)
        
        proxy_url = random.choice(proxies_pool)
        proxies = {"http": proxy_url, "https": proxy_url}
        
        headers = {
            "User-Agent": random.choice(user_agents),
            "Accept": "image/avif,image/webp,image/apng,image/*,*/*;q=0.8",
            "Referer": link
        }
        
        try:
            response = session.get(link, headers=headers, proxies=proxies, timeout=3)
            response.raise_for_status()
            
            with open(save_path, "wb") as f:
                f.write(response.content)
                
        except Exception as e:
            self._save_blank_a4(save_path)
    
    def _get_page_filename(self, index: int) -> str:
        """Generate filename for a page image."""
        return f"{self.metadata['year']}_{self.metadata['exam_variant']}_{self.metadata['subject']}_{self.state}_{index}.jpg"
    
    def _save_blank_a4(self, path: str) -> None:
        """Save a blank A4 page at 300 DPI."""
        img = Image.new("RGB", (2480, 3508), "white")
        img.save(path, "JPEG", quality=95)
    
    # ==================== PDF CONVERSION ====================
    
    def convert_document_pdf(self) -> None:
        """Convert all downloaded images to a single PDF and delete images."""
        image_files = self._get_sorted_image_files()
        
        if not image_files:
            return
        
        images = self._load_images(image_files)
        pdf_path = self._save_as_pdf(images, image_files[0])
        self._delete_images(image_files)
    
    def _get_sorted_image_files(self) -> list[str]:
        """Get all jpg files sorted by index."""
        image_files = [
            f for f in os.listdir(self.output_folder) 
            if f.lower().endswith(".jpg")
        ]
        
        def extract_index(filename: str) -> int:
            return int(filename.rsplit("_", 1)[-1].split(".")[0])
        
        image_files.sort(key=extract_index)
        return image_files
    
    def _load_images(self, image_files: list[str]) -> list[Image.Image]:
        """Load images and convert to RGB if needed."""
        images = []
        for file in image_files:
            img_path = os.path.join(self.output_folder, file)
            img = Image.open(img_path)
            if img.mode != 'RGB':
                img = img.convert('RGB')
            images.append(img)
        return images
    
    def _save_as_pdf(self, images: list[Image.Image], first_filename: str) -> str:
        """Save images as a single PDF."""
        base_name = "_".join(first_filename.rsplit("_", 1)[0].split("_"))
        pdf_filename = f"{base_name}.pdf"
        pdf_path = os.path.join(self.output_folder, pdf_filename)
        
        images[0].save(pdf_path, save_all=True, append_images=images[1:])
        return pdf_path
    
    def _delete_images(self, image_files: list[str]) -> None:
        """Delete all image files."""
        for file in image_files:
            os.remove(os.path.join(self.output_folder, file))
    
    # ==================== DUPLICATE DETECTION ====================
    
    def already_scraped(self) -> bool:
        """Check if this instance has already been scraped."""
        self.set_metadata()
        if not self.metadata:
            return False
        
        return self.tracker.is_instance_scraped()
    
    # ==================== ORCHESTRATION ====================
    
    def scraper_orchestrator(self) -> bool:
        """
        Orchestrate the complete scraping workflow.
        
        Steps:
        1. Extract metadata
        2. Set and create output folder
        3. Get base link
        4. Generate image links
        5. Download images
        6. Convert to PDF
        7. Populate dataclass values
        
        Returns:
            True if successful, False otherwise
        """
        try:
            # Extract metadata
            self.set_metadata()
            if not self.metadata:
                return False
            
            # Setup output folder
            self.set_output_folder()
            self.create_output_folder()
            
            # Get base link
            self.set_base_link()
            if not self.base_url:
                return False
            
            # Generate image links
            self.generate_image_links()
            if not self.page_links:
                return False
            
            # Download and convert
            self.download_document_pages()
            self.convert_document_pdf()
            
            # Populate dataclass
            self.set_examsol_values()
            
            return True
            
        except Exception as e:
            return False