# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""PyMongo-based helper for Azure Cosmos DB (Mongo API) CRUD operations.

Used by router logic classes to persist and query documents such as
schemas, schema sets, content processes, and claim batches.
"""

import warnings
from typing import Any, Dict, List, Optional

import certifi
from pymongo import MongoClient
from pymongo.database import Collection, Database


class CosmosMongDBHelper:
    """Thin CRUD wrapper around a single Cosmos DB (Mongo API) collection.

    Responsibilities:
        1. Open a PyMongo connection with TLS via the certifi CA bundle.
        2. Auto-create the target collection and optional indexes.
        3. Expose insert, find, count, update, and delete operations.

    Attributes:
        connection_string: Cosmos DB Mongo connection string.
        client: Active PyMongo MongoClient.
        db: Target database handle.
        container: Target collection handle.
    """

    def __init__(
        self,
        connection_string: str,
        db_name: str,
        container_name: str,
        indexes: list = None,
    ):
        self.connection_string = connection_string
        self.client: MongoClient = None
        self.container: Collection = None
        self.db: Database = None

        self.client, self.db, self.container = self._prepare(
            connection_string, db_name, container_name, indexes
        )

    def _prepare(
        self,
        connection_string: str,
        db_name: str,
        container_name: str,
        indexes: list = None,
    ):
        """Connect to Cosmos DB and ensure the collection and indexes exist.

        Args:
            connection_string: Cosmos DB Mongo connection string.
            db_name: Database name.
            container_name: Collection name (created if absent).
            indexes: Optional list of ``(field, order)`` tuples to index.

        Returns:
            Tuple of (MongoClient, Database, Collection).
        """
        # Cosmos DB for MongoDB triggers a PyMongo supportability warning that
        # is noisy but harmless; suppress it during client creation.
        with warnings.catch_warnings():
            warnings.filterwarnings(
                "ignore",
                message=r"You appear to be connected to a CosmosDB cluster\..*",
                category=UserWarning,
            )
            # certifi CA bundle is required inside containers that lack system certs.
            mongoClient = MongoClient(connection_string, tlsCAFile=certifi.where())
        database = mongoClient[db_name]
        container = self._create_container(database, container_name)
        if indexes:
            self._create_indexes(container, indexes)

        return mongoClient, database, container

    def _create_container(self, database: Database, container_name: str) -> Collection:
        """Return the named collection, creating it if it does not exist."""
        if container_name not in database.list_collection_names():
            database.create_collection(container_name)
        return database[container_name]

    def _create_indexes(self, container, fields):
        """Create single-field indexes for any that do not already exist."""
        existing_indexes = container.index_information()
        for field, order in fields:
            if f"{field}_{order}" not in existing_indexes:
                container.create_index([(field, order)])

    def insert_document(self, document: Dict[str, Any]):
        """Insert a single document and return the insert result."""
        result = self.container.insert_one(document)
        return result

    def find_document(
        self,
        query: Dict[str, Any],
        sort_fields: Optional[List[tuple]] = None,
        skip: int = 0,
        limit: int = 0,
        projection: Optional[List[str]] = None,
    ):
        """Query documents with optional sort, pagination, and projection."""
        cursor = self.container.find(query, projection)
        if sort_fields:
            cursor = cursor.sort(sort_fields)
        if skip:
            cursor = cursor.skip(skip)
        if limit:
            cursor = cursor.limit(limit)
        items = list(cursor)
        return items

    def count_documents(self, query: Dict[str, Any] = None) -> int:
        """Return the number of documents matching *query* (all if None)."""
        if query is None:
            query = {}
        return self.container.count_documents(query)

    def update_document(self, item_id: str, update: Dict[str, Any]):
        """Update the document whose ``Id`` matches *item_id*."""
        result = self.container.update_one({"Id": item_id}, {"$set": update})
        return result

    def update_document_by_query(self, query: Dict[str, Any], update: Dict[str, Any]):
        """Update the first document matching *query*."""
        result = self.container.update_one(query, {"$set": update})
        return result

    def delete_document(self, item_id: str, field_name: str = None):
        """Delete the document identified by *item_id* on *field_name* (default ``Id``)."""
        field_name = field_name or "Id"  # Use "Id" if field_name is empty or None
        result = self.container.delete_one({field_name: item_id})
        return result
