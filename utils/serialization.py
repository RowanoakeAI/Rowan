from datetime import datetime, date
from bson import ObjectId
from typing import Any, Dict, List, Union
import json

class DataSerializer:
    """Utility class to handle serialization of complex data structures"""
    
    @staticmethod
    def serialize_object(obj: Any) -> Any:
        """Serialize a single object to JSON-compatible format"""
        if isinstance(obj, (datetime, date)):
            return obj.isoformat()
        if isinstance(obj, ObjectId):
            return str(obj)
        if isinstance(obj, dict):
            return {k: DataSerializer.serialize_object(v) for k, v in obj.items()}
        if isinstance(obj, (list, tuple)):
            return [DataSerializer.serialize_object(item) for item in obj]
        return obj

    @staticmethod
    def serialize_dict(data: Dict[str, Any]) -> Dict[str, Any]:
        """Serialize an entire dictionary and its nested structures"""
        return DataSerializer.serialize_object(data)

    @staticmethod
    def to_json(data: Union[Dict[str, Any], List[Any]]) -> str:
        """Convert data to JSON string after serialization"""
        serialized_data = DataSerializer.serialize_object(data)
        return json.dumps(serialized_data)