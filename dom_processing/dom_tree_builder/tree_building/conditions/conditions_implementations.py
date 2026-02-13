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
            href = a.get_attribute("href")
            text = a.text.strip().lower()
            if not href:
                continue
            if text in ("真题","试题", "答案")  : #("exam", "solution")
                links.append(a)
                
        return links

    def is_satisfied(self, result) -> bool:
        # 1. Check if result is empty
        if not result:
            return False

        # 2. Extract texts from the result elements to validate logic.
        # We use a set for faster lookups and to handle duplicates.
        found_texts = {a.text.strip().lower() for a in result}

        has_exam = "真题" in found_texts or "试题" in found_texts
        has_solution = "答案" in found_texts

        # 3. Apply the rule: "solution" can't exist alone; it needs "exam"
        if has_solution and not has_exam:
            return False

        # If we have only "exam", or both "exam" and "solution", return True
        return True


class ConditionExamSolutionBuild(ConditionBuildStrategy):
    id = 1

    def apply(self, parent_node,condition_result,schema_queries,stack):
        
        if not condition_result:
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
        #### here is the issue; the target_nodes don't get added to the node; why is that?
        node = TreeBuilderStrategy.create_node(
            "regular",
            schema,
            parent=parent,
            condition=True,
            condition_id=condition_id,
        )
    
        return node
        

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
    def _prune_empty_branch(self, node):
        current = node
        while current.parent is not None:
            parent = current.parent
            parent.remove_child(current)
            current = parent
            if current.children:
                break
            
    def apply(self, node, caching_coordinator):
        current_landmark = caching_coordinator._cache_handler.get_current_landmark()
        
        
        elements = caching_coordinator._cache_handler._element_finder.find_multiple(
            current_landmark, By.XPATH, "./a"
        )

        
        for a in elements:
            text = a.text.strip()
            href = a.get_attribute("href")
            
            if not href or not href.strip():
                continue

            if text in ("真题","试题")  and "exam" in node.target_types:
                node.web_element = a
                break

            if text == "答案"  and "solution" in node.target_types:
                node.web_element = a
                break

        if not node.web_element:
                raise Exception("a tag element didn't get assigned")

                            
