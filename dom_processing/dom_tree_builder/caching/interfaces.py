
from abc import ABC, abstractmethod
from typing import List, Protocol, Optional



class WebElementInterface(Protocol):
    """Protocol for web element operations - doesn't require Selenium"""
    
    def find_element(self, by: str, selector: str) -> 'WebElementInterface':
        ...
    
    def find_elements(self, by: str, selector: str) -> List['WebElementInterface']:
        ...


class ElementFinder(ABC):
    """Abstract element finder - can be mocked easily"""
    
    @abstractmethod
    def find_single(self, parent: WebElementInterface, by: str, selector: str) -> Optional[WebElementInterface]:
        """Find single element"""
        pass
    
    @abstractmethod
    def find_multiple(self, parent: WebElementInterface, by: str, selector: str) -> List[WebElementInterface]:
        """Find multiple elements"""
        pass
    