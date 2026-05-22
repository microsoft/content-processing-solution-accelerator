// Copyright (c) Microsoft Corporation.
// Licensed under the MIT License.

/**
 * Redux slice for the left panel: schema selection, process grid data,
 * file upload, delete operations, and Swagger JSON fetching.
 */
import { createSlice, createAsyncThunk, PayloadAction } from '@reduxjs/toolkit';

import httpUtility, { handleApiThunk } from '../../Services/httpUtility';
import { toast } from "react-toastify";

export interface LeftPanelState {
    schemaData: Record<string, unknown>[];
    schemaSetData: Record<string, unknown>[];
    schemaError: string | null;
    schemaLoader: boolean;
    schemaSelectedOption: Record<string, unknown>;
    gridData: GridData;
    gridLoader: boolean;
    processId: string | null;
    selectedItem: Record<string, unknown>;
    selectedClaim: Record<string, unknown> | null;
    selectionType: 'claim' | 'document' | null;
    pageSize: number;
    deleteFilesLoader: string[];
    deleteClaimsLoader: string[];
    isGridRefresh: boolean;
    swaggerJSON: Record<string, unknown> | null;
    refreshTrigger: number;
}

interface GridData {
    total_count: number;
    total_pages: number;
    current_page: number;
    page_size: number;
    items: Record<string, unknown>[];
}

interface UploadMetadata {
    Claim_Id: string;
    Schema_Id: string;
    Metadata_Id: string;
}

export interface CreateBatchResponse {
    readonly claim_id: string;
}

interface DeleteApiResponse {
    process_id: string;
    status: string;
    message: string;
}


export const fetchSwaggerData = createAsyncThunk<Record<string, unknown>, void>(
    '/openapi',
    async (_, { rejectWithValue }) => {
        return handleApiThunk(
            httpUtility.get<Record<string, unknown>>('/openapi.json'),
            rejectWithValue,
            'Failed to fetch Swagger data',
            '/openapi.json'
        );
    }
);

export const fetchSchemaData = createAsyncThunk<Record<string, unknown>[], void>(
    '/schemavault',
    async (_, { rejectWithValue }) => {
        return handleApiThunk(
            httpUtility.get<Record<string, unknown>[]>('/schemavault/'),
            rejectWithValue,
            'Failed to fetch schema',
            '/schemavault/'
        );
    }
);

export const fetchSchemasetData = createAsyncThunk<Record<string, unknown>[], void>(
    '/schemasetvault',
    async (_, { rejectWithValue }) => {
        return handleApiThunk(
            httpUtility.get<Record<string, unknown>[]>('/schemasetvault/'),
            rejectWithValue,
            'Failed to fetch schema set',
            '/schemasetvault/'
        );
    }
);

export const fetchSchemasBySchemaSet = createAsyncThunk<
    Record<string, unknown>[],
    { schemaSetId: string }
>(
    '/schemasetvault/schemas',
    async ({ schemaSetId }, { rejectWithValue }) => {
        const url = `/schemasetvault/${schemaSetId}/schemas`;
        return handleApiThunk(
            httpUtility.get<Record<string, unknown>[]>(url),
            rejectWithValue,
            'Failed to fetch schemas for schema set',
            url
        );
    }
);

export const fetchContentTableData = createAsyncThunk<
    GridData,
    { pageSize: number; pageNumber: number }
>(
    '/claimprocessor/claims/processed',
    async ({ pageSize, pageNumber }, { rejectWithValue }) => {
        return handleApiThunk(
            httpUtility.post<GridData>('/claimprocessor/claims/processed', {
                page_size: pageSize,
                page_number: pageNumber,
            }),
            rejectWithValue,
            'Failed to fetch content data.',
            'claimprocessor/claims/processed'
        );
    }
);

export const deleteProcessedFile = createAsyncThunk<DeleteApiResponse, { processId: string | null }>(
    '/contentprocessor/deleteProcessedFile/',
    async ({ processId }, { rejectWithValue }) => {
        if (!processId) {
            return rejectWithValue('Reset store');
        }

        const url = '/contentprocessor/processed/' + processId;
        return handleApiThunk(
            httpUtility.delete<DeleteApiResponse>(url),
            rejectWithValue,
            'Failed to delete processed file',
            '/contentprocessor/deleteProcessedFile/'
        );
    }
);

export const deleteClaim = createAsyncThunk<DeleteApiResponse, { claimId: string | null }>(
    '/claimprocessor/deleteClaim/',
    async ({ claimId }, { rejectWithValue }) => {
        if (!claimId) {
            return rejectWithValue('Claim ID is required');
        }

        const url = `/claimprocessor/claims/${claimId}`;
        return handleApiThunk(
            httpUtility.delete<DeleteApiResponse>(url),
            rejectWithValue,
            'Failed to delete claim',
            url
        );
    }
);


export const createBatch = createAsyncThunk<
    CreateBatchResponse,
    { schemaCollectionId: string }
>(
    '/claimprocessor/claims/createBatch',
    async ({ schemaCollectionId }, { rejectWithValue }) => {
        return handleApiThunk(
            httpUtility.put<CreateBatchResponse>('/claimprocessor/claims', {
                schema_collection_id: schemaCollectionId,
            }),
            rejectWithValue,
            'Failed to create batch',
            '/claimprocessor/claims'
        );
    }
);

export const uploadFile = createAsyncThunk<
    Record<string, unknown>,
    { file: File; claimId: string; schemaId: string }
>(
    '/claimprocessor/claims/files',
    async ({ file, claimId, schemaId }, { rejectWithValue }) => {
        const url = `/claimprocessor/claims/${claimId}/files`;

        const metadata: UploadMetadata = {
            Claim_Id: claimId,
            Schema_Id: schemaId,
            Metadata_Id: crypto.randomUUID(),
        };

        const formData = new FormData();
        formData.append('file', file);
        formData.append('data', JSON.stringify(metadata));

        return handleApiThunk(
            httpUtility.upload<Record<string, unknown>>(url, formData),
            rejectWithValue,
            'Failed to import file',
            url
        );
    }
);

export const submitBatchClaim = createAsyncThunk<
    Record<string, unknown>,
    { claimProcessId: string }
>(
    '/claimprocessor/claims/submit',
    async ({ claimProcessId }, { rejectWithValue }) => {
        return handleApiThunk(
            httpUtility.post<Record<string, unknown>>('/claimprocessor/claims', {
                claim_process_id: claimProcessId,
            }),
            rejectWithValue,
            'Failed to submit batch claim',
            '/claimprocessor/claims'
        );
    }
);

const gridDefaultVal: GridData = {
    total_count: 0, total_pages: 0, current_page: 1, page_size: 500,
    items: []
};


const initialState: LeftPanelState = {
    schemaData: [],
    schemaSetData: [],
    schemaSelectedOption: {},
    schemaLoader: false,
    schemaError: null,

    gridData: { ...gridDefaultVal },
    gridLoader: false,
    processId: null,
    selectedItem: {},
    selectedClaim: null,
    selectionType: null,
    isGridRefresh: false,
    pageSize: 500,

    deleteFilesLoader: [],
    deleteClaimsLoader: [],
    swaggerJSON: null,
    refreshTrigger: 0,
};

const leftPanelSlice = createSlice({
    name: 'Left Panel',
    initialState,
    reducers: {
        setSchemaSelectedOption: (state, action: PayloadAction<Record<string, unknown>>) => {
            state.schemaSelectedOption = action.payload;
        },
        setSelectedGridRow: (state, action: PayloadAction<{ processId: string | null; item: Record<string, unknown>; selectionType?: 'claim' | 'document' }>) => {
            state.processId = action.payload.processId;
            state.selectedItem = action.payload.item;
            state.selectionType = action.payload.selectionType || 'document';
        },
        setSelectedClaim: (state, action: PayloadAction<{ claim: Record<string, unknown> }>) => {
            state.selectedClaim = action.payload.claim;
            state.selectionType = 'claim';
            state.processId = null;
            state.selectedItem = {};
        },
        setRefreshGrid: (state, action: PayloadAction<boolean>) => {
            state.isGridRefresh = action.payload;
        },
        incrementRefreshTrigger: (state) => {
            state.refreshTrigger += 1;
        },
    },
    extraReducers: (builder) => {
        builder
            .addCase(fetchSwaggerData.pending, (state) => {
                state.swaggerJSON = null;
            })
            .addCase(fetchSwaggerData.fulfilled, (state, action) => {
                state.swaggerJSON = action.payload as Record<string, unknown>;
            })
            .addCase(fetchSwaggerData.rejected, (state) => {
                state.swaggerJSON = null;
            });
        
        builder
            .addCase(fetchSchemaData.pending, (state) => {
                state.schemaLoader = true;
                state.schemaError = null;
            })
            .addCase(fetchSchemaData.fulfilled, (state, action) => {
                state.schemaData = action.payload as Record<string, unknown>[];
                state.schemaLoader = false;
            })
            .addCase(fetchSchemaData.rejected, (state, action) => {
                state.schemaError = action.error.message || 'An error occurred';
                state.schemaLoader = false;
            });

        builder
            .addCase(fetchSchemasetData.pending, (state) => {
                state.schemaLoader = true;
                state.schemaError = null;
            })
            .addCase(fetchSchemasetData.fulfilled, (state, action) => {
                state.schemaSetData = action.payload as Record<string, unknown>[];
                state.schemaLoader = false;
            })
            .addCase(fetchSchemasetData.rejected, (state, action) => {
                state.schemaError = action.error.message || 'An error occurred';
                state.schemaLoader = false;
            });

        builder
            .addCase(fetchSchemasBySchemaSet.pending, (state) => {
                state.schemaLoader = true;
                state.schemaError = null;
                state.schemaData = [];
            })
            .addCase(fetchSchemasBySchemaSet.fulfilled, (state, action) => {
                state.schemaData = action.payload as Record<string, unknown>[];
                state.schemaLoader = false;
            })
            .addCase(fetchSchemasBySchemaSet.rejected, (state, action) => {
                state.schemaError = action.error.message || 'An error occurred';
                state.schemaLoader = false;
            });

        builder
            .addCase(fetchContentTableData.pending, (state) => {
                state.gridLoader = true;
            })
            .addCase(fetchContentTableData.fulfilled, (state, action) => {
                state.gridData = action.payload as GridData;
                state.gridLoader = false;
            })
            .addCase(fetchContentTableData.rejected, (state, action) => {
                state.gridLoader = false;
                toast.error(action.payload as string);
            });

        builder
            .addCase(uploadFile.pending, () => {
                // No loading state needed; handled by file-upload UI.
            })
            .addCase(uploadFile.fulfilled, () => {
                // Handled by the upload modal callback.
            })
            .addCase(uploadFile.rejected, () => {
                // Error already surfaced via handleApiThunk.
            });

        builder
            .addCase(deleteProcessedFile.pending, (state, action) => {
                const processId = action.meta.arg.processId;
                if (processId) {
                    state.deleteFilesLoader.push(processId);
                }
            })
            .addCase(deleteProcessedFile.fulfilled, (state, action) => {
                const processId = action.meta.arg.processId;
                if (processId) {
                    state.deleteFilesLoader = state.deleteFilesLoader.filter(id => id !== processId);
                }
                const payload = action.payload as DeleteApiResponse;
                if (payload.status === 'Success') {
                    toast.success("File deleted successfully.");
                    state.isGridRefresh = true;
                } else {
                    toast.error(payload.message);
                }
            })
            .addCase(deleteProcessedFile.rejected, (state, action) => {
                const processId = action.meta.arg.processId;
                if (processId) {
                    state.deleteFilesLoader = state.deleteFilesLoader.filter(id => id !== processId);
                    toast.error("Failed to delete the file. Please try again.")
                }
            });

        builder
            .addCase(deleteClaim.pending, (state, action) => {
                const claimId = action.meta.arg.claimId;
                if (claimId) {
                    state.deleteClaimsLoader.push(claimId);
                }
            })
            .addCase(deleteClaim.fulfilled, (state, action) => {
                const claimId = action.meta.arg.claimId;
                if (claimId) {
                    state.deleteClaimsLoader = state.deleteClaimsLoader.filter(id => id !== claimId);
                }
                const payload = action.payload as DeleteApiResponse;
                if (payload.status === 'Success') {
                    toast.success("Claim deleted successfully.");
                    state.isGridRefresh = true;
                } else {
                    toast.error(payload.message);
                }
            })
            .addCase(deleteClaim.rejected, (state, action) => {
                const claimId = action.meta.arg.claimId;
                if (claimId) {
                    state.deleteClaimsLoader = state.deleteClaimsLoader.filter(id => id !== claimId);
                    toast.error("Failed to delete the claim. Please try again.")
                }
            });
    },
});

export const { setSchemaSelectedOption, setSelectedGridRow, setSelectedClaim, setRefreshGrid, incrementRefreshTrigger } = leftPanelSlice.actions;
export default leftPanelSlice.reducer;
