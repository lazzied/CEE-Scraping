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

    
    def _handle_attributes(self,schema,index, template_name):
        if "attrs" in schema :
            if template_name == "exam_variant":
                _attrs = {
                        k: (v.format(index=index) if k == "id" and "{index}" in v else v)
                        for k, v in schema["attrs"].items()
                    }
                return _attrs
            else:
                return schema.get("attrs",{})

    
    def _create_node(self,schema,index,parent_node,template_name):

        _attrs = self._handle_attributes(schema, index, template_name)

        node = DOMNode(
            tag = schema.get("tag",""),
            classes=  schema.get("classes",[]),
            attrs=_attrs,
            description = schema.get("description", ""),
            template_name=template_name
        )

        node.parent = parent_node

        if self.root_node is None:
            self.root_node = node
            print("root node has been set")

        return node
    
    def _annotate_node(self,node,web_element):
        closest_landmark = self.get_closest_landmark(node)
        links = closest_landmark.web_element.find_elements(By.TAG_NAME, "a")
        if node.tag == 'a':
        
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
            
        elif node.tag =="li" and web_element is not None:
            node.web_element = web_element

        else:
            # Non-<a> nodes, use CSS selector
            selector = node.get_css_selector()
            node.web_element = closest_landmark.web_element.find_element(By.CSS_SELECTOR, selector)

    # this will be harcoded for this example
    def build_tree(self,schema,index=0,parent_node=None,template_name=None, web_element=None):

        if "repeat" in schema:
            return self.handle_repeat(schema, parent_node)
        
        node = self._create_node(schema, index,parent_node, template_name)

        if "annotate" in schema and node.description != "root":
            self._annotate_node(node,web_element)

        if "children" in schema:
            for child_schema in schema["children"]:
                
                result = self.build_tree(child_schema,parent_node=node) # can't use extend here we always need to call the add_child function

                if isinstance(result,list):
                    for child in result:
                        node.add_child(child) #only at the end the parent_child relationship is established
                else:
                    node.add_child(result)

        return node

    def handle_repeat(self, schema, parent_node):
        """
        Handle repeated template elements.
        
        Args:
            schema: Schema containing repeat configuration
            parent_node: Parent node for the repeated elements
        
        Returns:
            list: List of child nodes created from the template
        """
        template_name = schema["repeat"]["template"]
        template_count = schema["repeat"]["count"]
        
        try:
            if template_count == "auto":
                template_count = self.get_dynamic_count(parent_node)
        except Exception as e:
            print(f"this dynamic block is trippin{e}")
        
        template_schema = self.schema["templates"][template_name]
        children = []

        # Special handling for subject_li template
        if template_name == "subject_li":
            closest_landmark = self.get_closest_landmark(parent_node)
            subjects_web_elements = closest_landmark.web_element.find_elements(By.TAG_NAME, "li")
            q = Queue()
            for subj_web_element in subjects_web_elements:
                q.enqueue(subj_web_element)

        # Build template instances
        for iteration in range(template_count):
            # Handle exam_variant template
            if template_name == "exam_variant":
                self.template_instance_pair[template_name] += 1
                idx = self.template_instance_pair[template_name]
                
                # Skip 2 and 4 (HTML page inconsistency)
                if idx in (2, 4):
                    continue

                template_node = self.build_tree(
                    schema=template_schema, 
                    index=idx, 
                    template_name=template_name,
                    parent_node=parent_node
                )

            # Handle subject_li template
            elif template_name == "subject_li":
                template_node = self.build_tree(
                    schema=template_schema, 
                    template_name=template_name,
                    parent_node=parent_node, 
                    web_element=q.front()
                )
                q.dequeue()

            # Handle other templates
            else:
                template_node = self.build_tree(
                    schema=template_schema, 
                    template_name=template_name,
                    parent_node=parent_node
                )

            children.append(template_node)

        return children

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
            """

            
            """
        except Exception as e:
            print(f"failed to annotate root: {e}")

    #this is hardcoded for now, but later we can make it dynamic based on the templates and selectory types/values;
    #here we have a fallback func and a bit of try/except for debugging
    
    def build_and_annotate(self):
        """Main pipeline to run everything."""
        # self.safe_get()
        self.build_tree(self.schema)
        #for key in templates:
          #  self.annotate_template_web_elements(key)

        return self.root_node

# parent that has multiple children; that's where we put the web_element + looped branches like the st {i} 
    
    def tree_builder_orchestrator(self):
        self.annotate_root()
        
            