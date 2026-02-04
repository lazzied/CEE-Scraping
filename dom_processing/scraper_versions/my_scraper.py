import re
import os
from pathlib import Path
from typing import Union, Optional, Dict, List, Any
from dataclasses import dataclass
import random

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from PIL import Image

from db.my_dataclasses import Exam, Solution
from dom_processing.english_translation import translate_to_english
from abc import ABC, abstractmethod
from dom.node import DOMNode
from enum import Enum
from pydantic import BaseModel, computed_field


class MetadataTypes(Enum):
    EXAM = "exam"
    SOLUTION = "solution"
    YEAR = "year"
    EXAM_VARIANT = "exam_variant"
    SUBJECT = "subject"


class DocumentContent(Enum):
    EXAM = "exam"
    SOLUTION = "solution"
    BOTH = "exam_and_solution"


@dataclass(frozen=True)
class ScrapingConfig:
    need_translation: bool
    need_year_conversion: bool
    country: str


class InstanceMetadata(BaseModel):
    year: str
    exam_variant: str
    subject: str
    page_count: Optional[int] = None

    model_config = {"validate_assignment": True}


class InstanceDocuments(BaseModel):
    exam_path: Optional[Union[Path, List[Path]]] = None
    solution_path: Optional[Union[Path, List[Path]]] = None


class Instance(BaseModel):
    scraping_config: ScrapingConfig
    metadata: InstanceMetadata
    documents: InstanceDocuments

    @computed_field
    def year(self) -> str:
        return self.metadata.year

    @computed_field
    def exam_variant(self) -> str:
        return self.metadata.exam_variant

    @computed_field
    def subject(self) -> str:
        return self.metadata.subject

    @computed_field
    def page_count(self) -> Optional[int]:
        return self.metadata.page_count

    @computed_field
    def exam_document_path(self) -> Optional[Union[Path, List[Path]]]:
        return self.documents.exam_path

    @computed_field
    def solution_document_path(self) -> Optional[Union[Path, List[Path]]]:
        return self.documents.solution_path


class TextParser(ABC):
    @abstractmethod
    def get_single_metadata_value(self, text: str, metadata_type: str) -> Any:
        pass

    @abstractmethod
    def get_multiple_metadata_values(self, text: str, metadata_types: list) -> dict:
        pass


class ContentTransformer(ABC):
    @abstractmethod
    def translate_to_english(self, text: str) -> str:
        pass

    @abstractmethod
    def convert_year(self, year_str: str) -> str:
        pass


class OutputPath:
    def build(self, metadata: InstanceMetadata) -> Path:
        root = Path(os.getenv("SAVE_PATH", "./downloads"))
        return root / f"{metadata.year}_{metadata.exam_variant}_{metadata.subject}"

    def ensure(self, path: Path) -> None:
        path.mkdir(parents=True, exist_ok=True)


class ImageURLPattern(ABC):
    @abstractmethod
    def extract_url_info(self, raw_url: str):
        pass

    @abstractmethod
    def build_image_urls(
        self, suffix: str, start_index: int, base_url: str, page_count: int
    ) -> list[str]:
        pass


class DocumentRetriever(ABC):
    @abstractmethod
    def construct_document(self, node: DOMNode, instance: Instance, schema_queries) -> Path:
        pass


class MetadataProcessing(OutputPath):
    def process_metadata(
        self,
        instance: Instance,
        content_transformer: ContentTransformer
    ) -> dict:

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


class ChineseImageURLPattern(ImageURLPattern):
    def get_raw_url(self, node: DOMNode) -> str:
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
        return raw_url.rsplit("/", 1)[0] + "/"

    def extract_url_info(self, raw_url: str) -> tuple[str, str]:
        image_name = raw_url.split("/")[-1]
        stem = image_name.split(".")[0]
        match = re.match(r"([a-zA-Z]+)(\d+)", stem)
        if not match:
            raise ValueError("Match not found")
        return match.group(1), match.group(2)

    def build_image_urls(self, suffix: str, start_index: int, base_url: str, page_count: int) -> list[str]:
        urls = []
        for i in range(start_index, page_count + 1):
            suffix_num = f"{i:02d}"
            urls.append(f"{base_url}{suffix}{suffix_num}.png")
        return urls


class DriverOperations:
    def __init__(self, selenium_driver=None):
        self.selenium_driver = selenium_driver


class ChineseDriverOperations(DriverOperations):
    def get_page_count(self) -> int:
        return self.selenium_driver.execute_script("return _PAGE_COUNT;")


class PageDownloader:
    def download_document_pages(
        self,
        save_path: Path,
        page_urls: List[str],
        metadata: Dict[str, str],
        state: str,
    ) -> None:
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
        return [
            "http://fdkvhhhe:42jcljcpj8e6@142.111.48.253:7030",
            "http://fdkvhhhe:42jcljcpj8e6@31.59.20.176:6754",
            "http://fdkvhhhe:42jcljcpj8e6@23.95.150.145:6114",
            "http://fdkvhhhe:42jcljcpj8e6@198.23.239.134:6540",
            "http://fdkvhhhe:42jcljcpj8e6@107.172.163.27:6543",
        ]

    def _get_user_agent_pool(self) -> List[str]:
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
        return (
            f"{metadata['year']}_"
            f"{metadata['exam_variant']}_"
            f"{metadata['subject']}_"
            f"{state}_"
            f"{index}.{extension}"
        )

    def _save_blank_a4(self, path: str) -> None:
        img = Image.new("RGB", (2480, 3508), "white")
        img.save(path, "JPEG", quality=95)


class PDFConverter:
    def convert_document_pdf(self, save_path: str) -> None:
        image_files = self._get_sorted_image_files(save_path)
        if not image_files:
            return
        images = self._load_images(save_path, image_files)
        stem = image_files[0].rsplit("_", 1)[0]
        self._save_as_pdf(save_path, images, stem)
        self._delete_images(save_path, image_files)

    def _get_sorted_image_files(self, save_path: str) -> List[str]:
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
        pdf_filename = f"{stem}.pdf"
        pdf_path = os.path.join(save_path, pdf_filename)
        images[0].save(pdf_path, save_all=True, append_images=images[1:])
        return pdf_path

    def _delete_images(
        self,
        save_path: str,
        image_files: List[str]
    ) -> None:
        for file in image_files:
            os.remove(os.path.join(save_path, file))


class ChineseDocumentRetriever(DocumentRetriever):
    def __init__(self, selenium_driver=None) -> None:
        self.image_patterns = ChineseImageURLPattern()
        self.driver_ops = ChineseDriverOperations(selenium_driver)
        self.metadata_processing = MetadataProcessing()
        self.page_downloader = PageDownloader()
        self.pdf_converter = PDFConverter()

    def get_document_content(self, node: DOMNode, schema_queries) -> str:
        return schema_queries.get_document_content(node.schema_node)

    def construct_document(
        self,
        node: DOMNode,
        instance: Instance,
        schema_queries
    ) -> Path:
        save_path = self.metadata_processing.build(instance.metadata)
        self.metadata_processing.ensure(save_path)

        raw_url = self.image_patterns.get_raw_url(node)
        suffix, start_index = self.image_patterns.extract_url_info(raw_url)
        base_url = self.image_patterns.get_url_base(raw_url)

        page_count = self.driver_ops.get_page_count()
        urls = self.image_patterns.build_image_urls(
            suffix=suffix,
            start_index=int(start_index),
            base_url=base_url,
            page_count=page_count
        )

        document_content = self.get_document_content(node, schema_queries)

        self.page_downloader.download_document_pages(
            save_path=save_path,
            page_urls=urls,
            metadata=instance.metadata.model_dump(),
            state=document_content
        )

        self.pdf_converter.convert_document_pdf(str(save_path))
        return save_path


class InstanceNodeManager:
    def find_target_nodes(self, root_node) -> list:
        stack = [root_node]
        target_nodes = []
        while stack:
            current_node = stack.pop()
            if current_node.metadata:
                target_nodes.append(current_node)
            for child in current_node.children:
                stack.append(child)
        return target_nodes

    def classify_target_nodes(self, target_nodes: list) -> tuple[list, list]:
        instance_documents_target_nodes = []
        for target_node in target_nodes:
            if MetadataTypes.EXAM in target_node.metadata_types or MetadataTypes.SOLUTION in target_node.metadata_types:
                instance_documents_target_nodes.append(target_node)

        instance_metadata_target_nodes = [
            node for node in target_nodes if node not in instance_documents_target_nodes
        ]
        return instance_metadata_target_nodes, instance_documents_target_nodes


class InstanceDataSetter:
    def set_instance_metadata_attributes(self, instance: Instance, nodes: list, text_parser: TextParser) -> None:
        for target_node in nodes:
            text_content = target_node.web_element.text
            filtered_metadata_type = [
                t for t in target_node.metadata_types
                if t not in [MetadataTypes.EXAM, MetadataTypes.SOLUTION]
            ]

            if len(filtered_metadata_type) == 1:
                metadata_type = filtered_metadata_type[0]
                parsed_val = text_parser.get_single_metadata_value(
                    text_content, metadata_type.value
                )
                setattr(instance.metadata, metadata_type.value, parsed_val)
            else:
                parsed_dict = text_parser.get_multiple_metadata_values(
                    text_content, [t.value for t in filtered_metadata_type]
                )
                for key, value in parsed_dict.items():
                    setattr(instance.metadata, key, value)

    def set_instance_documents_attributes(
        self,
        instance: Instance,
        nodes: list,
        document_retriever: DocumentRetriever,
        schema_queries
    ) -> None:
        for target_node in nodes:
            if MetadataTypes.EXAM in target_node.metadata_types:
                exam_path = document_retriever.construct_document(
                    target_node, instance, schema_queries
                )
                instance.documents.exam_path = exam_path
            elif MetadataTypes.SOLUTION in target_node.metadata_types:
                sol_path = document_retriever.construct_document(
                    target_node, instance, schema_queries
                )
                instance.documents.solution_path = sol_path


class InstanceAssembler:
    def __init__(self, text_parser: TextParser, document_retriever: DocumentRetriever, schema_queries):
        self.text_parser = text_parser
        self.document_retriever = document_retriever
        self.schema_queries = schema_queries
        self.node_manager = InstanceNodeManager()
        self.data_setter = InstanceDataSetter()

    def assemble(self, root_node, instance: Instance) -> None:
        all_nodes = self.node_manager.find_target_nodes(root_node)
        meta_nodes, doc_nodes = self.node_manager.classify_target_nodes(all_nodes)

        self.data_setter.set_instance_metadata_attributes(
            instance, meta_nodes, self.text_parser
        )
        self.data_setter.set_instance_documents_attributes(
            instance, doc_nodes, self.document_retriever, self.schema_queries
        )
