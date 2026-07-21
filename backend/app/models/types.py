"""Custom SQLAlchemy Types for Postgres Features"""

import json
from typing import Any, Optional
from sqlalchemy import TypeDecorator, Text, String
from sqlalchemy.engine import Dialect


class Vector(TypeDecorator):
    """pgvector compatible vector type with SQLite fallback"""

    impl = Text
    cache_ok = True

    def __init__(self, dimension: int = 1536):
        super().__init__()
        self.dimension = dimension

    def load_dialect_impl(self, dialect: Dialect):
        """Use pgvector for Postgres, Text for others"""
        if dialect.name == 'postgresql':
            try:
                from pgvector.sqlalchemy import Vector as PGVector
                return dialect.type_descriptor(PGVector(self.dimension))
            except ImportError:
                # Fallback if pgvector not installed
                return dialect.type_descriptor(Text())
        return dialect.type_descriptor(Text())

    def process_bind_param(self, value: Optional[list], dialect: Dialect) -> Optional[Any]:
        """Convert list to appropriate format"""
        if value is None:
            return None
        if dialect.name == 'postgresql':
            # pgvector handles list directly
            return value
        # SQLite: store as JSON string
        return json.dumps(value)

    def process_result_value(self, value: Optional[Any], dialect: Dialect) -> Optional[list]:
        """Convert stored value back to list"""
        if value is None:
            return None
        if dialect.name == 'postgresql':
            # pgvector returns list directly
            if isinstance(value, list):
                return value
            # Sometimes returns string representation
            if isinstance(value, str):
                return json.loads(value.strip('[]').replace(' ', ','))
        # SQLite: parse JSON
        if isinstance(value, str):
            return json.loads(value)
        return value


class EncryptedStr(TypeDecorator):
    """Encrypted string type with automatic encrypt/decrypt"""

    impl = Text
    cache_ok = True

    def __init__(self, length: int = 500):
        super().__init__()
        self.length = length

    def load_dialect_impl(self, dialect: Dialect):
        return dialect.type_descriptor(Text())

    def process_bind_param(self, value: Optional[str], dialect: Dialect) -> Optional[str]:
        """Encrypt value before storing"""
        if value is None:
            return None
        from app.core.crypto import get_crypto
        return get_crypto().encrypt(value)

    def process_result_value(self, value: Optional[str], dialect: Dialect) -> Optional[str]:
        """Decrypt value after loading"""
        if value is None:
            return None
        from app.core.crypto import get_crypto
        try:
            return get_crypto().decrypt(value)
        except Exception:
            # If decryption fails, return as-is (for migration scenarios)
            return value


def JSONB():
    """JSONB type for Postgres with JSON fallback"""
    from sqlalchemy import JSON as SQLAlchemyJSON
    from sqlalchemy.dialects.postgresql import JSONB as PostgresJSONB

    class JSONBType(TypeDecorator):
        impl = SQLAlchemyJSON
        cache_ok = True

        def load_dialect_impl(self, dialect: Dialect):
            if dialect.name == 'postgresql':
                return dialect.type_descriptor(PostgresJSONB())
            return dialect.type_descriptor(SQLAlchemyJSON())

    return JSONBType
