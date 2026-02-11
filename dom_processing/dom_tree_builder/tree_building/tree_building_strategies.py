from dom.node import BaseDOMNode, TemplateNode
from dom_processing.dom_tree_builder.caching.coordinators import CachingCoordinator
from dom_processing.dom_tree_builder.tree_building.builder_interface import TreeBuilderStrategy
from dom_processing.json_parser import ConfigQueries, SchemaQueries, TemplateRegistry
from selenium.webdriver.common.by import By
from dom_processing.dom_tree_builder.tree_building.conditions.conditions_interfaces import (
    Condition,
    ConditionBuildStrategy,
)
#don't delete this, it is essential for registry population:
from dom_processing.dom_tree_builder.tree_building.conditions import conditions_implementations
from utils import generate_selector_from_webelement, get_direct_children_in_range


class SimpleTreeBuilderStrategy(TreeBuilderStrategy):
    """Simple schema with no repeat templates"""
    @staticmethod
    def should_apply(
        schema_queries: SchemaQueries,
    ) -> bool:
        # No repeat detected in the current node
        return not schema_queries.json_schema_has_repeat()
    

    def build_node_tree_from_top(
    self,
    schema_queries: SchemaQueries,

    ) -> BaseDOMNode:
        """Build tree node iteratively using a stack"""
        
        # Create root node
        schema_node = schema_queries._schema.get("main_schema")

        root = self.create_node("root", schema_node)
        stack = [(schema_node, root)]
        
        while stack:
            current_schema, current_node = stack.pop()
            
            if schema_queries.has_children(current_schema):
                children_schemas = schema_queries.get_children(current_schema)
                
                for child_schema in children_schemas:
                    child_node = self.create_node("regular", child_schema, parent=current_node) # parent set here
                    current_node.add_child(child_node)
                    stack.append((child_schema, child_node))
        
        return root


class RepeatTreeBuilderStrategy(TreeBuilderStrategy):
    
    @staticmethod
    def should_apply( 
        schema_queries: SchemaQueries,
    ) -> bool:
        """Check if the entire schema has any repeat blocks, the research will start from the root node"""
        return schema_queries.json_schema_has_repeat()
    
    def get_dynamic_count(self, caching_coordinator: CachingCoordinator, invariant_selector:str) -> int: #this needs adjustment, repeat_tag is not enough, get more info on your specific divs
        """Get count of child elements from landmark cache"""

        current_landmark = caching_coordinator._cache_handler.get_current_landmark()
        if current_landmark is None:
            return 0
 
        selector = "./" + invariant_selector
        child_elements = caching_coordinator._cache_handler._element_finder.find_multiple(current_landmark, By.XPATH, selector)

        return len(child_elements)
    
    def _get_template_attributes(
            self,
            index: int,
            repeat_config: dict,
            schema_queries: SchemaQueries
        ) -> dict:
        if repeat_config['needs_indexing']:
            return schema_queries.get_dynamic_schema_node_attrs(
                repeat_config['template_schema'],
                placeholder=repeat_config['placeholder'],
                indexing_attribute = repeat_config["indexing_attribute"],
                index=index
            )
        else:
            return schema_queries.get_static_schema_node_attrs(
                repeat_config['template_schema']
            )
    def _get_repeat_configuration(
    self,
    child_schema: dict,
    schema_queries: SchemaQueries,
    config_queries: ConfigQueries,
    template_registry: TemplateRegistry,
    caching_coordinator: CachingCoordinator,
) -> dict:
    
        repeat_info = schema_queries.get_repeat_info(child_schema)
        
        template_name = repeat_info["template"]
        template_schema = template_registry.get_template_schema(template_name)
        
        # Get version name (configuration variant)
        template_configuration_version_name = repeat_info.get("template_configuration", "")
        
        # Validate version if specified
        if template_configuration_version_name:
            if not config_queries.has_versions(template_name):
                raise ValueError(
                    f"Version '{template_configuration_version_name}' specified for template '{template_name}', "
                    f"but this template has no configuration versions"
                )
            
            available_versions = config_queries.get_available_versions(template_name)
            if template_configuration_version_name not in available_versions:
                raise ValueError(
                    f"Configuration version '{template_configuration_version_name}' not found for template '{template_name}'. "
                    f"Available versions: {available_versions}"
                )
        
        # Build selector - use base template without version
        # Because selector depends on template structure, not configuration
        selector_list = template_registry.get_template_invariant_characteristics(
            template_name, config_queries  # No template_configuration_version_name needed for selector building
        )
        invariant_selector = template_registry.form_template_selector(
            template_name, selector_list
        )
        
        count = (
            self.get_dynamic_count(caching_coordinator, invariant_selector)
            if repeat_info["count"] == "auto"
            else repeat_info["count"]
        )
        
        # Get configuration parameters WITH version
        return {
            'template_name': template_name,
            'template_schema': template_schema,
            'template_configuration_version_name': template_configuration_version_name,
            'count': count,
            'needs_indexing': config_queries.needs_indexing(template_name, template_configuration_version_name),
            'placeholder': config_queries.get_placeholder(template_name, template_configuration_version_name),
            'indexing_attribute': config_queries.get_indexing_attribute(template_name, template_configuration_version_name),
            'skip_indices': config_queries.get_skip_indices(template_name, template_configuration_version_name),
            'starting_index': config_queries.get_starting_index(template_name, template_configuration_version_name),
            'finish_index':config_queries.get_finish_index(template_name, template_configuration_version_name)

        }
    

    def _should_skip_index(self, index: int, repeat_config: dict) -> bool:
        return (
            repeat_config['needs_indexing'] and  repeat_config['skip_indices'] and
            index in repeat_config['skip_indices']
        )

    def _handle_condition(self,child_schema,parent_node,schema_queries,caching_coordinator, stack):

        condition_id = schema_queries.get_condition_id(child_schema)

        condition = Condition.from_id(condition_id)()
        result = condition.evaluate(caching_coordinator)

        build_strategy = ConditionBuildStrategy.from_id(condition_id)()
        build_strategy.apply(
            parent_node=parent_node,
            condition_result=result,
            schema_queries=schema_queries,
            stack =stack
        )

    def build_node_tree_from_top(
            self,
            schema_queries: SchemaQueries,
            config_queries: ConfigQueries,
            template_registry: TemplateRegistry,
            caching_coordinator: CachingCoordinator,
        ):
        schema_node = schema_queries._schema.get("main_schema")
        root = self.create_node("root", schema_node)
        stack = [(schema_node, root, 'enter')]
        #root has already been cached, see main()
        while stack:
            current_schema, current_node, phase = stack.pop()

            if phase == "exit":
                # Handle exit phase - uncache landmark
                if caching_coordinator.should_cache_node(current_schema):
                    caching_coordinator.uncache_landmark()
                continue

            else: 
                #this shouldn't happen with the precache
                if isinstance(current_node,TemplateNode) and \
                config_queries.get_precache_bool(current_node.template_name):
                    # Explicitly skip caching
                    pass

                else:
                    if caching_coordinator.should_cache_node(current_schema):
                        caching_coordinator.cache_landmark_node(current_node)
                        
                stack.append((current_schema, current_node, 'exit'))

                if schema_queries.has_children(current_schema):
                    children_schemas = schema_queries.get_children(current_schema)
                    
                    for child_schema in children_schemas:
                        
                        if schema_queries.has_conditional(child_schema):
                            
                            #here the current node is the parent/
                            #here the most impportant thing is to correctly handle the caching and uncaching
                            self._handle_condition(child_schema,current_node,schema_queries,caching_coordinator,stack)
                            # here something weird happeining got me trippin
                            # never gets uncached

                        elif schema_queries.has_repeat(child_schema):

                            #handle the repeat block
                            repeat_config = self._get_repeat_configuration(
                                                            child_schema,
                                                            schema_queries,
                                                            config_queries,
                                                            template_registry,
                                                            caching_coordinator,
                                                        )
                            # get the starting and finishing boundaries:
                            #starting default = 1
                            # ending default = repeat_config['count'] 
                            if repeat_config['needs_indexing']:
                                start= repeat_config["starting_index"]
                                end = repeat_config["finish_index"]
                            else: 
                                start = 1
                                end = repeat_config["count"]
                            test_template_node_webelement_set= set()
                            test_template_node_webelement =""
                            template_node_num = 1

                            for i in range(start, end+1):
                                if repeat_config['needs_indexing'] and self._should_skip_index(i, repeat_config):
                                    continue

                                
                                attrs = self._get_template_attributes(i, repeat_config, schema_queries)
                                
                                template_node = self.create_node(
                                    "template",
                                    repeat_config['template_schema'],
                                    parent=current_node,
                                    attrs=attrs,
                                    template_name=repeat_config['template_name']
                                )
                                stack.append((repeat_config['template_schema'], template_node, 'enter'))
                                current_node.add_child(template_node)
                                """
                                if template instances don't have id that differs them and the template nodes are landmark: 
                                      here inside the range: in first iteration, we cache the first direct element
                                       second iteration wee cache the second child and so on
                                      but how to implement it? 
                                      - first we can cache it at the end of the node creation

                                      here's the algo
                                
                                      if template node doesn't differ from its siblings: no specific id like st{index} etc... :
                                        get all the direct children(or specify which children, the first? the 5th you can give input
                                        and push them to the landmark cache in the correct order
                                        at the top, even though it says enter; we don't cache it since we already cached it beforehand
                                        so we remove the landmark element so it doesn't get recached again in the enter phase

                                       templ
                                """

                            if config_queries.get_precache_bool(repeat_config['template_name']):
                                self.handle_precache(config_queries, caching_coordinator,template_registry,repeat_config['template_name'],current_node,"ALL")
                                


                        else:
                            child_node = self.create_node("regular", child_schema, parent=current_node)
                            current_node.add_child(child_node)
                            stack.append((child_schema, child_node, 'enter'))
        return root
                           
    def handle_precache(self,config_queries,caching_coordinator,template_registry,template_name,node,range):
        #check if the current landmark points to the parent node(current_node)
        #REMOVE TEMPLATE NAME LATER ON SINCE YOU CAN RETREIVE IT FROM THE TEMPLATE_REGISTRY
        current_landmark = caching_coordinator._cache_handler.get_current_landmark()
        config_queries.get_precache_bool(template_name)
       
        if generate_selector_from_webelement(current_landmark) == node.get_css_selector() :
            template_invariant_characteristics=  template_registry.get_template_invariant_characteristics(template_name,config_queries)
            template_selector = template_registry.form_template_selector(template_name,template_invariant_characteristics)
            
            template_nodes_webelement = get_direct_children_in_range(current_landmark, range,template_selector)
            for template_node__webelement in template_nodes_webelement:
                caching_coordinator.cache_webelement(template_node__webelement)
            
        
            





    
