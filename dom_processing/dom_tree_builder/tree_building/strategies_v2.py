from abc import ABC, abstractmethod
from typing import List, Optional, Any, Generic, TypeVar
from selenium.webdriver.common.by import By
from dom.node import BaseDOMNode
from dom_processing.dom_tree_builder.caching.coordinators import CachingCoordinator
from dom_processing.dom_tree_builder.caching.interfaces import ElementFinder
from dom_processing.dom_tree_builder.tree_building.builder_interface import TreeBuilderStrategy
from dom_processing.dom_tree_builder.tree_building.conditions_interfaces import Condition, ConditionBuildStrategy
from dom_processing.json_parser import ConfigQueries, SchemaQueries, TemplateRegistry
from selenium.webdriver.common.by import By


class SimpleTreeBuilderStrategy(TreeBuilderStrategy):
    """Simple schema with no repeat templates"""
    
    def should_apply(
        self, 
        schema_queries: SchemaQueries,
        schema_node: dict
    ) -> bool:
        # No repeat detected in the current node
        return not schema_queries.has_repeat(schema_node)
    

    def build_node_tree_from_top(
    self,
    schema_queries: SchemaQueries,
    schema_node: dict,

    ) -> BaseDOMNode:
        """Build tree node iteratively using a stack"""
        
        # Create root node
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
    def should_apply(
        self, 
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
        #this combines info from the mainschema and config template, we merge the important info into one dict
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
        
        selector_list = template_registry.get_template_invariant_characteristics(template_name,config_queries)
        invariant_selector = template_registry.form_template_selector(template_name,selector_list)
        

        count = (
            #this is for testing: now we assume we can differentiate the children by their tag
            self.get_dynamic_count(caching_coordinator, invariant_selector)
            if repeat_info["count"] == "auto"
            else repeat_info["count"]
        )
         #any adding or deleting happens here
        
        return {
            'template_name': template_name,
            'template_schema': template_schema,
            'count': count,
            'needs_indexing': config_queries.needs_indexing(template_name),
            "placeholder": config_queries.get_placeholder(template_name),
            "indexing_attribute": config_queries.get_indexing_attribute(template_name),
            'skip_indices': config_queries.get_skip_indices(template_name)
        }
    def _should_skip_index(self, index: int, repeat_config: dict) -> bool:
        return (
            repeat_config['needs_indexing'] and  repeat_config['skip_indices'] and
            index in repeat_config['skip_indices']
        )

    def _handle_condition(self,current_schema,current_node,schema_queries,caching_coordinator):
        condition_id = current_schema.get("condition_id")

        condition = Condition.from_id(condition_id)()
        result = condition.evaluate(caching_coordinator)

        build_strategy = ConditionBuildStrategy.from_id(condition_id)()
        build_strategy.apply(
            node=current_node,
            condition_result=result,
            schema_queries=schema_queries,
            caching_coordinator=caching_coordinator
        )

    def build_node_tree_from_top(
            self,
            schema_queries: SchemaQueries,
            config_queries: ConfigQueries,
            template_registry: TemplateRegistry,
            caching_coordinator: CachingCoordinator,
            schema_node: dict,
        ):
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
                if caching_coordinator.should_cache_node(current_schema):
                    caching_coordinator.cache_landmark_node(current_node)
                stack.append((current_schema, current_node, 'exit'))
     
                if schema_queries.has_children(current_schema):
                    children_schemas = schema_queries.get_children(current_schema)
                    
                    for child_schema in children_schemas:
                        if schema_queries.has_conditional(child_schema):
                            self._handle_condition(current_schema,current_node,schema_queries,caching_coordinator)
                            continue                           

                        if schema_queries.has_repeat(child_schema):
                            #handle the repeat block
                            repeat_config = self._get_repeat_configuration(
                                                            child_schema,
                                                            schema_queries,
                                                            config_queries,
                                                            template_registry,
                                                            caching_coordinator,
                                                        )
                            
                            for i in range(repeat_config['count'], 0, -1):
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

                        else:
                            child_node = self.create_node("regular", child_schema, parent=current_node)
                            current_node.add_child(child_node)
                            stack.append((child_schema, child_node, 'enter'))
        return root
                           
                  





    
