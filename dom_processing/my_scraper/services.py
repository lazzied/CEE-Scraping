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
from .models import InstanceMetadata, Instance
from .interfaces import ContentTransformer
import os
from pathlib import Path

class OutputPath:
    """Service for building and creating output paths."""

    def build(self, metadata: dict, state) -> Path:
        """Build output path from metadata. Supports exam_variant as a list."""

        if not isinstance(metadata, dict):
            raise TypeError(f"metadata must be a dict, got {type(metadata).__name__}")
        
        if state not in ["exam", "solution"]:
            raise ValueError(f"Invalid state '{state}': must be 'exam' or 'solution'")
        
        required_keys = ["year", "exam_variant", "subject"]
        missing_keys = [key for key in required_keys if key not in metadata]
        if missing_keys:
            raise KeyError(f"Missing required metadata keys: {missing_keys}. Available keys: {list(metadata.keys())}")
        
        year = metadata["year"]
        exam_variant = metadata["exam_variant"]
        subject = metadata["subject"]
        
        if not year:
            raise ValueError("metadata['year'] cannot be empty")
        if not subject:
            raise ValueError("metadata['subject'] cannot be empty")
        
        # Handle exam_variant as a list
        if isinstance(exam_variant, list):
            exam_variant_str = "_".join(str(v) for v in exam_variant if v) or "unknown"
        else:
            exam_variant_str = str(exam_variant) if exam_variant else "unknown"

        try:
            root = Path(os.getenv("SAVE_PATH", "./downloads"))
            # Safe filename: replace spaces with underscores
            safe_subject = str(subject).replace(" ", "_")
            return root / f"{year}_{exam_variant_str}_{safe_subject}_{state}"
        except Exception as e:
            raise RuntimeError(
                f"Failed to build path for year={year}, exam_variant={exam_variant}, "
                f"subject={subject}, state={state}: {type(e).__name__}: {e}"
            )

    def ensure(self, path: Path) -> None:
        """Ensure path exists, creating if necessary."""
        if not path:
            raise ValueError("path cannot be None")
        
        if not isinstance(path, Path):
            raise TypeError(f"path must be a Path object, got {type(path).__name__}")
        
        try:
            path.mkdir(parents=True, exist_ok=True)
        except PermissionError:
            raise PermissionError(f"Permission denied when creating directory: {path}")
        except Exception as e:
            raise RuntimeError(f"Failed to create directory '{path}': {type(e).__name__}: {e}")


class MetadataProcessing:
    """Service for processing and transforming metadata."""

    
    def __init__(self):
        try:
            self.output_path = OutputPath()  # Composition instead of inheritance
        except Exception as e:
            raise RuntimeError(f"Failed to initialize MetadataProcessing: {type(e).__name__}: {e}")

    
    def build(self, metadata: dict, state) -> Path:
        """Delegate to OutputPath."""
        if not metadata:
            raise ValueError("metadata cannot be None")
        if state not in ["exam", "solution"]:
            raise ValueError(f"Invalid state '{state}': must be 'exam' or 'solution'")
        
        try:
            return self.output_path.build(metadata, state)
        except Exception as e:
            raise RuntimeError(f"Failed to build path (state={state}): {e}")
    
    def ensure(self, path: Path) -> None:
        """Delegate to OutputPath."""
        if not path:
            raise ValueError("path cannot be None")
        
        try:
            self.output_path.ensure(path)
        except Exception as e:
            raise RuntimeError(f"Failed to ensure path '{path}': {e}")
        
class MetadataProcessing:
    """Service for processing and transforming metadata."""

    
    def __init__(self):
        try:
            self.output_path = OutputPath()  # Composition instead of inheritance
        except Exception as e:
            raise RuntimeError(f"Failed to initialize MetadataProcessing: {type(e).__name__}: {e}")

    
    def build(self, metadata: dict, state) -> Path:
        """Delegate to OutputPath."""
        if not metadata:
            raise ValueError("metadata cannot be None")
        if state not in ["exam", "solution"]:
            raise ValueError(f"Invalid state '{state}': must be 'exam' or 'solution'")
        
        try:
            return self.output_path.build(metadata, state)
        except Exception as e:
            raise RuntimeError(f"Failed to build path (state={state}): {e}")
    
    def ensure(self, path: Path) -> None:
        """Delegate to OutputPath."""
        if not path:
            raise ValueError("path cannot be None")
        
        try:
            self.output_path.ensure(path)
        except Exception as e:
            raise RuntimeError(f"Failed to ensure path '{path}': {e}")
    
    def process_metadata(
        self,
        instance: Instance,
        content_transformer: ContentTransformer,
        content_transformation_config,
    ) -> dict:
        """Process instance metadata with optional transformation. Supports exam_variant as a list."""
        
        if not instance:
            raise ValueError("instance cannot be None")
        if not content_transformer:
            raise ValueError("content_transformer cannot be None")
        if not content_transformation_config:
            raise ValueError("content_transformation_config cannot be None")
        
        if not isinstance(content_transformation_config, dict):
            raise TypeError(f"content_transformation_config must be a dict, got {type(content_transformation_config).__name__}")
        
        if "need_year_conversion" not in content_transformation_config:
            raise KeyError("content_transformation_config missing 'need_year_conversion' key")
        if "need_translation" not in content_transformation_config:
            raise KeyError("content_transformation_config missing 'need_translation' key")
        
        if not hasattr(instance, 'metadata'):
            raise AttributeError(f"Instance missing 'metadata' attribute. Instance type: {type(instance).__name__}")
        
        metadata = instance.metadata
        
        if not hasattr(metadata, 'year'):
            raise AttributeError(f"Instance metadata missing 'year' attribute. Metadata type: {type(metadata).__name__}")
        if not hasattr(metadata, 'exam_variant'):
            raise AttributeError(f"Instance metadata missing 'exam_variant' attribute. Metadata type: {type(metadata).__name__}")
        if not hasattr(metadata, 'subject'):
            raise AttributeError(f"Instance metadata missing 'subject' attribute. Metadata type: {type(metadata).__name__}")
        
        processed_metadata = {}

        # Process year
        if content_transformation_config["need_year_conversion"]:
            if not hasattr(content_transformer, 'convert_year'):
                raise AttributeError(
                    f"content_transformer missing 'convert_year' method. "
                    f"Transformer type: {type(content_transformer).__name__}"
                )
            try:
                year = content_transformer.convert_year(metadata.year)
            except Exception as e:
                raise RuntimeError(f"Failed to convert year '{metadata.year}': {type(e).__name__}: {e}")
        else:
            year = metadata.year
        processed_metadata["year"] = year

        # Process exam_variant (as list) and subject
        if content_transformation_config["need_translation"]:
            if not hasattr(content_transformer, 'translate_to_english'):
                raise AttributeError(
                    f"content_transformer missing 'translate_to_english' method. "
                    f"Transformer type: {type(content_transformer).__name__}"
                )
            
            # exam_variant can be a list
            exam_variant_list = []
            if isinstance(metadata.exam_variant, list):
                for variant in metadata.exam_variant:
                    try:
                        translated = content_transformer.translate_to_english(variant)
                        exam_variant_list.append(translated)
                    except Exception as e:
                        print(f"Warning: Failed to translate exam_variant '{variant}': {e}")
                        exam_variant_list.append(variant)
            else:
                # fallback if it's not a list
                try:
                    exam_variant_list.append(content_transformer.translate_to_english(metadata.exam_variant))
                except Exception as e:
                    print(f"Warning: Failed to translate exam_variant '{metadata.exam_variant}': {e}")
                    exam_variant_list.append(metadata.exam_variant)
            
            # Process subject
            try:
                subject = content_transformer.translate_to_english(metadata.subject)
            except Exception as e:
                print(f"Warning: Failed to translate subject '{metadata.subject}': {e}")
                subject = metadata.subject
        else:
            exam_variant_list = metadata.exam_variant if isinstance(metadata.exam_variant, list) else [metadata.exam_variant]
            subject = metadata.subject

        processed_metadata["exam_variant"] = exam_variant_list
        processed_metadata["subject"] = subject

        return processed_metadata


import time

class PageDownloader:
    """Service for downloading document pages from URLs."""
    
    def download_document_pages(
    self,
    save_path: Path,
    page_urls: List[str],
    metadata: Dict[str, str],
    state: str,
) -> None:
        """Download all document pages with retry and polite delays."""
        if not save_path:
            raise ValueError("save_path cannot be None")
        if not isinstance(page_urls, list):
            raise TypeError(f"page_urls must be a list, got {type(page_urls).__name__}")
        if not page_urls:
            raise ValueError("page_urls list cannot be empty")
        if not isinstance(metadata, dict):
            raise TypeError(f"metadata must be a dict, got {type(metadata).__name__}")
        if state not in ["exam", "solution"]:
            raise ValueError(f"Invalid state '{state}': must be 'exam' or 'solution'")
        
        print(f"DEBUG: Starting download for state={state}, {len(page_urls)} pages")
        print(f"DEBUG: Save path: {save_path}")
        print(f"DEBUG: First URL: {page_urls[0] if page_urls else 'None'}")
        
        try:
            os.makedirs(save_path, exist_ok=True)
        except PermissionError:
            raise PermissionError(f"Permission denied when creating directory: {save_path}")
        except Exception as e:
            raise RuntimeError(f"Failed to create save directory '{save_path}': {type(e).__name__}: {e}")

        try:
            session = self._create_session_with_retry()
        except Exception as e:
            raise RuntimeError(f"Failed to create HTTP session: {type(e).__name__}: {e}")
        
        try:
            user_agents = self._get_user_agent_pool()
        except Exception as e:
            raise RuntimeError(f"Failed to initialize user-agent pool: {type(e).__name__}: {e}")

        for index, url in enumerate(page_urls, start=1):
            if not url:
                print(f"Warning: Empty URL at index {index}, skipping")
                continue
            
            if not isinstance(url, str):
                print(f"Warning: URL at index {index} is not a string (got {type(url).__name__}), skipping")
                continue
            
            try:
                print(f"DEBUG: Downloading page {index}/{len(page_urls)} from {url}")
                self.download_single_page(
                    index=index,
                    url=url,
                    session=session,
                    user_agents=user_agents,
                    save_path=save_path,
                    metadata=metadata,
                    state=state,
                )
                print(f"DEBUG: Successfully downloaded page {index}/{len(page_urls)}")
                
                # Add polite delay between requests (except after last page)
                if index < len(page_urls):
                    time.sleep(0.1)
                    
            except Exception as e:
                print(f"Warning: Failed to download page {index}/{len(page_urls)} from {url}: {type(e).__name__}: {e}")
                continue

        try:
            session.close()
        except Exception as e:
            print(f"Warning: Failed to close HTTP session: {e}")
        
        print(f"DEBUG: Finished downloading {len(page_urls)} pages for state={state}")

    def _create_session_with_retry(self) -> requests.Session:
        """Create HTTP session with retry strategy."""
        try:
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
        except Exception as e:
            raise RuntimeError(f"Failed to create session with retry strategy: {type(e).__name__}: {e}")

    def _get_user_agent_pool(self) -> List[str]:
        """Get list of user agent strings."""
        return [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/122.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 Version/15.1 Safari/605.1.15",
            "Mozilla/5.0 (Linux; Android 10) AppleWebKit/537.36 Chrome/119.0.0.0 Mobile Safari/537.36",
        ]

    def download_single_page(
        self,
        *,
        index: int, #for file name
        url: str, #download url
        session: requests.Session, # extra
        user_agents: List[str], #extra
        save_path: Path,
        metadata: Dict[str, str],
        state: str,
    ) -> None:
        """Download a single page with error handling."""
        if not isinstance(index, int) or index < 1:
            raise ValueError(f"index must be a positive integer, got {index}")
        if not url:
            raise ValueError("url cannot be empty")
        if not session:
            raise ValueError("session cannot be None")
        if not user_agents:
            raise ValueError("user_agents cannot be empty")
        
        try:
            headers = {
                "User-Agent": random.choice(user_agents),
                "Accept": "image/png,image/*,*/*",
                "Accept-Encoding": "gzip, deflate, br",
                "Accept-Language": "en-US,en;q=0.9",
                "Referer": "https://gaokao.eol.cn/",
                "Connection": "keep-alive",
            }

            response = session.get(
                url,
                headers=headers,
                timeout=10,
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

        except requests.exceptions.Timeout:
            print(f"Warning: Timeout downloading page {index} from {url}, saving blank page")
            filename = self._get_page_filename(index, metadata, state, "jpg")
            file_save_path = os.path.join(save_path, filename)
            try:
                self._save_blank_a4(file_save_path)
            except Exception as blank_error:
                print(f"Error: Failed to save blank page for index {index}: {blank_error}")
                raise
        except requests.exceptions.RequestException as e:
            print(f"Warning: Request failed for page {index} from {url}: {type(e).__name__}: {e}, saving blank page")
            filename = self._get_page_filename(index, metadata, state, "jpg")
            file_save_path = os.path.join(save_path, filename)
            try:
                self._save_blank_a4(file_save_path)
            except Exception as blank_error:
                print(f"Error: Failed to save blank page for index {index}: {blank_error}")
                raise
        except Exception as e:
            print(f"Warning: Unexpected error downloading page {index} from {url}: {type(e).__name__}: {e}, saving blank page")
            filename = self._get_page_filename(index, metadata, state, "jpg")
            file_save_path = os.path.join(save_path, filename)
            try:
                self._save_blank_a4(file_save_path)
            except Exception as blank_error:
                print(f"Error: Failed to save blank page for index {index}: {blank_error}")
                raise

    def _get_page_filename(
        self,
        index: int,
        metadata: Dict[str, str],
        state: str,
        extension: str,
    ) -> str:
        """Generate filename for a page."""
        if not isinstance(index, int) or index < 1:
            raise ValueError(f"index must be a positive integer, got {index}")
        if not isinstance(metadata, dict):
            raise TypeError(f"metadata must be a dict, got {type(metadata).__name__}")
        
        required_keys = ["year", "exam_variant", "subject"]
        missing_keys = [key for key in required_keys if key not in metadata]
        if missing_keys:
            raise KeyError(f"Missing required metadata keys for filename: {missing_keys}")
        
        if state not in ["exam", "solution"]:
            raise ValueError(f"Invalid state '{state}': must be 'exam' or 'solution'")
        if not extension:
            raise ValueError("extension cannot be empty")
        
        try:
            return (
                f"{metadata['year']}_"
                f"{metadata['exam_variant']}_"
                f"{metadata['subject']}_"
                f"{state}_"
                f"{index}.{extension}"
            )
        except Exception as e:
            raise RuntimeError(
                f"Failed to generate filename for index {index}, state {state}: {type(e).__name__}: {e}"
            )

    def _save_blank_a4(self, path: str) -> None:
        """Save blank A4 page as fallback."""
        if not path:
            raise ValueError("path cannot be empty")
        
        try:
            img = Image.new("RGB", (2480, 3508), "white")
            img.save(path, "JPEG", quality=95)
        except Exception as e:
            raise RuntimeError(f"Failed to save blank A4 image to '{path}': {type(e).__name__}: {e}")

class PDFConverter:
    """Service for converting images to PDF."""
    
    def convert_document_pdf(self, save_path: str) -> None:
        """Convert all images in path to single PDF."""
        if not save_path:
            raise ValueError("save_path cannot be empty")
        
        if not os.path.exists(save_path):
            raise FileNotFoundError(f"Save path does not exist: {save_path}")
        
        if not os.path.isdir(save_path):
            raise ValueError(f"Save path is not a directory: {save_path}")
        
        try:
            image_files = self._get_sorted_image_files(save_path)
        except Exception as e:
            raise RuntimeError(f"Failed to get sorted image files from '{save_path}': {e}")
        
        if not image_files:
            print(f"Warning: No image files found in '{save_path}', skipping PDF conversion")
            return
        
        try:
            images = self._load_images(save_path, image_files)
        except Exception as e:
            raise RuntimeError(f"Failed to load images from '{save_path}': {e}")
        
        if not images:
            raise ValueError(f"No images loaded from '{save_path}'")
        
        try:
            stem = image_files[0].rsplit("_", 1)[0]
        except Exception as e:
            raise RuntimeError(f"Failed to extract stem from filename '{image_files[0]}': {type(e).__name__}: {e}")
        
        if not stem:
            raise ValueError(f"Empty stem extracted from filename '{image_files[0]}'")
        
        try:
            self._save_as_pdf(save_path, images, stem)
        except Exception as e:
            raise RuntimeError(f"Failed to save PDF to '{save_path}': {e}")
        
        try:
            self._delete_images(save_path, image_files)
        except Exception as e:
            print(f"Warning: Failed to delete image files from '{save_path}': {e}")

    def _get_sorted_image_files(self, save_path: str) -> List[str]:
        """Get sorted list of image files."""
        if not save_path:
            raise ValueError("save_path cannot be empty")
        
        try:
            all_files = os.listdir(save_path)
        except PermissionError:
            raise PermissionError(f"Permission denied when listing directory: {save_path}")
        except Exception as e:
            raise RuntimeError(f"Failed to list directory '{save_path}': {type(e).__name__}: {e}")
        
        image_files = [
            f for f in all_files
            if f.lower().endswith(".jpg")
        ]

        def extract_index(filename: str) -> int:
            try:
                return int(filename.rsplit("_", 1)[-1].split(".")[0])
            except (ValueError, IndexError) as e:
                raise ValueError(f"Failed to extract index from filename '{filename}': {e}")

        try:
            image_files.sort(key=extract_index)
        except Exception as e:
            raise RuntimeError(f"Failed to sort image files: {e}")
        
        return image_files

    def _load_images(
        self,
        save_path: str,
        image_files: List[str]
    ) -> List[Image.Image]:
        """Load and convert images to RGB."""
        if not save_path:
            raise ValueError("save_path cannot be empty")
        if not isinstance(image_files, list):
            raise TypeError(f"image_files must be a list, got {type(image_files).__name__}")
        
        images = []
        for i, file in enumerate(image_files):
            img_path = os.path.join(save_path, file)
            
            try:
                img = Image.open(img_path)
            except FileNotFoundError:
                raise FileNotFoundError(f"Image file not found: {img_path}")
            except Exception as e:
                raise RuntimeError(f"Failed to open image '{img_path}': {type(e).__name__}: {e}")
            
            try:
                if img.mode != "RGB":
                    img = img.convert("RGB")
            except Exception as e:
                print(f"Warning: Failed to convert image {i+1}/{len(image_files)} '{file}' to RGB: {e}")
                try:
                    img.close()
                except:
                    pass
                continue
            
            images.append(img)
        
        return images

    def _save_as_pdf(
            self,
            save_path: str,
            images: List[Image.Image],
            stem: str
        ) -> str:
            """Save images as single PDF."""
            if not save_path:
                raise ValueError("save_path cannot be empty")
            if not isinstance(images, list):
                raise TypeError(f"images must be a list, got {type(images).__name__}")
            if not images:
                raise ValueError("images list cannot be empty")
            if not stem:
                raise ValueError("stem cannot be empty")
            
            try:
                pdf_filename = f"{stem}.pdf"
                pdf_path = os.path.join(save_path, pdf_filename)
                
                # Handle duplicate filenames
                if os.path.exists(pdf_path):
                    index = 1
                    while True:
                        pdf_filename = f"{stem}_{index}.pdf"
                        pdf_path = os.path.join(save_path, pdf_filename)
                        if not os.path.exists(pdf_path):
                            break
                        index += 1
                
                images[0].save(pdf_path, save_all=True, append_images=images[1:])
                
                return pdf_path
            except PermissionError:
                raise PermissionError(f"Permission denied when saving PDF to: {save_path}")
            except Exception as e:
                raise RuntimeError(
                    f"Failed to save PDF '{pdf_filename}' to '{save_path}': "
                    f"{type(e).__name__}: {e}"
                )

    def _delete_images(
        self,
        save_path: str,
        image_files: List[str]
    ) -> None:
        """Delete image files after PDF creation."""
        if not save_path:
            raise ValueError("save_path cannot be empty")
        if not isinstance(image_files, list):
            raise TypeError(f"image_files must be a list, got {type(image_files).__name__}")
        
        for i, file in enumerate(image_files):
            file_path = os.path.join(save_path, file)
            try:
                os.remove(file_path)
            except FileNotFoundError:
                print(f"Warning: Image file {i+1}/{len(image_files)} already deleted or not found: {file_path}")
            except PermissionError:
                print(f"Warning: Permission denied when deleting image {i+1}/{len(image_files)}: {file_path}")
            except Exception as e:
                print(f"Warning: Failed to delete image {i+1}/{len(image_files)} '{file}': {type(e).__name__}: {e}")