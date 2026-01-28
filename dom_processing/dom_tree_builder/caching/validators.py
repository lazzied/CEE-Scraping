class ElementValidator:
    """Validates element types - easily mockable"""
    
    def is_valid_landmark(self, element: any) -> bool:
        """
        Check if element is valid for caching
        
        Input: element - Element to validate
        Output: bool
        """
        # In production, check for WebElement
        from selenium.webdriver.remote.webelement import WebElement
        return isinstance(element, WebElement)