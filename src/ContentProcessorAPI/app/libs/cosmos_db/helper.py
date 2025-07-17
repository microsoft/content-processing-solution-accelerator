# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

from typing import Any, Dict, List, Optional

import certifi
from pymongo import MongoClient
from pymongo.database import Collection, Database


class CosmosMongDBHelper:
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
        """
        Prepare the MongoDB connection and create the container if it doesn't exist.

        Args:
            connection_string (str): Connection String for MongoDB
            db_name (str): Database Name
            container_name (str): Collection Name to be created or used
            indexes (list, optional): Adding Fields to be get indexed for searching and ordering. Defaults to None.

        Returns:
            tuple: MongoClient, Database, Collection
        """
        # MongoClient need to get Certificate but in Container,
        # it doesn't have native certificate so we need to add it othwerwise the connection will be fail
        mongoClient = MongoClient(connection_string, tlsCAFile=certifi.where())
        database = mongoClient[db_name]
        container = self._create_container(database, container_name)
        # Add Indexes
        if indexes:
            self._create_indexes(container, indexes)
        # self._create_indexes(container, ["ClassName", "Id"])

        return mongoClient, database, container

    def _create_container(self, database: Database, container_name: str) -> Collection:
        if container_name not in database.list_collection_names():
            database.create_collection(container_name)
        return database[container_name]

    def _create_indexes(self, container, fields):
        existing_indexes = container.index_information()
        for field, order in fields:
            if f"{field}_{order}" not in existing_indexes:
                container.create_index([(field, order)])

    def insert_document(self, document: Dict[str, Any]):
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
        if query is None:
            query = {}
        return self.container.count_documents(query)

    def update_document(self, item_id: str, update: Dict[str, Any]):
        result = self.container.update_one({"Id": item_id}, {"$set": update})
        return result

    def update_document_by_query(self, query: Dict[str, Any], update: Dict[str, Any]):
        result = self.container.update_one(query, {"$set": update})
        return result

    def delete_document(self, item_id: str, field_name: str = None):
        field_name = field_name or "Id"  # Use "Id" if field_name is empty or None
        result = self.container.delete_one({field_name: item_id})
        return result
