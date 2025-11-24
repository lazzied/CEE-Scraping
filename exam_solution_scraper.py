


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

for annotation, we use the shortest path to a landmark; we don't always use the root's node to find the web element, sometimes we use a parent node as the base to find child nodes, this is more efficient and less error-prone
also we don't need to compare all the landmarks, like the sti range from 1 to 33, they are all landmarks, we compare parents/ grandparents/ cousins/uncles etc... then we compare the distance to the target node, this way we can find the target node more accurately
"""
from tree_builder import TreeBuilder
from node import DOMNode
import re
import requests
import os
from PIL import Image

class Scraper:
    # the dom node tree should it be built inside the scraper or be passed on already built?
    # i need to create another class, the orchestrator, that handles the navigation and data sending between pages 
    # also i need to study the possibility building the first st1 then scrape the data there, go back to main page, build the second st2 and so on... will it boost performance? this is building a plan, for each context
    #for now the data will be built inside the scraper class!!!
    def __init__(self,tree_builder:TreeBuilder,state:str,output_folder ):
        self.tree_builder = tree_builder

        self.root = None
        self.base_url = None
        self.page_links= None
        self.state= state
        #state is either "exam" or "solution"

        self.raw_url= None # this is url of the first page
        self.metadata = None
        self.output_folder  = output_folder
        
        
    
    def build_page_tree(self):
        self.tree_builder.build_and_annotate()
        self.root = self.tree_builder.root_node
    
    def set_metadata(self):
        metadata_node = self.root.find_in_node("class", "title")
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
        
    def set_base_link(self):
        img_link_node = self.root.find_in_node("tag","img")
        link=img_link_node.web_element.get_attribute("src")
        def get_base_link(url: str) -> str:
            return url.rsplit("/", 1)[0] + "/"
        
        self.base_url = get_base_link(link)
        self.raw_url = link

    
    def generate_image_links(self):
        links = []
        print(self.base_url)
        def extract_suffix(url: str) -> str:
            # Extract the filename: e.g. "yy01.png"
            filename = url.split("/")[-1]
            
            # Remove file extension
            name = filename.split(".")[0]  # "yy01"
            
            # Extract the letters before the digits
            match = re.match(r"([a-zA-Z]+)\d+", name)
            if match:
                return match.group(1)
            return ""
        
        suffix = extract_suffix(self.raw_url)
        print("this is the suffix", suffix)

        print(self.metadata)
        for i in range(1, self.metadata["page_count"] + 1):
            suffix_num = f"{i:02d}"   # formats 1 → "01", 9 → "09", 10 → "10"
            links.append(f"{self.base_url}{suffix}{suffix_num}.png")

        self.page_links =  links

    # this is made for validation and testing
    def get_page_count(self):
        return self.tree_builder.driver.execute_script("return _PAGE_COUNT;")


        
    
    def download_document_pages(self):
        """
        Download all images in self.list and save them with the naming convention:
        {year}_{exam_variant}_{subject}_{state} in the specified folder.
        
        :param save_folder: Folder to save the images
        :param state: State string to include in the filename
        """
        # Ensure the folder exists
        os.makedirs(self.output_folder, exist_ok=True)

        year = self.metadata.get("year")
        exam_variant = self.metadata.get("exam_variant")
        subject = self.metadata.get("subject")

        index = 1
        for link in self.page_links:
            # Construct the filename
            filename = f"{year}_{exam_variant}_{subject}_{self.state}_{index}.jpg"
            index+=1
            save_path = os.path.join(self.output_folder, filename)

            # Download the image
            response = requests.get(link)
            if response.status_code == 200:
                with open(save_path, "wb") as f:
                    f.write(response.content)
                print(f"Image saved to {save_path}")
            else:
                print(f"Failed to download image from {link}: {response.status_code}")
    
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
            print("No images found in folder.")
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
        print(f"PDF saved at {pdf_path}")

        # Delete all the images
        for file in image_files:
            os.remove(os.path.join(self.output_folder, file))
        print(f"All images deleted from {self.output_folder}")

    
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
            # Build the DOM tree
            self.build_page_tree()
            if not self.root:
                print("Error: Failed to build page tree")
                return False
            
            # Extract metadata
            self.set_metadata()
            if not self.metadata:
                print("Error: Failed to extract metadata")
                return False
            
            # Get base link
            self.set_base_link()
            if not self.base_url:
                print("Error: Failed to get base URL")
                return False
            

            # Generate image links
            self.generate_image_links()
            if not self.page_links:
                print("Error: Failed to generate image links")
                return False
            """
            # Validate data
            validation_result = self.validation()
            if not validation_result["passed"]:
                print("Error: Validation failed")
                return False
            """

            # Download images
            self.download_document_pages()
            
            # Convert to PDF
            self.convert_document_pdf()
            
            print(f" Completed: {self.metadata.get('year')} {self.metadata.get('exam_variant')} {self.metadata.get('subject')} [{self.state}] - {self.metadata["page_count"]} pages")
            
            return True
            
        except Exception as e:
            print(f" Error: {str(e)}")
            import traceback
            traceback.print_exc()
            return False
        

    
    

