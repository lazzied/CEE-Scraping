"""
workflow:
each year: contains two 3 paages: the main page, the exam page and the solution page

the exam and solution page have pratically the same format, so basically we need to build two dom trees: one for the main page, one for the exam/solution page and each has their own variation/inconsistencies
i should have an error detection when the DOM structure changes, so that i can update the blueprints accordingly

checked: also the number of subjects can vary, so the json blueprint must be dynamic enough to handle that : so when you encounter the count="auto" you look for the number of children available in the actual page and build accordingly
we need to cache the blueprints for each page structure, so that we can reuse them when needed

scraping steps:
first we will test the sequential way, we'll explore parallelization later if needed
1. load main page
2. build dom tree for main page based on blueprint
3. for each examType in examTypeContainer:
    - locate container for examType
    - extract type_text and year
    - get subject elements
    - for each subject element:
        - extract subject name
        - build dom tree for subject based on blueprint
        - for each exam variant in subject:
            - extract exam variant info
            - navigate to exam page
            - build dom tree for exam page based on blueprint
            - scrape exam data
            - navigate to solution page
            - build dom tree for solution page based on blueprint
            - scrape solution data
            - store data in database
locating is easy, they are predetermined by the node descriptions/ tag/ id/ classes etc... in the json blueprint, so we just need to find the it collect the infos and move on to the next node

for annotation, we use the shortest path to a landmark; we don't always use the root_node's node to find the web element, sometimes we use a parent node as the base to find child nodes, this is more efficient and less error-prone
also we don't need to compare all the landmarks, like the sti range from 1 to 33, they are all landmarks, we compare parents/ grandparents/ cousins/uncles etc... then we compare the distance to the target node, this way we can find the target node more accurately
"""

import re
import requests
import os
from PIL import Image
from test_functions import get_logger
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from typing import Union

from my_dataclasses import Exam, Solution,DocumentLink

class Scraper:
    # the dom node tree should it be built inside the scraper or be passed on already built?
    # i need to create another class, the orchestrator, that handles the navigation and data sending between pages 
    # also i need to study the possibility building the first st1 then scrape the data there, go back to main page, build the second st2 and so on... will it boost performance? this is building a plan, for each context
    #for now the data will be built inside the scraper class!!!
    
    def __init__(self,driver,root,state:str,output_folder, ExamSol:Union[Exam,Solution]=None,): 
        # uppercase to differentiate between the dataclass and other type of classes
        self.root_node = root
        self.base_url = None
        self.page_links= None
        self.state= state
        self.driver = driver
        #state is either "exam" or "solution"

        self.raw_url= None # this is url of the first page
        self.metadata = None
        self.output_folder  = output_folder
        
        self.logger = get_logger(__name__)
        self.logger.disabled = False

        self.ExamSol=ExamSol
        
        
    def set_metadata(self):
        metadata_node = self.root_node.find_in_node("class", "title")
        metadata_node_text = metadata_node.web_element.text
        def parse_title(title: str) -> dict:
            # Example format: "2025年高考全国一卷英语试题"
            
            # Extract year (before "年")
            year = title.split("年")[0]

            # Extract exam variant (between "高考" and subject)
            variant_part = title.split("高考")[1]
            
            # subject is before "试题"
            subject = variant_part.split("试题")[0]
            
            # exam variant = everything except the subject at the end
            exam_variant = subject[:-2]  # remove the last two characters
            
            # subject = last two characters (like "英语")
            subject = subject[-2:]
            
            return {
                "year": year,
                "exam_variant": exam_variant,
                "subject": subject
            }
        
        page_count = int(self.get_page_count())
        exam_data = parse_title(metadata_node_text)
        exam_data["page_count"]=page_count

        self.metadata = exam_data

    def get_metadata(self):
        return self.metadata
    
    
    def get_document_links_dataclass(self):
        page_count = self.get_page_count()
        document_links = []

        page_count = int(page_count)

        
        self.logger.info(f"Creating document links: page_count={page_count}, links_available={len(self.page_links)}")
        
        if not self.page_links:
            self.logger.error("No page_links available!")
            return []
        
        for i, subj_link in zip(range(1, page_count + 1), self.page_links):
            document_link = DocumentLink(
                document_state=self.ExamSol.__class__.__name__,
                page_number=i,
                link=subj_link,
            )
            document_links.append(document_link)
            self.logger.info(f"Created link #{i}: {subj_link[:50]}...")
        
        self.logger.info(f"Total document links created: {len(document_links)}")
        return document_links
    
    def set_examsol_values(self):
        """Populate Exam or Solution dataclass with scraped metadata"""
        
        # Set document links for both Exam and Solution
        self.ExamSol.downloaded_links = self.get_document_links_dataclass()
        
        if isinstance(self.ExamSol, Exam):
            # Exam-specific fields
            self.ExamSol.year = self.metadata["year"]
            self.ExamSol.exam_variant = self.metadata["exam_variant"]
            self.ExamSol.subject = self.metadata["subject"]
            self.ExamSol.exam_url = self.raw_url
            self.logger.info(f"Set Exam metadata: {self.ExamSol.subject}")
            
        elif isinstance(self.ExamSol, Solution):
            # Solution-specific fields
            self.ExamSol.solution_url = self.raw_url
            self.logger.info(f"Set Solution metadata")

    def set_base_link(self):
        img_link_node = self.root_node.find_in_node("tag", "img")

        self.logger.info(img_link_node.web_element.get_attribute("outerHTML"))
        
        if img_link_node.web_element.get_attribute("alt"):
            self.logger.info(img_link_node.web_element.get_attribute("alt"))
        else:
            self.logger.info("cound't find the alt attribute")
        
        if not img_link_node:
            self.logger.error(f"[ERROR] Could not find <img> node in tree for {self.state}")
            self.base_url = None
            self.raw_url = None
            return
        
        if not img_link_node.web_element:
            self.logger.error(f"[ERROR] <img> node exists but has no web_element for {self.state}")
            self.base_url = None
            self.raw_url = None
            return
        
        link = img_link_node.web_element.get_attribute("src")
        
        if not link:
            self.logger.error(f"[ERROR] <img> has no 'src' attribute for {self.state}")
            self.base_url = None
            self.raw_url = None
            return
        
        self.logger.info(f"[DEBUG] Found image URL: {link[:100]}")
        
        # Check if it's a data URI
        if link.startswith("data:"):
            self.logger.error(f"[ERROR] Got base64 data URI instead of URL for {self.state}")
            self.base_url = None
            self.raw_url = link
            return
        
        def get_base_link(url: str) -> str:
            return url.rsplit("/", 1)[0] + "/"
        
        self.base_url = get_base_link(link)
        self.raw_url = link
        self.logger.info(f"[DEBUG] Base URL: {self.base_url}")

    
    def generate_image_links(self):
        # Check if we have a valid base_url
        if not self.base_url or self.raw_url.startswith("data:"):
            self.logger.error(f"[ERROR] Cannot generate links - invalid URL for {self.state}")
            self.page_links = []
            return
        
        links = []
        self.logger.info(f"[DEBUG] Base URL: {self.base_url}")
        
        def extract_suffix(url: str) -> tuple[str, str]:
            filename = url.split("/")[-1]
            name = filename.split(".")[0]
            
            self.logger.info(f"[DEBUG] Extracting from filename: {filename}, name: {name}")

            match = re.match(r"([a-zA-Z]+)(\d+)", name)
            if match:
                letters = match.group(1)
                number = match.group(2)
                self.logger.info(f"[DEBUG] Matched - letters: {letters}, number: {number}")
                return letters, number
            
            self.logger.warning(f"[WARNING] No match for pattern in: {name}")
            return "", ""

        suffix, starting_index = extract_suffix(self.raw_url)
        
        if not suffix or not starting_index:
            self.logger.error(f"[ERROR] Failed to extract suffix/index from: {self.raw_url}")
            # Try alternate approach - maybe URL format is different
            self.page_links = []
            return
        
        self.logger.info(f"[DEBUG] Suffix: {suffix}, Starting index: {starting_index}")
        
        starting_index = int(starting_index)
        
        for i in range(starting_index, self.metadata["page_count"] + 1):
            suffix_num = f"{i:02d}"
            links.append(f"{self.base_url}{suffix}{suffix_num}.png")

        self.page_links = links
        self.logger.info(f"[DEBUG] Generated {len(links)} image links")

    # this is made for validation and testing
    def get_page_count(self):
        return self.driver.execute_script("return _PAGE_COUNT;")


        
    
    def download_document_pages(self):
        """
        Download all images in self.list and save them with the naming convention:
        {year}_{exam_variant}_{subject}_{state} in the specified folder.
        
        :param save_folder: Folder to save the images
        :param state: State string to include in the filename
        """
        # Ensure the folder exists
        os.makedirs(self.output_folder, exist_ok=True)

        # Setup session with retry logic
        session = requests.Session()
        retry_strategy = Retry(
            total=3,  # Total number of retries
            backoff_factor=1,  # Wait 1, 2, 4 seconds between retries
            status_forcelist=[429, 500, 502, 503, 504],  # Retry on these HTTP status codes
            raise_on_status=False
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)

        year = self.metadata.get("year")
        exam_variant = self.metadata.get("exam_variant")
        subject = self.metadata.get("subject")

        index = 1
        for link in self.page_links:
            # Construct the filename
            filename = f"{year}_{exam_variant}_{subject}_{self.state}_{index}.jpg"
            save_path = os.path.join(self.output_folder, filename)

            try:
                # Download the image with timeout
                response = session.get(link, timeout=15)  # 15 second timeout
                response.raise_for_status()  # Raises exception for 4xx/5xx status codes
                
                # Save the image
                with open(save_path, "wb") as f:
                    f.write(response.content)
                self.logger.info(f"Image saved to {save_path}")
                index += 1
                
            except requests.exceptions.Timeout:
                self.logger.error(f"Timeout downloading image from {link}")
            except requests.exceptions.ConnectionError as e:
                self.logger.error(f"Connection error downloading {link}: {e}")
            except requests.exceptions.HTTPError as e:
                self.logger.error(f"HTTP error downloading {link}: {e}")
            except requests.exceptions.RequestException as e:
                self.logger.error(f"Error downloading image from {link}: {e}")
            except Exception as e:
                self.logger.error(f"Unexpected error saving {link}: {e}")
        
        session.close()
    
    def convert_document_pdf(self):
        """
        Convert all images in the folder to a single PDF.
        Images must follow the format: {year}_{exam_variant}_{subject}_{state}_{index}.jpg
        The PDF pages will be sorted by the 'index'.
        After successfully creating the PDF, the images will be deleted.
        """
        # Get all jpg files
        image_files = [f for f in os.listdir(self.output_folder) if f.lower().endswith(".jpg")]

        if not image_files:
            self.logger.warning("No images found in folder.")
            return

        # Sort by index extracted from filename
        def extract_index(filename):
            return int(filename.rsplit("_", 1)[-1].split(".")[0])

        image_files.sort(key=extract_index)

        # Load images
        images = []
        for file in image_files:
            img_path = os.path.join(self.output_folder, file)
            img = Image.open(img_path)
            if img.mode != 'RGB':
                img = img.convert('RGB')  # Convert to RGB for PDF
            images.append(img)

        # Create PDF filename from the first image's metadata
        # Extract: year_exam_variant_subject_state from first filename
        first_file = image_files[0]
        base_name = "_".join(first_file.rsplit("_", 1)[0].split("_"))  # Remove index part
        pdf_filename = f"{base_name}.pdf"
        pdf_path = os.path.join(self.output_folder, pdf_filename)

        # Save all images as a single PDF
        images[0].save(pdf_path, save_all=True, append_images=images[1:])
        self.logger.info(f"PDF saved at {pdf_path}")

        # Delete all the images
        for file in image_files:
            os.remove(os.path.join(self.output_folder, file))
        self.logger.info(f"All images deleted from {self.output_folder}")

    
    def validation():
        #validate: 
            # page_count == len(links)

        return
    
    #note for optimization
        #the exam scraper tree follow the same structure only thing that changes is is the annotation; so here we can use the build tree then annotate method;
        # there isn't get dynamic count or repeated templates; so yeah
        # i might create html random builder for testing most possible edge cases and inconsistencies 
    
    def scraper_orchestrator(self):
        """
        Orchestrate the complete scraping workflow:
        1. Build page tree
        2. Extract metadata
        3. Get base link
        4. Get page count
        5. Generate image links
        6. Validate data
        7. Download images
        8. Convert to PDF
        
        Returns True if successful, False otherwise
        """
        try: 
            # 1. Extract metadata
            self.set_metadata()
            if not self.metadata:
                self.logger.error("Error: Failed to extract metadata")
                return False
            
            # 2. Get base link
            self.set_base_link()
            if not self.base_url:
                self.logger.error("Error: Failed to get base URL")
                return False
            
            # 3. Generate image links
            self.generate_image_links()
            if not self.page_links:
                self.logger.error("Error: Failed to generate image links")
                return False
            
            # 4. Download images
            self.download_document_pages()
            
            # 5. Convert to PDF
            self.convert_document_pdf()
            
            self.logger.info(f"Completed: {self.metadata.get('year')} {self.metadata.get('exam_variant')} {self.metadata.get('subject')} [{self.state}] - {self.metadata['page_count']} pages")
            
            # 6. set the dataclass values (all data is ready)
            self.set_examsol_values()
            
            self.logger.info(f"Dataclass populated: year={self.ExamSol.year}, subject={getattr(self.ExamSol, 'subject', 'N/A')}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error: {str(e)}")
            import traceback
            self.logger.error(traceback.format_exc())
            return False