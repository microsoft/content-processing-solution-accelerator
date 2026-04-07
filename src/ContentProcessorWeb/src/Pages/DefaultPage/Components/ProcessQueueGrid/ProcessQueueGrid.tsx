// Copyright (c) Microsoft Corporation.
// Licensed under the MIT License.

/**
 * Expandable data grid that displays claim batches as parent rows and their
 * processed documents as collapsible child rows. Supports selection, deletion,
 * and inline status/score rendering via {@link CustomCellRender}.
 */

import React, { useState, useEffect } from "react";
import {
    DocumentQueueAdd20Regular,
    DocumentPdfRegular,
    ImageRegular,
    ChevronDown20Regular,
    ChevronRight20Regular,
} from "@fluentui/react-icons";
import { Tooltip, Button } from "@fluentui/react-components";
import {
    TableBody, TableCell, TableRow, Table,
    TableHeader, TableHeaderCell, TableCellLayout, createTableColumn, useTableFeatures,
    useTableSelection, useTableSort, TableColumnId, 
    TableRowId
} from "@fluentui/react-components";

import { useDispatch, useSelector, shallowEqual } from "react-redux";
import { RootState, AppDispatch } from "../../../../store";
import {
    setSelectedGridRow,
    setSelectedClaim,
    deleteClaim,
    fetchContentTableData,
} from "../../../../store/slices/leftPanelSlice";

import { Confirmation } from "../../../../Components/DialogComponent/DialogComponent";
import CustomCellRender from "./CustomCellRender";
import {
    ClaimItem,
    ProcessedDocument,
    GridComponentProps,
} from "./ProcessQueueGridTypes";

import "./ProcessQueueGrid.styles.scss";

/** Internal state for a claim row including expansion and selection state. */
interface ClaimRowData {
    claim: ClaimItem;
    isExpanded: boolean;
    isSelected: boolean;
}

/**
 * Renders an expandable claims-and-documents grid with selection, status badges,
 * score indicators, and row-level delete actions.
 */
const ProcessQueueGrid: React.FC<GridComponentProps> = () => {
    const dispatch = useDispatch<AppDispatch>();
    const store = useSelector(
        (state: RootState) => ({
            gridData: state.leftPanel.gridData,
            processId: state.leftPanel.processId,
            deleteClaimsLoader: state.leftPanel.deleteClaimsLoader,
            pageSize: state.leftPanel.pageSize,
            gridLoader: state.leftPanel.gridLoader,
        }),
        shallowEqual
    );

    const [claims, setClaims] = useState<ClaimRowData[]>([]);
    const [selectedClaimId, setSelectedClaimId] = useState<string | null>(null);
    const [selectedDocumentId, setSelectedDocumentId] = useState<string | null>(null);

    const [isDialogOpen, setIsDialogOpen] = useState(false);
    const [selectedDeleteItem, setSelectedDeleteItem] = useState<{
        claimId: string;
        claimName: string;
    } | null>(null);

    const getFileIcon = (mimeType: string, fileName: string) => {
        const normalizedFileName = fileName.toLowerCase();
        if (mimeType === "application/pdf" || normalizedFileName.endsWith(".pdf")) {
            return <DocumentPdfRegular />;
        }
        if (mimeType.startsWith("image/") || /\.(png|jpe?g|gif|bmp|webp|tiff|svg)$/i.test(normalizedFileName)) {
            return <ImageRegular />;
        }
        return <DocumentQueueAdd20Regular />;
    };

    useEffect(() => {
        if (!store.gridLoader) {
            if (store.gridData.items && store.gridData.items.length > 0) {
                const claimRows: ClaimRowData[] = store.gridData.items.map((item: ClaimItem) => ({
                    claim: item,
                    isExpanded: false,
                    isSelected: false,
                }));
                setClaims((previousClaims) => {
                    const expandedClaimIds = new Set(
                        previousClaims
                            .filter((row) => row.isExpanded)
                            .map((row) => row.claim.id)
                    );

                    return claimRows.map((row) => ({
                        ...row,
                        isExpanded: expandedClaimIds.has(row.claim.id),
                    }));
                });

                // Preserve current selection on refresh, or auto-select first claim on initial load
                if (claimRows.length > 0) {
                    const currentClaim = selectedClaimId
                        ? claimRows.find(r => r.claim.id === selectedClaimId)
                        : null;

                    if (currentClaim) {
                        // Update selected claim with fresh data (status may have changed)
                        // Only dispatch if in claim mode (no document selected)
                        if (!selectedDocumentId) {
                            dispatch(setSelectedClaim({ claim: currentClaim.claim }));
                        }
                    } else {
                        // Auto-select first claim (initial load or selected claim no longer exists)
                        const firstClaim = claimRows[0].claim;
                        setSelectedClaimId(firstClaim.id);
                        setSelectedDocumentId(null);
                        dispatch(setSelectedClaim({ claim: firstClaim }));
                    }
                }
            } else {
                setClaims([]);
                dispatch(setSelectedGridRow({ processId: "", item: {} }));
            }
        }
    }, [store.gridData, store.gridLoader, dispatch]);

    const toggleExpand = (claimId: string) => {
        setClaims((prev) => {
            const targetRow = prev.find((row) => row.claim.id === claimId);
            const shouldExpandTarget = !(targetRow?.isExpanded ?? false);

            return prev.map((row) => ({
                ...row,
                isExpanded: row.claim.id === claimId ? shouldExpandTarget : false,
            }));
        });
    };

    const handleClaimClick = (claim: ClaimItem) => {
        if (selectedClaimId !== null && selectedClaimId !== claim.id) {
            setClaims((prev) =>
                prev.map((row) =>
                    row.isExpanded ? { ...row, isExpanded: false } : row
                )
            );
        }
        setSelectedClaimId(claim.id);
        setSelectedDocumentId(null);
        // Dispatch the claim selection
        dispatch(
            setSelectedClaim({
                claim: claim,
            })
        );
    };

    const handleDocumentClick = (document: ProcessedDocument, claimId: string) => {
        setSelectedClaimId(claimId);
        setSelectedDocumentId(document.process_id);
        dispatch(
            setSelectedGridRow({
                processId: document.process_id,
                item: document,
            })
        );
    };

    const isDeleteDisabled = (claimId: string, status: string) => {
        if (status !== "Completed" && status !== "Error")
            return { disabled: true, message: "In progress" };
        if (store.deleteClaimsLoader.includes(claimId))
            return { disabled: true, message: "Deleting" };
        return { disabled: false, message: "" };
    };

    const handleDelete = async () => {
        if (selectedDeleteItem) {
            try {
                toggleDialog();
                await dispatch(
                    deleteClaim({ claimId: selectedDeleteItem.claimId })
                ).unwrap();
                await dispatch(fetchContentTableData({ pageSize: store.pageSize, pageNumber: 1 })).unwrap();
            } catch (error) {
                console.error("Delete failed:", error);
            }
        }
    };

    const toggleDialog = () => {
        setIsDialogOpen(!isDialogOpen);
    };

    const dialogContent = () => {
        return <p>Are you sure you want to delete this claim and all its documents?</p>;
    };

    const formatDate = (dateString: string) => {
        const date = new Date(dateString);
        return `${(date.getMonth() + 1).toString().padStart(2, "0")}/${date
            .getDate()
            .toString()
            .padStart(2, "0")}/${date.getFullYear()}`;
    };

    return (
        <>
            <div className="gridContainer">
                <Table
                    noNativeElements={true}
                    size="medium"
                    aria-label="Claims table with expandable rows"
                    className="gridTable"
                >
                    <TableHeader>
                        <TableRow aria-rowindex={1}>
                            <TableHeaderCell className="col colExpand"></TableHeaderCell>
                            <TableHeaderCell className="col col1">
                                File name
                            </TableHeaderCell>
                            <TableHeaderCell className="col col2">
                                Imported
                            </TableHeaderCell>
                            <TableHeaderCell className="col col3">
                                Status
                            </TableHeaderCell>
                            <TableHeaderCell className="col col4">
                                Process time
                            </TableHeaderCell>
                            <TableHeaderCell className="col col5">
                                Entity score
                            </TableHeaderCell>
                            <TableHeaderCell className="col col6">
                                Schema score
                            </TableHeaderCell>
                            <TableHeaderCell className="col col7">
                            </TableHeaderCell>
                        </TableRow>
                    </TableHeader>
                    <TableBody className="gridTableBody">
                        <div className="GridList">
                            {claims.length > 0 ? (
                                claims.map((claimRow) => (
                                    <React.Fragment key={claimRow.claim.id}>
                                        {/* Claim Row */}
                                        <TableRow
                                            className={`claimRow ${
                                                selectedClaimId === claimRow.claim.id
                                                    ? "selectedRow"
                                                    : ""
                                            }`}
                                            onClick={() => handleClaimClick(claimRow.claim)}
                                        >
                                            <TableCell className="col colExpand">
                                                <Button
                                                    appearance="subtle"
                                                    size="small"
                                                    icon={
                                                        claimRow.isExpanded ? (
                                                            <ChevronDown20Regular />
                                                        ) : (
                                                            <ChevronRight20Regular />
                                                        )
                                                    }
                                                    onClick={(e) => {
                                                        e.stopPropagation();
                                                        toggleExpand(claimRow.claim.id);
                                                    }}
                                                />
                                            </TableCell>
                                            <TableCell className="col col1">
                                                <Tooltip
                                                    content={claimRow.claim.process_name}
                                                    relationship="label"
                                                >
                                                    <TableCellLayout truncate>
                                                        {claimRow.claim.process_name}
                                                    </TableCellLayout>
                                                </Tooltip>
                                            </TableCell>
                                            <TableCell className="col col2">
                                                <div className="columnCotainer centerAlign">
                                                    {formatDate(claimRow.claim.process_time)}
                                                </div>
                                            </TableCell>
                                            <TableCell className="col col3">
                                                <CustomCellRender
                                                    type="roundedButton"
                                                    props={{ txt: claimRow.claim.status }}
                                                />
                                            </TableCell>
                                            <TableCell className="col col4">
                                                <CustomCellRender
                                                    type="processTime"
                                                    props={{
                                                        timeString: claimRow.claim.processed_time,
                                                    }}
                                                />
                                            </TableCell>
                                            <TableCell className="col col5">
                                                {/* Empty for claim rows */}
                                            </TableCell>
                                            <TableCell className="col col6">
                                                {/* Empty for claim rows */}
                                            </TableCell>
                                            <TableCell className="col col7">
                                                <CustomCellRender
                                                    type="deleteButton"
                                                    props={{
                                                        item: {
                                                            processId: { label: claimRow.claim.id },
                                                        },
                                                        deleteBtnStatus: isDeleteDisabled(
                                                            claimRow.claim.id,
                                                            claimRow.claim.status
                                                        ),
                                                        setSelectedDeleteItem: () =>
                                                            setSelectedDeleteItem({
                                                                claimId: claimRow.claim.id,
                                                                claimName: claimRow.claim.process_name,
                                                            }),
                                                        toggleDialog,
                                                    }}
                                                />
                                            </TableCell>
                                        </TableRow>

                                        {/* Document Rows (expanded) */}
                                        {claimRow.isExpanded &&
                                            claimRow.claim.processed_documents?.map((doc) => (
                                                <TableRow
                                                    key={doc.process_id}
                                                    className={`documentRow ${
                                                        selectedDocumentId === doc.process_id
                                                            ? "selectedDocRow"
                                                            : ""
                                                    }`}
                                                    onClick={() =>
                                                        handleDocumentClick(doc, claimRow.claim.id)
                                                    }
                                                >
                                                    <TableCell className="col colExpand"></TableCell>
                                                    <TableCell className="col col1">
                                                        <Tooltip
                                                            content={doc.file_name}
                                                            relationship="label"
                                                        >
                                                            <TableCellLayout
                                                                truncate
                                                                media={getFileIcon(doc.mime_type || "", doc.file_name)}
                                                                style={{ paddingLeft: '8px' }}
                                                            >
                                                                {doc.file_name}
                                                            </TableCellLayout>
                                                        </Tooltip>
                                                    </TableCell>
                                                    <TableCell className="col col2">
                                                        {/* Empty for document rows - imported date is on claim */}
                                                    </TableCell>
                                                    <TableCell className="col col3">
                                                        <CustomCellRender
                                                            type="roundedButton"
                                                            props={{ txt: doc.status }}
                                                        />
                                                    </TableCell>
                                                    <TableCell className="col col4">
                                                        <CustomCellRender
                                                            type="processTime"
                                                            props={{ timeString: doc.processed_time }}
                                                        />
                                                    </TableCell>
                                                    <TableCell className="col col5">
                                                        <CustomCellRender
                                                            type="percentage"
                                                            props={{
                                                                valueText: doc.entity_score.toString(),
                                                                status: doc.status,
                                                            }}
                                                        />
                                                    </TableCell>
                                                    <TableCell className="col col6">
                                                        <CustomCellRender
                                                            type="percentage"
                                                            props={{
                                                                valueText: doc.schema_score.toString(),
                                                                status: doc.status,
                                                            }}
                                                        />
                                                    </TableCell>
                                                    <TableCell className="col col7">
                                                        {/* Empty for document rows - no delete */}
                                                    </TableCell>
                                                </TableRow>
                                            ))}
                                    </React.Fragment>
                                ))
                            ) : (
                                <p style={{ textAlign: "center" }}>No data available</p>
                            )}
                        </div>
                    </TableBody>
                </Table>
            </div>

            <Confirmation
                title="Delete Confirmation"
                content={dialogContent()}
                isDialogOpen={isDialogOpen}
                onDialogClose={toggleDialog}
                footerButtons={[
                    {
                        text: "Confirm",
                        appearance: "primary",
                        onClick: handleDelete,
                    },
                    {
                        text: "Cancel",
                        appearance: "secondary",
                        onClick: toggleDialog,
                    },
                ]}
            />
        </>
    );
};

export default ProcessQueueGrid;