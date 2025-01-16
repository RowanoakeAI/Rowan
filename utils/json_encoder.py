from datetime import datetime, date
from bson import ObjectId
from json import JSONEncoder
from typing import Any

class RowanJSONEncoder(JSONEncoder):
    """Custom JSON encoder that handles datetime, date, and MongoDB ObjectId objects.
    
    This encoder converts:
    - datetime/date objects to ISO format strings
    - MongoDB ObjectId to string representation
    - Provides informative errors for non-serializable objects
    """
    def default(self, obj: Any) -> str:
        try:
            if isinstance(obj, (datetime, date)):
                return obj.isoformat()
            if isinstance(obj, ObjectId):
                return str(obj)
            return super().default(obj)
        except TypeError as e:
            # Provide more context about which object couldn't be serialized
            raise TypeError(
                f"Object of type {type(obj).__name__} is not JSON serializable: {obj}"
            ) from e