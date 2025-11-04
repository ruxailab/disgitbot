"""
Singleton wrapper for the service container.
"""

class Singleton:
    """
    A wrapper to ensure a class is only instantiated once
    by the ServiceContainer.
    """
    def __init__(self, implementation_class):
        self._implementation_class = implementation_class
        self._instance = None

    def get_instance(self):
        """
        Get the singleton instance. 
        Creates it if it doesn't exist yet.
        """
        if self._instance is None:
            self._instance = self._implementation_class()
        return self._instance