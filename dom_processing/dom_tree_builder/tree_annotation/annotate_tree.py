from dom.node import BaseDOMNode
from dom_processing.dom_tree_builder.caching.coordinators import CachingCoordinator
from dom_processing.dom_tree_builder.tree_building.conditions.conditions_interfaces import ConditionAnnotationStrategy
from dom_processing.json_parser import SchemaQueries


class AnnotateTree:

    def annotate_tree(
        self, 
        tree_root: BaseDOMNode, 
        caching_coordinator: CachingCoordinator, 
        schema_query: SchemaQueries
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
        caching_coordinator.initialize_with_root(tree_root)
        
        stack = [(tree_root, 'enter')]
        
        while stack:
            current_node, phase = stack.pop()
            
            if phase == 'exit':
                self._handle_exit_phase(current_node, caching_coordinator)
            else:
                if current_node.condition: #when the web element requires more than a css selector for identification
                    self._handle_condition(current_node,caching_coordinator)

                    continue
                else:
                    self._handle_enter_phase(
                        current_node, 
                        stack, 
                        caching_coordinator, 
                        schema_query
                    )

    def _handle_condition(self,current_node,caching_coordinator):
        condition_id=  current_node.condition_id
        condition_annotation = ConditionAnnotationStrategy.from_id(condition_id)()

        condition_annotation.apply(current_node,caching_coordinator)

    def _handle_exit_phase(
        self, 
        current_node: 'BaseDOMNode', 
        caching_coordinator: CachingCoordinator,
    ) -> None:
        """
        Handle exit phase - uncache landmark if needed.
        
        Args:
            current_node: Node being exited
            caching_coordinator: Manages landmark caching
            schema_query: Queries schema information
        """
        schema_node = current_node.schema_node
        
        if caching_coordinator.should_cache_node(schema_node):
            caching_coordinator.uncache_landmark()
    
    def _handle_enter_phase(
        self,
        current_node: 'BaseDOMNode',
        stack: list,
        caching_coordinator: CachingCoordinator,
        schema_query: SchemaQueries
    ) -> None:
        """
        Handle enter phase - cache landmark if needed, annotate target, push children.
        
        Args:
            current_node: Node being entered
            stack: DFS stack
            caching_coordinator: Manages landmark caching
            element_finder: Finds web elements
            schema_query: Queries schema information
        """
        schema_node = current_node.schema_node
        
        # Cache landmark and schedule exit phase
        if caching_coordinator.should_cache_node(schema_node):
            self._cache_landmark(current_node, stack, caching_coordinator)
        
        # Annotate if target node
        if schema_query.is_target(schema_node):
            
            self._annotate_target_node(current_node, caching_coordinator)
        
        # Push children for processing
        self._push_children_to_stack(current_node, stack)
    
    def _cache_landmark(
        self,
        current_node: 'BaseDOMNode',
        stack: list,
        caching_coordinator: CachingCoordinator
    ) -> None:
        """
        Cache a landmark node and schedule its exit phase.
        
        Args:
            current_node: Node to cache
            stack: DFS stack
            caching_coordinator: Manages landmark caching
        """
        # Push exit phase first (LIFO) so we uncache after processing all children
        stack.append((current_node, 'exit'))
        caching_coordinator.cache_landmark_node(current_node)
    
    
    def _annotate_target_node(
        self,
        current_node: 'BaseDOMNode',
        caching_coordinator: CachingCoordinator,
    ) -> None:
        """
        Find and attach web element to target node.
        
        Args:
            current_node: Target node to annotate
            caching_coordinator: Provides current landmark context
            element_finder: Finds web elements
        """

        parent_element = caching_coordinator._cache_handler.get_current_landmark()
        selector = current_node.get_css_selector()
        
        # this doesn't work
        element_finder = caching_coordinator._cache_handler._element_finder
        current_node.web_element = element_finder.find_single(
            parent_element,
            "CSS_SELECTOR",
            selector
        )
    
    def _push_children_to_stack(
        self,
        current_node: 'BaseDOMNode',
        stack: list
    ) -> None:
        """
        Push children to stack in reverse order for left-to-right processing.
        
        Args:
            current_node: Parent node
            stack: DFS stack
        """
        # Push children in reverse order so first child is processed first (LIFO)
        for child in reversed(current_node.children):
            stack.append((child, 'enter'))

    