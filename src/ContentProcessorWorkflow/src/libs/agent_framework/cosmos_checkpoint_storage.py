# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""Cosmos DB SQL API adapter for Agent Framework workflow checkpoints.

This module bridges the ``agent_framework.CheckpointStorage`` interface to
Azure Cosmos DB via the ``sas.cosmosdb.sql`` repository layer.  It provides
three collaborating classes:

1. ``CosmosWorkflowCheckpoint`` — Cosmos DB document model that wraps
   ``WorkflowCheckpoint`` with a partition-key–aware ``RootEntityBase``.
2. ``CosmosWorkflowCheckpointRepository`` — CRUD repository with convenience
   methods for save / load / list / delete operations.
3. ``CosmosCheckpointStorage`` — Adapter that implements the SDK’s
   ``CheckpointStorage`` protocol, delegating to the repository.

Storage layout:
    - Each checkpoint is stored as a single Cosmos DB item keyed by
      ``checkpoint_id`` (mapped to the document ``id``).
    - ``workflow_id`` enables filtered queries to list checkpoints for a
      specific workflow run.

Usage:
    .. code-block:: python

        repo = CosmosWorkflowCheckpointRepository(
            account_url="https://...",
            database_name="workflows",
            container_name="checkpoints",
        )
        storage = CosmosCheckpointStorage(repository=repo)
        await storage.save_checkpoint(checkpoint)
"""

from typing import Any

from agent_framework import CheckpointStorage, WorkflowCheckpoint
from sas.cosmosdb.sql import RepositoryBase, RootEntityBase


class CosmosWorkflowCheckpoint(RootEntityBase[WorkflowCheckpoint, str]):
    """Cosmos DB wrapper for WorkflowCheckpoint with partition key support."""

    checkpoint_id: str
    workflow_id: str = ""
    timestamp: str = ""

    # Core workflow state
    messages: dict[str, list[dict[str, Any]]] = {}
    shared_state: dict[str, Any] = {}
    pending_request_info_events: dict[str, dict[str, Any]] = {}

    # Runtime state
    iteration_count: int = 0

    # Metadata
    metadata: dict[str, Any] = {}
    version: str = "1.0"

    def __init__(self, **data):
        # Add id field from checkpoint_id before passing to parent
        if "id" not in data and "checkpoint_id" in data:
            data["id"] = data["checkpoint_id"]
        super().__init__(**data)


class CosmosWorkflowCheckpointRepository(RepositoryBase[CosmosWorkflowCheckpoint, str]):
    """CRUD repository for ``CosmosWorkflowCheckpoint`` documents.

    Wraps ``sas.cosmosdb.sql.RepositoryBase`` with domain-specific convenience
    methods that hide the generic ``add_async`` / ``get_async`` / ``all_async``
    surface behind checkpoint-oriented names.
    """

    def __init__(
        self, account_url: str, database_name: str, container_name: str
    ) -> None:
        """Connect to a Cosmos DB SQL container.

        Args:
            account_url: Cosmos DB account endpoint (e.g. ``https://<name>.documents.azure.com:443/``).
            database_name: Target database within the account.
            container_name: Container that holds checkpoint documents.
        """
        super().__init__(
            account_url=account_url,
            database_name=database_name,
            container_name=container_name,
        )

    async def save_checkpoint(self, checkpoint: CosmosWorkflowCheckpoint) -> None:
        """Persist a checkpoint document (upsert semantics).

        Args:
            checkpoint: The checkpoint to save.  Its ``id`` (derived from
                ``checkpoint_id``) is used as the document key.
        """
        await self.add_async(checkpoint)

    async def load_checkpoint(self, checkpoint_id: str) -> CosmosWorkflowCheckpoint:
        """Load a single checkpoint by its unique ID.

        Args:
            checkpoint_id: Document key to retrieve.

        Returns:
            The deserialized ``CosmosWorkflowCheckpoint``.

        Raises:
            Exception: If the document does not exist.
        """
        cosmos_checkpoint = await self.get_async(checkpoint_id)
        return cosmos_checkpoint

    async def list_checkpoint_ids(self, workflow_id: str | None = None) -> list[str]:
        """List checkpoint document IDs, optionally filtered by workflow.

        Args:
            workflow_id: If provided, only return checkpoints belonging to
                this workflow.  If ``None``, return all checkpoint IDs.

        Returns:
            List of checkpoint ID strings.
        """
        if workflow_id is None:
            query = await self.all_async()
        else:
            query = await self.find_one_async({"workflow_id": workflow_id})
            # f"SELECT c.id FROM c WHERE c.entity.workflow_id = '{workflow_id}'"

        return [checkpoint_id["id"] for checkpoint_id in query]

    async def list_checkpoints(
        self, workflow_id: str | None = None
    ) -> list[WorkflowCheckpoint]:
        """Load full checkpoint objects, optionally filtered by workflow.

        Args:
            workflow_id: If provided, only return checkpoints for this workflow.

        Returns:
            List of deserialized ``WorkflowCheckpoint`` instances.
        """
        if workflow_id is None:
            query = await self.all_async()
        else:
            query = await self.find_one_async({"workflow_id": workflow_id})

        return [checkpoint for checkpoint in query]

    async def delete_checkpoint(self, checkpoint_id: str) -> None:
        """Remove a checkpoint document by ID.

        Args:
            checkpoint_id: Document key to delete.
        """
        await self.delete_async(key=checkpoint_id)


class CosmosCheckpointStorage(CheckpointStorage):
    """Adapter that implements ``CheckpointStorage`` using Cosmos DB.

    This class satisfies the ``agent_framework.CheckpointStorage`` protocol by
    delegating every operation to a ``CosmosWorkflowCheckpointRepository``.
    It handles the conversion between the SDK’s ``WorkflowCheckpoint`` and the
    Cosmos-specific ``CosmosWorkflowCheckpoint`` document model.

    Lifecycle:
        1. Caller creates a ``CosmosWorkflowCheckpointRepository`` (binds to a
           specific Cosmos DB container).
        2. Caller wraps it in ``CosmosCheckpointStorage``.
        3. The storage is injected into Agent Framework workflows that require
           checkpoint persistence.
    """

    def __init__(self, repository: CosmosWorkflowCheckpointRepository) -> None:
        """Bind the adapter to a Cosmos DB checkpoint repository.

        Args:
            repository: The CRUD repository that performs actual Cosmos DB I/O.
        """
        self.repository = repository

    async def save_checkpoint(self, checkpoint: WorkflowCheckpoint) -> None:
        """Convert a ``WorkflowCheckpoint`` to a Cosmos document and persist it.

        Args:
            checkpoint: The SDK checkpoint to save.
        """
        cosmos_checkpoint = CosmosWorkflowCheckpoint(**checkpoint.to_dict())
        await self.repository.save_checkpoint(cosmos_checkpoint)

    async def load_checkpoint(self, checkpoint_id: str) -> WorkflowCheckpoint:
        """Load a checkpoint by ID and return it as a ``WorkflowCheckpoint``.

        Args:
            checkpoint_id: The unique checkpoint identifier.

        Returns:
            The deserialized checkpoint (``CosmosWorkflowCheckpoint`` is a
            ``WorkflowCheckpoint`` subtype, so it satisfies the return type).
        """
        cosmos_checkpoint = await self.repository.load_checkpoint(checkpoint_id)
        return cosmos_checkpoint

    async def list_checkpoint_ids(self, workflow_id: str | None = None) -> list[str]:
        """List checkpoint IDs, optionally scoped to a workflow.

        Args:
            workflow_id: Optional filter.

        Returns:
            List of checkpoint ID strings.
        """
        return await self.repository.list_checkpoint_ids(workflow_id)

    async def list_checkpoints(
        self, workflow_id: str | None = None
    ) -> list[WorkflowCheckpoint]:
        """Load full checkpoint objects, optionally scoped to a workflow.

        Args:
            workflow_id: Optional filter.

        Returns:
            List of ``WorkflowCheckpoint`` instances.
        """
        return await self.repository.list_checkpoints(workflow_id)

    async def delete_checkpoint(self, checkpoint_id: str) -> None:
        """Delete a checkpoint by ID.

        Args:
            checkpoint_id: The unique checkpoint identifier to remove.
        """
        await self.repository.delete_checkpoint(checkpoint_id)
