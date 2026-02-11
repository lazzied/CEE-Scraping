from dom.node import BaseDOMNode, TemplateNode
from dom.selenium_driver import SeleniumDriver
from dom_processing.dom_tree_builder.caching.coordinators import CachingCoordinator
from dom_processing.dom_tree_builder.tree_building.conditions.conditions_interfaces import ConditionAnnotationStrategy
from dom_processing.dom_tree_builder.tree_building.tree_building_entry_point import BuildTree
from dom_processing.dom_tree_builder.tree_building.tree_building_strategies import RepeatTreeBuilderStrategy
from dom_processing.json_parser import ConfigQueries, SchemaQueries, TemplateRegistry
from utils import generate_selector_from_webelement


class AnnotateTree:

    def annotate_tree(
        self, 
        driver: SeleniumDriver,
        tree_root: BaseDOMNode, 
        caching_coordinator: CachingCoordinator, 
        schema_query: SchemaQueries,
        config_queries: ConfigQueries,
        template_registry: TemplateRegistry
    ) -> None:
        """
        Annotate the tree by finding web elements for target nodes.
        Uses DFS traversal with enter/exit phases for proper cache lifecycle.
        
        Args:
            tree_root: Root node of the DOM tree
            caching_coordinator: Manages landmark caching
            element_finder: Finds web elements
            schema_query: Queries schema information
        """
        root_element = BuildTree.get_root_web_element(driver, schema_query)
        caching_coordinator.initialize_with_root(root_element)
        
        stack = [(tree_root, 'enter')]
        
        while stack:
            current_node, phase = stack.pop()
            
            if phase == 'exit':
                # _handle_exit_phase logic
                schema_node = current_node.schema_node
                
                if caching_coordinator.should_cache_node(schema_node):
                    caching_coordinator.uncache_landmark()
                continue
            else:
                # _handle_enter_phase logic
                schema_node = current_node.schema_node

                if isinstance(current_node, TemplateNode) and \
                            config_queries.get_precache_bool(current_node.template_name):
                        # Explicitly skip caching
                        pass
                else:
                        if caching_coordinator.should_cache_node(schema_node):
                            caching_coordinator.cache_landmark_node(current_node)

                if schema_query.is_target(schema_node):
                        # _annotate_target_node logic
                        if current_node.web_element is None:
                            parent_element = caching_coordinator._cache_handler.get_current_landmark()
                            selector = current_node.get_css_selector()
                            
                            element_finder = caching_coordinator._cache_handler._element_finder
                            current_node.web_element = element_finder.find_single(
                                parent_element,
                                "CSS_SELECTOR",
                                selector
                            )
                stack.append((current_node, 'exit'))

                template_nodes = []

                # Push children for processing
                if current_node.children:
                    # _push_children_to_stack logic
                    # Push children in reverse order so first child is processed first (LIFO)
                    for child in current_node.children:
                        if child.condition:  # when the web element requires more than a css selector for identification
                            # _handle_condition logi
                          
                            condition_id = child.condition_id
                            condition_annotation = ConditionAnnotationStrategy.from_id(condition_id)()
                            condition_annotation.apply(child, caching_coordinator)
                            #sometimes,
                          
                            #should not be "" never, if it does,
                        if isinstance(child, TemplateNode) and config_queries.get_precache_bool(child.template_name):
                            template_nodes.append(child)

                        stack.append((child, 'enter'))

                    if template_nodes:
                        # _precache_children logic
                        RepeatTreeBuilderStrategy.handle_precache(
                            config_queries,
                            caching_coordinator,
                            template_registry,
                            template_nodes[0].template_name,
                            current_node,
                            "ALL"
                        )