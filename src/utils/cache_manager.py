import hashlib
import json
import psycopg2
from psycopg2.extras import DictCursor
import os
from datetime import datetime
from typing import Optional, Any
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class CacheManager:
    def __init__(self):
        database_url = os.environ.get('DATABASE_URL', 'postgresql://postgres:postgres@localhost:5432/postgres')
        self.conn = psycopg2.connect(database_url)

    def _generate_hash(self, data: dict) -> str:
        """Generate a unique hash for the request data"""
        # Sort the dictionary to ensure consistent hashing
        serialized = json.dumps(data, sort_keys=True)
        return hashlib.sha256(serialized.encode()).hexdigest()

    def get_cached_response(self, model_type: str, request_data: dict) -> Optional[str]:
        """Retrieve cached response if it exists"""
        data_hash = self._generate_hash(request_data)
        
        with self.conn.cursor(cursor_factory=DictCursor) as cur:
            cur.execute(
                "SELECT response_data FROM cache WHERE model_type = %s AND data_hash = %s",
                (model_type, data_hash)
            )
            result = cur.fetchone()
            return result['response_data'] if result else None

    def cache_response(self, model_type: str, request_data: dict, response_data: str) -> None:
        """Cache the response data"""
        data_hash = self._generate_hash(request_data)
        
        with self.conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO cache (model_type, data_hash, response_data)
                VALUES (%s, %s, %s)
                ON CONFLICT (model_type, data_hash) 
                DO UPDATE SET response_data = EXCLUDED.response_data
                """,
                (model_type, data_hash, response_data)
            )
            self.conn.commit()

    def __del__(self):
        """Close the database connection when the object is destroyed"""
        if hasattr(self, 'conn'):
            self.conn.close()