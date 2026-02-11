from dom_processing.dom_tree_builder.tree_building.builder_interface import TreeBuilderStrategy
from dom_processing.dom_tree_builder.tree_building.conditions.conditions_interfaces import Condition, ConditionAnnotationStrategy, ConditionBuildStrategy
from selenium.webdriver.common.by import By

from utils import generate_selector_from_webelement


class ConditionExamSolutionLinks(Condition):
    id = 1

    def evaluate(self, caching_coordinator):
        links = []

        current_landmark = caching_coordinator._cache_handler.get_current_landmark()
        elements = caching_coordinator._cache_handler._element_finder.find_multiple(
            current_landmark, By.XPATH, "./a"
        )

        for a in elements:
            text = a.text.strip().lower()
            color_attr = a.get_attribute("color")  # Get HTML attribute, not CSS property

            if text in ("exam", "solution") and color_attr == "blue":
                links.append(a)
                
        return links

    def is_satisfied(self, result) -> bool:
        return len(result) > 0


class ConditionExamSolutionBuild(ConditionBuildStrategy):
    id = 1

    def apply(self, parent_node,condition_result,schema_queries,stack):
        
        if not condition_result:
            self._prune_empty_branch(parent_node)
            return []

        
        exam_schema = schema_queries._schema.get("exam_schema")
        exam_node = self._create(parent_node, exam_schema, self.id)
        stack.append((exam_schema, exam_node, 'enter'))

        parent_node.add_child(exam_node)



        if len(condition_result) == 2:
            solution_schema = schema_queries._schema.get("solution_schema")
            solution_node = self._create(parent_node, solution_schema, self.id)
            stack.append((solution_schema, solution_node, 'enter'))
            parent_node.add_child(solution_node)

        
        

    def _create(self, parent, schema, condition_id):
        return TreeBuilderStrategy.create_node(
            "regular",
            schema,
            parent=parent,
            condition=True,
            condition_id=condition_id,
            target_types=schema["target_types"]
        )

    def _prune_empty_branch(self, node):
        current = node
        while current.parent is not None:
            parent = current.parent
            parent.remove_child(current)
            current = parent
            if current.children:
                break


class ConditionExamSolutionAnnotation(ConditionAnnotationStrategy):
    id = 1

    def apply(self, node,caching_coordinator):
        current_landmark = caching_coordinator._cache_handler.get_current_landmark()

        if "exam" in node.target_types:
            element = caching_coordinator._cache_handler._element_finder.find_single(
                current_landmark, By.XPATH,
                "//*[contains(translate(text(), 'Exam', 'exam'), 'exam')]"
            )
            node.web_element = element

        if "solution" in node.target_types:
            element = caching_coordinator._cache_handler._element_finder.find_single(
                current_landmark, By.XPATH,
                "//*[contains(translate(text(), 'Solution', 'solution'), 'solution')]"
            )
            node.web_element = element
