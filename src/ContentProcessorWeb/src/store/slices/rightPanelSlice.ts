// Copyright (c) Microsoft Corporation.
// Licensed under the MIT License.

/**
 * Redux slice for the right panel, which displays the original file preview
 * (blob URL, response headers) for a selected processed document.
 */
import { createSlice, createAsyncThunk, PayloadAction } from '@reduxjs/toolkit';

import httpUtility from '../../Services/httpUtility';

interface FileResponseEntry {
    headers: Record<string, string>;
    blobURL: string;
    processId: string;
}

export interface RightPanelState {
    fileHeaders: Record<string, string>;
    rLoader: boolean;
    blobURL: string;
    rError: string | null;
    fileResponse: FileResponseEntry[];
}

/** Fetches the original file blob and its HTTP headers for the given process. */
export const fetchContentFileData = createAsyncThunk<
    FileResponseEntry,
    { processId: string | null }
>(
    '/contentprocessor/processed/files/',
    async ({ processId }, { rejectWithValue }) => {
        const url = '/contentprocessor/processed/files/' + processId;
        try {
            const response = await httpUtility.headers(url);

            if (!response.ok) throw new Error("Failed to fetch file");
            const blob = await response.blob();
            const blobURL = URL.createObjectURL(blob);
            const headers = response.headers;
            if (!headers) {
                throw new Error("Failed to fetch headers");
            }
            const headersObject = Object.fromEntries(headers.entries());
            return { headers: headersObject, blobURL, processId: processId as string };
        } catch {
            return rejectWithValue({
                success: false,
                message: 'Failed to fetch file',
            });
        }
    }
);

const initialState: RightPanelState = {
    fileHeaders: {},
    blobURL: '',
    rLoader: false,
    rError: '',
    fileResponse: [],
};

const rightPanelSlice = createSlice({
    name: 'Right Panel',
    initialState,
    reducers: {},
    extraReducers: (builder) => {
        builder
            .addCase(fetchContentFileData.pending, (state) => {
                state.fileHeaders = {};
                state.blobURL = '';
                state.rLoader = true;
                state.rError = '';
            })
            .addCase(fetchContentFileData.fulfilled, (state, action: PayloadAction<FileResponseEntry>) => {
                state.fileHeaders = action.payload.headers;
                state.blobURL = action.payload.blobURL;
                state.rLoader = false;
                const isItemExists = state.fileResponse.find(
                    (i) => i.processId === action.payload.processId
                );
                if (!isItemExists) {
                    state.fileResponse.push(action.payload);
                }
            })
            .addCase(fetchContentFileData.rejected, (state, action) => {
                state.rLoader = false;
                state.rError = action.error.message || 'An error occurred';
            });
    },
});

export default rightPanelSlice.reducer;
