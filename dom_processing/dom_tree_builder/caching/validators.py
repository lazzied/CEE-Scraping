

from dom_processing.dom_tree_builder.caching.interfaces import WebElementInterface


class ElementValidator:
    """Validates element types - easily mockable"""
    @staticmethod
    def is_valid_landmark( element: any) -> bool:
        """
        Check if element is valid for caching
        
        Input: element - Element to validate
        Output: bool
        """
        # In production, check for WebElement
        if isinstance(element, WebElementInterface):
            return True
        else:
            raise Exception("a wrong type element is trying to get pushed to tha landmark cache")