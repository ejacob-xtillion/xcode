"""
Shared interfaces and protocols for xCode.

This module defines common interfaces used across the codebase to ensure
consistent behavior and enable duck typing.
"""

from typing import Any, Protocol


class Statsable(Protocol):
    """
    Protocol for objects that can provide statistics.
    
    Any class implementing this protocol should provide a get_stats() method
    that returns a dictionary of statistics about the object's state.
    """

    def get_stats(self) -> dict[str, Any]:
        """
        Get statistics about the object's current state.
        
        Returns:
            Dictionary containing relevant statistics. Keys should be
            descriptive strings, values can be any JSON-serializable type.
        """
        ...
