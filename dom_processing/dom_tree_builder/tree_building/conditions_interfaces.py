from abc import ABC, abstractmethod
from typing import Any, Generic, TypeVar

T = TypeVar('T')

class Condition(ABC, Generic[T]):
    """Evaluates whether a special condition is met."""
    _registry = {}
    id: int

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        if not hasattr(cls, "id"):
            raise ValueError(f"{cls.__name__} must define an id")
        if cls.id in cls._registry:
            raise ValueError(f"Duplicate condition id: {cls.id}")
        cls._registry[cls.id] = cls

    @classmethod
    def from_id(cls, id_: int):
        return cls._registry[id_]

    @abstractmethod
    def evaluate(self, **context) -> T:
        """
        Evaluate condition and return result data.
        
        Typical context includes:
        - caching_coordinator: CachingCoordinator
        - schema_queries: SchemaQueries
        - etc.
        """
        pass

    @abstractmethod
    def is_satisfied(self, result: T) -> bool:
        """Check if evaluation result satisfies the condition."""
        pass


class ConditionBuildStrategy(ABC):
    """Handles tree building when condition is met."""
    _registry = {}
    id: int

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        if not hasattr(cls, "id"):
            raise ValueError(f"{cls.__name__} must define an id")
        if cls.id in cls._registry:
            raise ValueError(f"Duplicate build strategy id: {cls.id}")
        cls._registry[cls.id] = cls

    @classmethod
    def from_id(cls, id_: int):
        return cls._registry[id_]

    @abstractmethod
    def apply(self, **context) -> Any:
        """
        Apply tree building based on condition result.
        
        Typical context includes:
        - node: BaseDOMNode - The parent node to build from
        - condition_result: Any - Result from condition evaluation
        - schema_queries: SchemaQueries
        - caching_coordinator: CachingCoordinator
        
        Returns:
            List of created nodes (or None if no nodes created)
        """
        pass


class ConditionAnnotationStrategy(ABC):
    """Handles annotation when condition is met."""
    _registry = {}
    id: int

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        if not hasattr(cls, "id"):
            raise ValueError(f"{cls.__name__} must define an id")
        if cls.id in cls._registry:
            raise ValueError(f"Duplicate annotation strategy id: {cls.id}")
        cls._registry[cls.id] = cls

    @classmethod
    def from_id(cls, id_: int):
        return cls._registry[id_]

    @abstractmethod
    def apply(self, **context) -> None:
        """
        Apply annotation logic to node.
        
        Typical context includes:
        - node: BaseDOMNode - The node to annotate
        - caching_coordinator: CachingCoordinator
        """
        pass