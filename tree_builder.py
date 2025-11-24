from node import DOMNode
from selenium.webdriver.common.by import By
from dotenv import load_dotenv
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from my_queue import Queue

from test_functions import log
import os

class TreeBuilder:
    def __init__(self, driver, url, schema):
        self.driver = driver
        self.url = url
        self.schema = schema
        self.root_node = None # this is just the root node without its children it will be used for querying during scraping : its most important feature is the web_element that will be attached later


        self.template_instance_pair = {
            "exam_variant": 0,
            "subject_li": 0
        } # this doesn't mean anything, it just used to help tracking repeated items, and deal with inconsistencies

    
    def setup_driver(self, headless: bool= True) -> webdriver.Chrome:
        load_dotenv()
        # chromedriver_path = os.getenv("CHROMEDRIVER_PATH")
        options = Options()
        if headless:
            options.add_argument("--headless")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")

        # service = Service(chromedriver_path)
        driver = webdriver.Chrome( options=options) #service=service,
        return driver


    def safe_get(self):
        self.driver.get(self.url)
    
    # this will be harcoded for this example
    def build_tree(self,schema,index=0,parent_node=None,template_name=None, web_element=None):
        #schema is a json text
        """
        pseudo code:

        if repeat detected:
            get template name
            get template count if not obvious through get_dynamic_count(parentnode) but how to access the parent node? 
            get the template schema
            children=[]
            for i in range(count):
                children.append.build_tree(template_schema,index = index +1 ) #index is for the st{index} so write a checker for the attrbs
            return children
        
            handle normal node
            create node: if index in attrbs["id"] : replace the placeholder with the actual index
            if node.description == "root"
                self.root_node = node
            populate its children recursively:
                    loop: for child_schema in schema.children:
                        node.children.extend(build_tree(child_schema,index,parentnode=node))
            
        return node
            
        issues:
        root node isn't initialized for 33 times but im sure i initialized it; fixed
        index number isn't correctly incremented it goes from 1 to 8 then it restarts with each repeat block; gonna hardcord it
            every template should have a counter like how many node instances of thattemplate have been built fixed

        st1 to st8 and st9 to st33 should be nephew/uncle relationship, currently it is sibling relationship fixed


        - the sub_template isn't repeated correctly, it isn't even placed it only keeps showing 3; which is weird:
            so it should be tighted with the sti here where the landmarking algorithm works
            like in repeated elements you look for css selector, it will fetch the first one it encounters, that's why it keeps returning 3

        - the dom_tree starts tweaking at the end, fix it (fixed)

        - include two phase approach; i'm currently combining the tree building and annotation phase together, which is not correct make it very slow 
            and repeated tasks


        
        - make the sti adaptable to sti changes;
        
        - annotation issues: the subject_li gets annotated before sti , why? because the sti hasn't finished building, that's why it annotates the subject_li before it
            how to fix it?

            apply annotation directly after defining sti, not waiting for it to populate its children
        
            okay now the sti gets annotated befor the li, but still the same issuse the get closest landmark
            The first two sti has two Li's but all the other has 3 with is weird af
        - trying to understand the root cause of subject_li irregularities:
        analyzing the terminal:
        08:43:43.603] this is the node that we will start going up from: with id: st1 class: ['test'] tag: div
        08:43:43.660] this is the node that we will start going up from: with id: None class: ['gkzt-xueke', 'mtT_30', 'clearfix'] tag: div
        > fixed! the top two logs are fixed, they aren't linked to the problem, just a logging issue
        3
        10:18:37.454] {'repeat': {'template': 'subject_li', 'count': 'auto'}}
        10:18:37.454] this is the node that we will start going up from: with id: None class: ['gkzt-xueke', 'mtT_30', 'clearfix'] tag: div
        10:18:37.455] this is going up one level to find the landmark node, these are the parent's characteristics: id: None with class:['gkzt-xueke', 'mtT_30', 'clearfix'] with the tag:div with web_element:None
        10:18:37.564] this is the node that we will start going up from: with id: None class: [] tag: li
        10:18:37.566] this is going up one level to find the landmark node, these are the parent's characteristics: id: None with class:[] with the tag:li with web_element:None
        10:18:37.611] this is the node that we will start going up from: with id: None class: [] tag: li
        10:18:37.611] this is going up one level to find the landmark node, these are the parent's characteristics: id: None with class:[] with the tag:li with web_element:None
        > instead of it going up it goes down which not what we want; so there's issue in parent-child relationshi

        these callings and all of that bullshit should be like this :
        this is the node that we will start going up from: with id: None class: ['gkzt-xueke', 'mtT_30', 'clearfix'] tag: div
        this is the node that we will start going up from: with id: st1 class: ['test'] tag: div

        li should never be called at this point, it shouldnt even exist! if it exists, there's issue in the landmarking logic and get dynamic count

        the tag li is a parent of another node that's getting called repeatedly

        fixed:
        the issue is that i call the get the closest landmark for multiple times

        new error: case error: there are duplicates for the <a> tag and the <div> only for the st33 which is weird
            how to identify the error:
                is it from the console or from the code? write testing functions using the final nodeDom tree:
                1st function: see only one branch of the nodetree
                    take input the dom tree; you want  to print a specific DESCENDENT tree branch from a node inside the tree(meaning you get that node and only its descendents/ no siblings ); so you have a pipeline of two functions:
                    first function is you take a dom tree and extract the node that you need but based on what? a DFS and put into it all the attributes/classes but there are a lot of elements that have the same attributes and classes; what should we do? they are duplicates , but they come from different branches, they have different predecessor and that's how you define them
        the probllem turned out to be from the console not from my logic

        next step is annotate the desired elements:
            in the JSON you add to elements that you're going to interact with an attribute; "interaction" that's a bool true or false; if it's true the treebuilder will automatically annotate that element, and we're be able to interact with it either click on a link, download an image if it's <img> tag, get the <span> text, or get the fonts
            using the closest landmark algo.
            to not lose my progress, upload this on github; and then create a branch; if it works just fine; merge it (done)
            i need to remove the hard encoding:
            when looping check the annotate attribute, if it's true, mark it as annotate: true

            now after annotating we treat one case meaning one examl then we build a looping mechanism / multiu threading/processing mechanism
            foa what is the fastest/easiest/ solid proof way to fetch an exam?
            each page in the caroussel has an image link that generally follow a specific pattern: base url + indexing
            if we are sure of the base url; we just loop through the indexing and finish in seconds
            how to be sure of the base url?
            
            a few issues in the exams:
                sometimes the same exam gets repeated accross multiple exams and exam variants; meaning it is not normal and most likely non the official exam:
                    for each year: we keep track of all the links that we visited; if a specific link has been visited more than one time under different subject/exam variant
                    we flag it,then we continue to the next example 
                the exam solution is in the same document as the exam
                    this will happen in the multithreading and multi processing;
                    here's how to identify the error: 
                        THE SOLUTION link wil have the original exam+ solution but starts on the solution page; the same file is shareed between the solution and the exam but each one has a different starting point
                        enter solution link, send warning to the exam link that the exam ends on page10 even though there are 13 pages
                        this will help us later on on ML training keep the data clean
                duplicates in the exam 

            fix the tag annotation 

        now experiment with clicking on a tag
            get the specified link node
            then get its web element and click() on it, 

        a bug: 
            only the sti with the number of subjects= 3 aren't logging right
            how to solve:
                only pass indexing for template == exam variant
                  

        to do list:
            - set up exam scrapper class
            - use the json buildtree function to build the exam page tree
            - work on the exam page links generation algo
                generate the base link
                test the links?? the images aren't in caroussel so going to each page is very time consuming, just trust it
                some exams gets repeated this is the case for the 2025 exams, how to handle it? keep a global link tracker, if it surpasses 2 flag it, every exam should have a seperate link
            - create an mvp database just for testing
            - save to database
            - optimize  tree_builder:
                - cache the landmark, keep a stack, where there's always the root_node, instead of calling get the closest landmark, get the top of the stack, and queue it everytime you add annotation
                    if you move to the next branch (next st{index}) clear it and only keep the root_node
                - instead of finding elements one by one like in the <a> tag, use a context object, fetch all needed elements one time and store them in a context object then distribute them during the building
                - too many if conditions, use seperate functions to deal with them, but this will hurt the scalability
                -  checking if idx in (2, 4) on every iteration, too many unnecessary calls
                - Separate Schema Preprocessing
                    Do this once at initialization:
                    Parse which nodes need annotation (annotate: true)
                    Identify all repeat blocks and their configs
                    Build a "build plan" that guides tree construction
                    No need to check schema repeatedly during building
                - template configuration: which elements to skip/ indexing
                - build a build_tree plan, no need to refetch the schema everytime
            - work on re annotation algo
            
            






        """
        
        
        if "repeat" in schema:
            template_name = schema["repeat"]["template"]
            template_count = schema["repeat"]["count"]
            try:
                if template_count == "auto":
                    #log(schema)
                    template_count = self.get_dynamic_count(parent_node)
                    #log(template_count)
                #log(f"Template: {template_name}, Expected count: {template_count}")

            except Exception as e:
                print(f"this dynamic block is trippin{e}")
            
            template_schema= self.schema["templates"][template_name]
            children = []

            if template_name == "subject_li":
                
                closest_landmark = self.get_closest_landmark(parent_node)
                subjects_web_elements = closest_landmark.web_element.find_elements(By.TAG_NAME,"li")
                q= Queue()
                for subj_web_element in subjects_web_elements:
                    q.enqueue(subj_web_element)
                    #print(subj_web_element.text)


            for iteration in range(template_count):
                # increment index
                if template_name == "exam_variant":
                    self.template_instance_pair[template_name] += 1
                    idx = self.template_instance_pair[template_name]
                    #print(idx)
                    #log(f"Iteration {idx}/{template_count}: exam_variant_idx={idx}, template={template_name}")
                 #indexing only matters for  exam_variant not subject_li so this is an optimization i need to work on later
                # skip 2 and 4 entirely, this is inconsistency in the html page, the html skips st2 and st4 for some reasons, but i have to adapt
                
                    if idx in (2, 4):
                        continue

                    template_node = self.build_tree(schema=template_schema, index=idx, template_name=template_name,parent_node= parent_node)

                    #log(f"Iteration {iteration + 1}/{template_count}: exam_variant_idx={self.template_instance_pair["exam_variant"]}, template={template_name}")

                elif template_name == "subject_li":
                    template_node = self.build_tree(schema=template_schema, template_name=template_name,parent_node= parent_node, web_element= q.front())
                    q.dequeue()

                else:
                    template_node = self.build_tree(schema=template_schema, template_name=template_name,parent_node= parent_node)
                



                # build only for valid indexes
                children.append(
                    template_node
                )
                #log(f"Added child. Total children now: {len(children)}")

                # annotate each template node here: get the closest landmark
                """
                if template_node.web_element is None:
                    closest_landmark = self.get_closest_landmark(template_node)
                    selector = template_node.get_css_selector()

                    template_node.web_element = closest_landmark.web_element.find_element(
                        By.CSS_SELECTOR, 
                        selector
                    )
                    #print("this node has been annotated with id:", node.attrs["id"] if "id" in node.attrs else None,"class:", node.classes, "tag",node.tag,"and closest landmark is:",closest_landmark.attrs["id"] if "id" in closest_landmark.attrs else None)
                """
            #log(f"Final children count for {template_name}: {len(children)}")

            return children
        
        if "attrs" in schema and template_name == "exam_variant":
            _attrs = {
                    k: (v.format(index=index) if k == "id" and "{index}" in v else v)
                    for k, v in schema["attrs"].items()
                }
            #print(_attrs)
        else:
            _attrs = {}

        print(f"Type of schema: {type(schema)}")
        print(f"Value of schema: {schema}")
        _classes = schema.get("classes",[])
        #error hger

        node = DOMNode(
            tag = schema.get("tag",""),
            classes= _classes,
            attrs=_attrs,
            description = schema.get("description", ""),
            template_name=template_name
        )
        node.parent = parent_node


        if self.root_node is None:
            self.root_node = node
            print("root node has been set")
        if node.description == "root":
                self.annotate_root()

        #if "id" in node.attrs and node.attrs["id"].startswith("st") and node.attrs["id"][2:].isdigit() and node.web_element is None:
        if "annotate" in schema and node.description != "root":
            closest_landmark = self.get_closest_landmark(node)
            links = closest_landmark.web_element.find_elements(By.TAG_NAME, "a")
            if node.tag == 'a':
                """
                links_web_elements = closest_landmark.web_element.find_elements(By.TAG_NAME,"a")
                q=Queue()
                for link_web_element in links_web_elements:
                    q.enqueue(link_web_element)
                log(f"a tags queue length {q.size}")
                """
                if node.description == 'Link to the exam paper.':
                    # <a> with <font> containing "真题"
                    #selector = "//a[font[text()='真题']]"
                    #node.web_element = closest_landmark.web_element.find_element(By.XPATH, selector)
                    for link in links:
                        if link.text=="真题":
                            node.web_element=link
                elif node.description == "Link to the solution.":
                    # <a> with <font> containing "答案"
                    #selector = "//a[font[text()='']]"
                    #node.web_element = closest_landmark.web_element.find_element(By.XPATH, selector)
                    for link in links:
                        if link.text=="答案":
                            node.web_element=link
                else:
                    # Other <a> tags, fallback to CSS selector
                    selector = node.get_css_selector()
                    node.web_element = closest_landmark.web_element.find_element(By.CSS_SELECTOR, selector)
                # i need to make a case for li on how to select the right one
                # i can get the parent of all of <li> web_elements put them in a stack and assign everyone/ ill do it with a list first
                #find_element always return the first encounter, so that's wrong, it should be stored somewhere then get accessed to
                """
                 a — classes: [] — webElement: <selenium.webdriver.remote.webelement.WebElement (session="83141f35f2ad77da017226a8c5dce3b6", element="f.380949D28557B81A4B639539260DD52D.d.E215AA505EF606390B5320FA9CD5F4E5.e.29")>
            a — classes: [] — webElement: <selenium.webdriver.remote.webelement.WebElement (session="83141f35f2ad77da017226a8c5dce3b6", element="f.380949D28557B81A4B639539260DD52D.d.E215AA505EF606390B5320FA9CD5F4E5.e.30")>
                
                """
                """
                this concerns the subject_li pattern;
                    every sti got a subject_li template let's say we have 3 subject_li
                    subject_li template detected:
                        get all <li> elements
                        put them in a stack in an ordered way
                        enter the subject_li template loop:
                            pop first element
                            pass it into the build_tree
                            now in the build_tree 
                """
            elif node.tag =="li" and web_element is not None:
                node.web_element = web_element

            else:
                # Non-<a> nodes, use CSS selector
                selector = node.get_css_selector()
                node.web_element = closest_landmark.web_element.find_element(By.CSS_SELECTOR, selector)

            # Optional debug print
            # print(
            #     f"Node annotated with id: {node.attrs.get('id')} | class: {node.classes} | "
            #     f"tag: {node.tag} | closest landmark: {closest_landmark} | "
            #     f"web_element: {node.web_element}"
            # )

        if "children" in schema:
            for child_schema in schema["children"]:
                
                result = self.build_tree(child_schema,parent_node=node) # can't use extend here we always need to call the add_child function

                if isinstance(result,list):
                    for child in result:
                        node.add_child(child) #only at the end the parent_child relationship is established
                else:
                    node.add_child(result)

        return node


    def get_dynamic_count(self, node):
        """Find count of repeated children dynamically."""
        if self.root_node.web_element is None:
            self.annotate_root()
        
        if not node.web_element:
            closest_landmark = self.get_closest_landmark(node)
            
            try:
                selector = node.get_css_selector()
                node.web_element = closest_landmark.web_element.find_element(
                    By.CSS_SELECTOR, 
                    selector
                )
            except Exception as e:
                print('eroooooooooooooor', e)
                return 0
        
        child_elements = node.web_element.find_elements(By.XPATH, "./*")
        return len(child_elements)


    def get_closest_landmark(self, node):
        """Walk up tree to find nearest ancestor with web_element."""
        # this is harcoded af: 
        if self.root_node.web_element is None:
            self.annotate_root()
            return self.root_node
        
        current = node
        #log(f'this is the node that we will start going up from: with id: {node.attrs.get("id")} class: {node.classes} tag: {node.tag}')
        #log(f'this node\'s parent is with id: {node.parent.attrs.get("id")} class: {node.parent.classes} tag: {node.parent.tag}')

        
        while current:
            #log(f'this is going up one level to find the landmark node, these are the parent\'s characteristics: id: {current.attrs["id"] if "id" in current.attrs else None} with class:{current.classes} with the tag:{current.tag} with web_element:{current.web_element}')
            if current.web_element:

                return current
            current = current.parent
        return self.root_node

            
    def annotate_root(self):
        """Find and attach the root web element."""
        try:
            if self.root_node:
                selector_value = self.root_node.get_css_selector()
                self.driver.get(self.url)
                wait = WebDriverWait(self.driver, 5)
                self.root_node.web_element = wait.until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, selector_value))
                )

        except Exception as e:
            print(f"failed to annotate root: {e}")

    #this is hardcoded for now, but later we can make it dynamic based on the templates and selectory types/values;
    #here we have a fallback func and a bit of try/except for debugging


    def find_in_tree(self, selector_type=None, selector_value=None):
        """
        Recursively searches the entire tree (starting from root_node)
        for a node matching the selector.
        
        Args:
            selector_type (str): 'id', 'class', 'tag', 'attr', or 'css'
            selector_value (str): The value to match.
        
        Returns:
            DOMNode or None: The first matching node, or None if not found.

        this is made mostly for testing
        """
        if not hasattr(self, "root_node") or self.root_node is None:
            raise Exception("Root node not initialized. Please build the tree first.")
        
        root = self.root_node

        def matches(node):
            if not selector_type or not selector_value:
                return False

            if selector_type == "id":
                return node.attrs.get("id") == selector_value

            elif selector_type == "class":
                return selector_value in node.classes

            elif selector_type == "tag":
                return node.tag == selector_value

            elif selector_type == "attr":
                if "=" in selector_value:
                    key, val = selector_value.split("=", 1)
                    return node.attrs.get(key) == val
                return selector_value in node.attrs

            elif selector_type == "css":
                # Compare full CSS selector from node.get_css_selector()
                try:
                    node_selector = node.get_css_selector()
                    return node_selector == selector_value
                except Exception:
                    return False

            return False

        # Depth-first search starting from the root node
        stack = [root]
        while stack:
            current = stack.pop()
            if matches(current):
                return current
            stack.extend(reversed(current.children))

        return None


    



    def find_nodes_by_template(self, template_name):

        result = []

        def _traverse(node):
            if node.template_name == template_name:
                result.append(node)
            for child in node.children:
                _traverse(child)

        _traverse(self.root_node)
        return result
        
       

    def build_and_annotate(self):
        """Main pipeline to run everything."""

        # self.safe_get()
        self.build_tree(self.schema)
        
        #for key in templates:
          #  self.annotate_template_web_elements(key)

        return self.root_node






# parent that has multiple children; that's where we put the web_element + looped branches like the st {i} 
        
        
            