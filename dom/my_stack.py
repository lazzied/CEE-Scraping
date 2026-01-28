# my_stack.py

class Stack:
    def __init__(self):
        """Initialize an empty stack."""
        self.items = []
    
    def push(self, item):
        """
        Add an item to the top of the stack.
        
        Args:
            item: The item to add
        """
        self.items.append(item)
    
    def pop(self):
        """
        Remove and return the top item from the stack.
        
        Returns:
            The top item
        
        Raises:
            IndexError: If the stack is empty
        """
        if self.is_empty():
            raise IndexError("pop from empty stack")
        return self.items.pop()
    
    def top(self):
        """
        Return the top item without removing it.
        
        Returns:
            The top item
        
        Raises:
            IndexError: If the stack is empty
        """
        if self.is_empty():
            raise IndexError("top from empty stack")
        return self.items[-1]
    
    def peek(self):
        """Alias for top(). Return the top item without removing it."""
        return self.top()
    
    def is_empty(self):
        """
        Check if the stack is empty.
        
        Returns:
            bool: True if empty, False otherwise
        """
        return len(self.items) == 0
    
    def size(self):
        """
        Get the number of items in the stack.
        
        Returns:
            int: Number of items
        """
        return len(self.items)
    
    def clear(self):
        """Remove all items from the stack."""
        self.items = []
    
    def __len__(self):
        """Support len(stack) syntax."""
        return len(self.items)
    
    def __bool__(self):
        """Support bool(stack) and 'if stack:' syntax."""
        return not self.is_empty()
    
    def __str__(self):
        """String representation of the stack."""
        return f"Stack({self.items})"
    
    def __repr__(self):
        """Developer-friendly representation."""
        return f"Stack({self.items})"