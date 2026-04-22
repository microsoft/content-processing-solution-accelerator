// Copyright (c) Microsoft Corporation.
// Licensed under the MIT License.

/**
 * Type definitions for the ProcessQueueGrid component and its related
 * data structures (claims, documents, grid rows).
 */

import type { JSX } from "react";
import { TableRowData as RowStateBase } from "@fluentui/react-components";

/** A single processed document within a claim batch. */
export interface ProcessedDocument {
    /** Unique process identifier. */
    readonly process_id: string;
    /** Original uploaded file name. */
    readonly file_name: string;
    /** MIME type of the document. */
    readonly mime_type: string;
    /** Entity extraction confidence score (0–1). */
    readonly entity_score: number;
    /** Schema compliance score (0–1). */
    readonly schema_score: number;
    /** Current processing status. */
    readonly status: string;
    /** Duration string for processing time (HH:MM:SS). */
    readonly processed_time: string;
}

/** A claim batch returned from the API. */
export interface ClaimItem {
    /** Unique claim identifier. */
    readonly id: string;
    /** Display name of the claim batch. */
    readonly process_name: string;
    /** Associated schema set ID. */
    readonly schemaset_id: string;
    /** Optional metadata ID. */
    readonly metadata_id: string | null;
    /** List of documents processed within this claim. */
    readonly processed_documents: ProcessedDocument[];
    /** Current processing status of the claim. */
    readonly status: string;
    /** AI-generated summary of the claim. */
    readonly process_summary: string;
    /** AI-identified gaps in the claim. */
    readonly process_gaps: string;
    /** User-supplied comment on the claim. */
    readonly process_comment: string;
    /** Timestamp when processing was initiated. */
    readonly process_time: string;
    /** Timestamp when processing completed. */
    readonly processed_time: string;
}

/** Grid row item representing a claim (parent row). */
export interface ClaimRowItem {
    claimId: { label: string };
    processName: { label: string };
    status: { label: string };
    processTime: { label: string };
    processedTime: { label: string };
    documentCount: { label: string };
    documents: ProcessedDocument[];
}

/** Grid row item representing a document (child row). */
export interface DocumentRowItem {
    fileName: { label: string; icon: JSX.Element };
    mimeType: { label: string };
    status: { label: string };
    processTime: { label: string };
    entityScore: { label: string };
    schemaScore: { label: string };
    processId: { label: string };
}

/** @deprecated Legacy row item interface kept for backward compatibility. */
export interface Item {
    fileName: { label: string; icon: JSX.Element };
    imported: { label: string };
    status: { label: string };
    processTime: { label: string };
    entityScore: { label: string };
    schemaScore: { label: string };
    processId: { label: string };
    lastModifiedBy: { label: string };
    file_mime_type: { label: string };
}

export interface TableRowData extends RowStateBase<Item> {
    onClick: (e: React.MouseEvent) => void;
    onKeyDown: (e: React.KeyboardEvent) => void;
    selected: boolean;
    appearance: "brand" | "none";
}

/** Props for the {@link ProcessQueueGrid} component. */
export type GridComponentProps = Record<string, never>;
