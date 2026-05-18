# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""
Cosmos DB (MongoDB API) repository for claim-process workflow state.

This module provides ``Claim_Processes``, a typed repository built on
``RepositoryBase`` that persists ``Claim_Process`` documents and offers
high-level operations for each workflow stage: document ingestion,
summarisation, gap analysis, and status tracking.

Every write method follows a read-modify-write pattern — fetch the
document by ``process_id``, mutate the relevant field(s), then call
``update_async``.  All I/O is ``async``.
"""

from sas.cosmosdb.mongo.repository import RepositoryBase

from repositories.model.claim_process import Claim_Process, Claim_Steps, Content_Process


class Claim_Processes(RepositoryBase[Claim_Process, str]):
    """
    Async CRUD repository for ``Claim_Process`` documents.

    Extends ``RepositoryBase[Claim_Process, str]`` to add domain-specific
    helpers for the content-processing workflow.  The collection is
    indexed on ``id``, ``process_name``, and ``process_time`` for
    efficient querying from both the queue consumer and the API layer.
    """

    def __init__(self, connection_string: str, database_name: str, container_name: str):
        """
        Connect to the backing Cosmos DB collection.

        Args:
            connection_string: MongoDB-compatible connection string for
                the Cosmos DB account.
            database_name:     Name of the target database.
            container_name:    Name of the collection (container) that
                stores ``Claim_Process`` documents.
        """
        super().__init__(
            connection_string,
            database_name,
            container_name,
            indexes=["id", "process_name", "process_time"],
        )

    async def Create_Claim_Process(self, claim_process: Claim_Process) -> Claim_Process:
        """Create (or replace) a ``Claim_Process`` document.

        If a document with the same ``id`` already exists it is deleted
        first, so the call is effectively an *upsert-by-replacement*.

        Args:
            claim_process: The entity to persist.

        Returns:
            The persisted ``Claim_Process`` entity.
        """
        existing_process = await self.get_async(claim_process.id)
        if existing_process:
            await self.delete_async(claim_process.id)

        await self.add_async(claim_process)
        return claim_process

    async def Upsert_Content_Process(
        self, process_id: str, content_process: Content_Process
    ) -> Claim_Process | None:
        """Append or replace a ``Content_Process`` inside a claim.

        Steps:
            1. Fetch the parent ``Claim_Process`` by *process_id*.
            2. If a ``Content_Process`` with the same ``file_name`` and
               ``process_id`` already exists in ``processed_documents``,
               remove it (replace semantics).
            3. Append the new *content_process* and persist.

        Args:
            process_id:      ID of the parent ``Claim_Process``.
            content_process: The document-level result to upsert.

        Returns:
            The updated ``Claim_Process``, or ``None`` if *process_id*
            was not found.
        """
        claim_process = await self.get_async(process_id)
        if claim_process:
            existing_process = next(
                (
                    cp
                    for cp in claim_process.processed_documents
                    if cp.file_name == content_process.file_name
                    and cp.process_id == content_process.process_id
                ),
                None,
            )
            if existing_process:
                claim_process.processed_documents.remove(existing_process)

            claim_process.processed_documents.append(content_process)
            await self.update_async(claim_process)
            return claim_process

        return None

    async def Get_Claim_Process_By_Id(self, process_id: str) -> Claim_Process | None:
        """Retrieve a ``Claim_Process`` by its unique identifier.

        Args:
            process_id: The document ``id``.

        Returns:
            The matching entity, or ``None`` if not found.
        """
        return await self.get_async(process_id)

    async def Update_Claim_Content_Process_Status(
        self, process_id: str, new_content_process_collection: list[Content_Process]
    ) -> Claim_Process | None:
        """Replace the entire ``processed_documents`` list on a claim.

        This is used when the caller has already built the updated
        collection (e.g. after bulk status changes) and wants to persist
        it in a single write.

        Args:
            process_id: ID of the parent ``Claim_Process``.
            new_content_process_collection:
                The replacement list of ``Content_Process`` entries.

        Returns:
            The updated ``Claim_Process``, or ``None`` if *process_id*
            was not found.
        """
        claim_process = await self.get_async(process_id)
        if claim_process:
            claim_process.processed_documents = new_content_process_collection
            await self.update_async(claim_process)
            return claim_process

        return None

    async def Update_Claim_Process(self, claim_process: Claim_Process) -> Claim_Process:
        """Persist an already-modified ``Claim_Process`` entity.

        Args:
            claim_process: The entity with updated fields.

        Returns:
            The same entity after a successful write.
        """
        await self.update_async(claim_process)
        return claim_process

    async def Update_Claim_Process_Summary(
        self, process_id: str, new_summary: str
    ) -> Claim_Process | None:
        """Set the ``process_summary`` field on a claim.

        Args:
            process_id:  ID of the target ``Claim_Process``.
            new_summary: Replacement summary text.

        Returns:
            The updated entity, or ``None`` if not found.
        """
        claim_process = await self.get_async(process_id)
        if claim_process:
            claim_process.process_summary = new_summary
            await self.update_async(claim_process)
            return claim_process
        return None

    async def Update_Claim_Process_Gaps(
        self, process_id: str, new_gaps: str
    ) -> Claim_Process | None:
        """Set the ``process_gaps`` field on a claim.

        Args:
            process_id: ID of the target ``Claim_Process``.
            new_gaps:   Replacement gap-analysis text.

        Returns:
            The updated entity, or ``None`` if not found.
        """
        claim_process = await self.get_async(process_id)
        if claim_process:
            claim_process.process_gaps = new_gaps
            await self.update_async(claim_process)
            return claim_process
        return None

    async def Update_Claim_Process_Comment(
        self, process_id: str, new_comment: str
    ) -> Claim_Process | None:
        """Set the ``process_comment`` field on a claim.

        Args:
            process_id:  ID of the target ``Claim_Process``.
            new_comment: Replacement specialist comment text.

        Returns:
            The updated entity, or ``None`` if not found.
        """
        claim_process = await self.get_async(process_id)
        if claim_process:
            claim_process.process_comment = new_comment
            await self.update_async(claim_process)
            return claim_process
        return None

    async def Update_Claim_Process_Status(
        self, process_id: str, new_status: Claim_Steps
    ) -> Claim_Process | None:
        """Advance (or reset) the workflow ``status`` on a claim.

        Args:
            process_id: ID of the target ``Claim_Process``.
            new_status: The ``Claim_Steps`` enum value to set.

        Returns:
            The updated entity, or ``None`` if not found.
        """
        claim_process = await self.get_async(process_id)
        if claim_process:
            claim_process.status = new_status
            await self.update_async(claim_process)
            return claim_process
        return None

    async def Delete_Claim_Process(self, process_id: str) -> None:
        """Remove a ``Claim_Process`` document from the collection.

        Args:
            process_id: ID of the document to delete.
        """
        await self.delete_async(process_id)
