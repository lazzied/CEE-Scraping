from realtime import Any
from dom.node import BaseDOMNode
from dom_processing.dom_tree_builder.tree_building.conditions_interfaces import Condition, ConditionAnnotationStrategy, ConditionBuildStrategy
from selenium.webdriver.common.by import By

from dom_processing.json_parser import SchemaQueries


class ConditionExamSolutionLinks(Condition):
    id = 1

    def evaluate(self, **context):
        caching_coordinator = context['caching_coordinator']
        links = []

        current_landmark = caching_coordinator._cache_handler.get_current_landmark()
        elements = caching_coordinator._cache_handler._element_finder.find_multiple(
            current_landmark, By.XPATH, "./a"
        )

        for a in elements:
            text = a.text.strip().lower()
            color = a.value_of_css_property("color")

            if text in ("exam", "solution") and color == "blue":
                links.append(a)

        return links

    def is_satisfied(self, result) -> bool:
        return len(result) > 0


class ConditionExamSolutionBuild(ConditionBuildStrategy):
    id = 1

    def apply(self, **context):
        node = context['node']
        condition_result = context['condition_result']
        schema_queries = context['schema_queries']
        
        if not condition_result:
            self._prune_empty_branch(node)
            return []

        created_nodes = []
        
        exam_schema = schema_queries.schema.get("exam_schema")
        exam_node = self._create(node, exam_schema, self.id)
        node.add_child(exam_node)
        created_nodes.append(exam_node)

        if len(condition_result) == 2:
            solution_schema = schema_queries.schema.get("solution_schema")
            solution_node = self._create(node, solution_schema, self.id)
            node.add_child(solution_node)
            created_nodes.append(solution_node)
        
        return created_nodes

    def _create(self, parent, schema, condition_id):
        return parent.create_node(
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

    def apply(self, **context):
        node = context['node']
        caching_coordinator = context['caching_coordinator']
        
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
