from node import DOMNode
from selenium.webdriver.common.by import By
from my_queue import Queue
from my_stack import Stack
from test_functions import get_logger
from my_dataclasses import Exam, Solution
from typing import Union


class TreeBuilder:
    def __init__(self, driver, schema,config=None, arg:Union[Exam,Solution]=None):
        self.driver = driver
        self.schema = schema
        self.root_node = None # this is just the root node without its children it will be used for querying during scraping : its most important feature is the web_element that will be attached later
        self.config = config

        self.document=arg

        self.landmark_cache= Stack()

        self.template_instance_pair = {
            "exam_variant": 0,
        } # this doesn't mean anything, it just used to help tracking repeated items, and deal with inconsistencies, will be replaced with a context object later on probably

        self.logger = get_logger(__name__)
        self.logger.disabled = False
    
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
            
    
    
    def _initialize_root(self):
        root = self._create_node(self.schema)
        self.root_node = root
        self._annotate_root()
        self.landmark_cache.push(self.root_node.web_element)
        #push it to the landmark cache

    
    def _create_node(self,schema,index=None,parent_node=None,template_name=None):
        _attrs = self._handle_attributes(schema, index, template_name)

        node = DOMNode(
            tag = schema.get("tag",""),
            classes=  schema.get("classes",[]),
            attrs=_attrs,
            description = schema.get("description", ""),
            template_name=template_name,
            annotation = schema.get("annotation","")
        )

        node.parent = parent_node

        if self.root_node is None:
            self.root_node = node
            self.logger.info("root node has been set")

        return node
    
    
    def _handle_repeat(self,schema, index=None, parent_node=None, template_name=None):
        template_name = schema["repeat"]["template"]
        template_count = schema["repeat"]["count"]
        template_config = self.config.get(template_name, {}) if self.config else {}
        
        self.logger.info(f"[REPEAT] Template: {template_name}, Count: {template_count}")
        
        try:
            if template_count == "auto":
                template_count = self.get_dynamic_count()
                self.logger.info(f"[REPEAT] Dynamic count resolved to: {template_count}")
        except Exception as e:
            self.logger.error(f"[ERROR] Dynamic count error: {e}")
        
        template_schema = self.schema["templates"][template_name]
        children = []
        
        # Special handling for prefetched elements
        if template_config and template_config.get("prefetch_elements") == "True":
            landmark = self.landmark_cache.top()
            prefetch_tag = template_config.get("prefetch_tag", "li")
            self.logger.info(f"[PREFETCH] Pre-fetching <{prefetch_tag}> elements using landmark: {landmark.get_attribute('class')}")
            
            prefetched_elements = landmark.find_elements(By.TAG_NAME, prefetch_tag)
            
            # Push in reverse so first element is on top
            for el in reversed(prefetched_elements):
                self.landmark_cache.push(el)
            
            self.logger.info(f"[PREFETCH] Pushed {len(prefetched_elements)} <{prefetch_tag}> elements | Cache size: {self.landmark_cache.size()}")
        
        # Build each template instance
        for i in range(1, template_count +1):
            
            if template_config and template_config.get("needs_indexing") == "True":
                self.logger.info("passing in to the first condition")


                self.template_instance_pair[template_name] += 1
                idx = self.template_instance_pair[template_name]
                
                
                self.logger.info(f"[EXAM_VARIANT] Processing variant #{idx}")
                
                skip_indices = template_config.get("skip_indices", [])

                if i in skip_indices:
                    self.logger.info(f"[REPEAT] Skipping index {i} for template {template_name}")
                    continue

                
                # Clean stack back to root before each variant
                cache_size_before = self.landmark_cache.size()

                while self.landmark_cache.size() > 1:
                    self.landmark_cache.pop()
                self.logger.info(f"[EXAM_VARIANT] Cleaned cache from {cache_size_before} to {self.landmark_cache.size()}")
                
                template_node = self._build_tree_layout(
                    schema=template_schema,
                    index=idx,
                    template_name=template_name,
                    parent_node=parent_node
                )


            else:
                self.logger.info("passing in to the second condition")
                template_node = self._build_tree_layout(
                    schema=template_schema,
                    template_name=template_name,
                    parent_node=parent_node
                )
            
            children.append(template_node)
        
        self.logger.info(f"[REPEAT] Built {len(children)} children for template {template_name}")
        return children




    def _build_tree_layout(self, schema, index=None, parent_node=None, template_name=None):
        
        # Handle repeat blocks
        if "repeat" in schema:
            return self._handle_repeat(schema, index, parent_node, template_name)
            
        
        # Create the node (structure only, no web_element yet)
        node = self._create_node(schema, index, parent_node, template_name)
        
        # Check if this template uses prefetching
        is_prefetched = False
        if self.config and node.template_name:
            template_config = self.config.get(node.template_name, {})
            is_prefetched = template_config.get("prefetch_elements") == "True"
        
        # PUSH to cache: Find and cache landmark elements (but DON'T attach to node yet)
        should_cache = (
            "annotation" in schema and 
            schema.get("annotation") == "landmark_element" and 
            node.description != "root" and 
            not is_prefetched  # Don't push if already prefetched
        )
        
        if should_cache:
            landmark = self.landmark_cache.top()
            selector = node.get_css_selector()
            landmark_element = landmark.find_element(By.CSS_SELECTOR, selector)
            self.landmark_cache.push(landmark_element)
            self.logger.info(f"[CACHE PUSH] Pushed landmark for {node.tag}.{'.'.join(node.classes)} | Cache size: {self.landmark_cache.size()}")
        
        # Build children recursively (they use the cached element) this is repeated also in the orchestrator
        if "children" in schema:
            for child_schema in schema["children"]:
                result = self._build_tree_layout(child_schema, parent_node=node)
                
                if isinstance(result, list):
                    for child in result:
                        node.add_child(child)
                else:
                    node.add_child(result)
        
        # POP: Clean up cache when leaving this node
        # Pop if: (1) we pushed a landmark, OR (2) this is a prefetched element
        if should_cache:
            self.landmark_cache.pop()
            self.logger.info(f"[CACHE POP] Popped landmark for {node.tag}.{'.'.join(node.classes)} | Cache size: {self.landmark_cache.size()}")
        elif is_prefetched:
            self.landmark_cache.pop()
            self.logger.info(f"[CACHE POP] Popped prefetched {node.tag} | Cache size: {self.landmark_cache.size()}")
        
        return node
        


    def annotate_sti_branch(self,node):
        # takes in a node and annnotate only its children this will be used for st{index} nodes  exclusively

        #this is hardcoded as fuck, will made it scalable later on
        
        self.logger.info(f"[ANNOTATE_STI] Initial cache size: {self.landmark_cache.size()}, and the respective node is:")
        self.logger.info(self.landmark_cache.top().get_attribute('class'))
        
        stk = Stack() 
        stk.push(node)
        
        self.logger.info("[ANNOTATE_STI] Pushed root node:")
        stk.top().print_attributes()
                

        while not stk.is_empty():
            current = stk.pop()

            self.logger.info("[POP TRACKING STACK] Popped node:")
            current.print_attributes()

            should_cache=(
                current.annotation == "landmark_element" and
                current.description != "root"
                )
    
            if should_cache:
                #This is a regular landmark node
                #this is hardcoded, need to make it more generic later on
                # the issue is li elements are prefetched and stored in the landmark cache before we even reach the <li> node in the tree, so when we reach the <li> node and we read "annotation":"landmark_element", we skip it since it's already in the cache
                #so here we should  make a strategy, if the parennt has a configured landmark; meaning we're prefetching its children, then we skip pushing it again
                if current.tag != "li":
                    landmark = self.landmark_cache.top()
                    selector = current.get_css_selector()
                    landmark_element = landmark.find_element(By.CSS_SELECTOR, selector)
                    self.landmark_cache.push(landmark_element)

                    self.logger.info(f"Cache size: {self.landmark_cache.size()} | [CACHE PUSH] Pushed landmark:")
                    current.print_attributes()

                # the case where wwe have multiple <li> elements, we need to prefetch them and store them in a queue
                #if node siblings have the same tag and >=1:
                    #prefetch them all and store them in a queue
                    #then enque them in the landmark cache
                    #this should work for the <li> and <a> tags
                
                if current.children and current.children[0].tag == "li" and len(current.children) >=1:
                    landmark = self.landmark_cache.top()
                    li_elements = landmark.find_elements(By.TAG_NAME, "li")
                    self.logger.info(f"[PREFETCH] Found {len(li_elements)} <li> elements")
                    for idx, li_el in enumerate(li_elements):
                        self.landmark_cache.push(li_el)
                        self.logger.info(f"[CACHE PUSH] Pushed <li> #{idx+1} | Cache size: {self.landmark_cache.size()}")

                if current.children and current.children[0].tag == "a" and len(current.children) >=1:
                    a_web_elements_queue = Queue()
                    landmark = self.landmark_cache.top()
                    a_elements = landmark.find_elements(By.TAG_NAME, "a")
                    self.logger.info(f"[PREFETCH] Found {len(a_elements)} <a> elements")
                    for idx, a_el in enumerate(a_elements):
                        a_web_elements_queue.enqueue(a_el)
                        self.logger.info(f"[QUEUE ENQUEUE] Enqueued <a> #{idx+1}")

            elif current.annotation == "target_element":

                self.logger.info(f"[TARGET] Processing target element:")
                current.print_attributes()

                #self._annotate_node(current,None)
                if current.tag == "a":
                    self.logger.info(f"[TARGET] <a> tag - checking queue")
                    if a_web_elements_queue is not None:
                        current.web_element = a_web_elements_queue.front()
                        a_web_elements_queue.dequeue()
                        self.logger.info(f"[QUEUE DEQUEUE] Dequeued <a>")
                    else:
                        self.logger.info(f"[TARGET] Queue is None")
                else:
                    selector_value = current.get_css_selector()
                    self.logger.info(f"[TARGET] Selector: {selector_value}")
                    current.web_element = self.landmark_cache.top().find_element(By.CSS_SELECTOR,selector_value)
                    self.logger.info(f"[TARGET] Annotated web_element")


            if not current.children:

                self.logger.info(f"[LEAF] Reached leaf node")
                current.print_attributes()

                if self.landmark_cache.size() > 1:  # Don't pop root
                    self.landmark_cache.pop()
                    self.logger.info(f"[CACHE POP] Popped at leaf | Cache size: {self.landmark_cache.size()}")

                else:
                    self.logger.info(f"[LEAF] Not popping (cache size = 1)")

            if current.children:
                self.logger.info(f"[CHILDREN] Pushing {len(current.children)} children (reversed)")
            for child in reversed(current.children):
                stk.push(child)
                self.logger.info("[PUSH TRACKING STACK] Pushed child node:")
                child.print_attributes()
            

        
        self.logger.info(f"\n[ANNOTATE_STI] Completed | Final cache size: {self.landmark_cache.size()}")
                    

    def get_dynamic_count(self):
      
        child_elements = self.landmark_cache.top().find_elements(By.XPATH, "./*")
        self.logger.info("dynamic count found:", len(child_elements))
        return len(child_elements)
      
    def _annotate_root(self):
        """Find and attach the root web element."""
        try:
            if self.root_node:
                selector_value = self.root_node.get_css_selector()
                self.root_node.web_element = self.driver.find_element(By.CSS_SELECTOR, selector_value)
        except Exception as e:
            self.logger.error(f"failed to annotate root: {e}")

    
    def full_build_layout_tree(self):
        
        # Initialize root FIRST
        self.root_node = self._create_node(self.schema)
        self._annotate_root()
        self.landmark_cache.push(self.root_node.web_element)
        
        # Build children of root
        if "children" in self.schema:
            for child_schema in self.schema["children"]:
                result = self._build_tree_layout(child_schema, parent_node=self.root_node)
                
                if isinstance(result, list):
                    for child in result:
                        self.root_node.add_child(child)
                else:
                    self.root_node.add_child(result)
        
    
        

    def annotate_full_main_tree(self):
         #this is made only for the main page
        # annotate the full tree using annotate_branch so i detect the sti nodes and annotate them properly then move on to the next sibling node

        allowed_ids = {f"st{index}" for index in range(1, 34) if index not in (2, 4)} # this is hardcoded for now will make it dynamic later on

        result = []
        stack = [self.root_node]

        while stack:
            node = stack.pop()

            node_id = node.attrs.get("id", None)
            if node_id in allowed_ids:
                result.append(node)

            # Continue DFS
            stack.extend(reversed(node.children))


        for sti_node in result:
            self.logger.info(f"Annotating branch for node ID: {sti_node.attrs.get('id')}")
            self.annotate_sti_branch(sti_node)

    
    def annotate_regular_tree(self):
        """Annotate using recursive DFS for proper push/pop symmetry"""
        #this is made for regular pages where we don't have sti nodes, such as the exam page and the solution page
    
        def _annotate_recursive(node):
            pushed_landmark = False
            
            if node.annotation == "landmark_element" and node.description != "root":
                landmark = self.landmark_cache.top()
                selector = node.get_css_selector()
                landmark_element = landmark.find_element(By.CSS_SELECTOR, selector)
                self.landmark_cache.push(landmark_element)
                pushed_landmark = True
                self.logger.info(f"[CACHE PUSH] Pushed landmark | Cache size: {self.landmark_cache.size()}")
            
            elif node.annotation == "target_element":
                selector_value = node.get_css_selector()
                node.web_element = self.landmark_cache.top().find_element(By.CSS_SELECTOR, selector_value)
                self.logger.info(f"[TARGET] Annotated web_element")
        
            # Process children
            for child in node.children:
                _annotate_recursive(child)
            
            # Pop if we pushed
            if pushed_landmark:
                self.landmark_cache.pop()
                self.logger.info(f"[CACHE POP] Popped landmark | Cache size: {self.landmark_cache.size()}")
    
        _annotate_recursive(self.root_node)