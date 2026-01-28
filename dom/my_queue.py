class Queue:
    def __init__(self):
        self.items = []

    def enqueue(self, item):
        """Add item to the rear of the queue"""
        self.items.append(item)

    def dequeue(self):
        """Remove and return the front item of the queue"""
        if self.is_empty():
            return None
        return self.items.pop(0)

    def front(self):
        """Return the front item without removing it"""
        if self.is_empty():
            return None
        return self.items[0]

    def is_empty(self):
        """Check if the queue is empty"""
        return len(self.items) == 0

    def size(self):
        """Return the number of elements in the queue"""
        return len(self.items)
