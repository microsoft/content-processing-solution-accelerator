// Copyright (c) Microsoft Corporation.
// Licensed under the MIT License.

/**
 * Redux slice for the center panel, which displays processed content JSON,
 * process step details, claim information, and handles save operations.
 */
import { createSlice, createAsyncThunk, PayloadAction } from '@reduxjs/toolkit';

import httpUtility, { handleApiThunk } from '../../Services/httpUtility';
import { toast } from "react-toastify";

export interface CenterPanelState {
    contentData: Record<string, unknown>;
    cLoader: boolean;
    cError: string | null;
    modified_result: Record<string, unknown>;
    comments: string;
    isSavingInProgress: boolean;
    activeProcessId: string;
    processStepsData: Record<string, unknown>[];
    isJSONEditorSearchEnabled: boolean;
    claimDetails: Record<string, unknown> | null;
    claimDetailsLoader: boolean;
    claimCommentSaving: boolean;
}

/** Maps certain backend error strings to user-friendly messages. */
const getDisplayMessage = (text: string): string => {
    if (
        text.startsWith('Processing of file with Process') &&
        text.endsWith('not found.')
    ) {
        return 'This record no longer exists. Please refresh.';
    }
    return text;
};

export const fetchContentJsonData = createAsyncThunk<
    Record<string, unknown>,
    { processId: string | null }
>('/contentprocessor/processed/', async ({ processId }, { rejectWithValue }) => {
    if (!processId) {
        return rejectWithValue("Reset store");
    }
    const url = '/contentprocessor/processed/' + processId;

    return handleApiThunk(
        httpUtility.get<Record<string, unknown>>(url),
        rejectWithValue,
        'Failed to fetch content JSON data',
        url
    );
});

export const fetchProcessSteps = createAsyncThunk<
    Record<string, unknown>[],
    { processId: string | null }
>('/contentprocessor/processed/processId/steps', async ({ processId }, { rejectWithValue }) => {
    if (!processId) {
        return rejectWithValue("Reset store");
    }
    const url = `/contentprocessor/processed/${processId}/steps`;

    return handleApiThunk(
        httpUtility.get<Record<string, unknown>[]>(url),
        rejectWithValue,
        'Failed to fetch process steps',
        url
    );
});

export const fetchClaimDetails = createAsyncThunk<
    Record<string, unknown>,
    { claimId: string | null }
>('/claimprocessor/claims/claimId', async ({ claimId }, { rejectWithValue }) => {
    if (!claimId) {
        return rejectWithValue("Reset store");
    }
    const url = `/claimprocessor/claims/${claimId}`;

    return handleApiThunk(
        httpUtility.get<Record<string, unknown>>(url),
        rejectWithValue,
        'Failed to fetch claim details',
        url
    );
});

export const saveClaimComment = createAsyncThunk<
    Record<string, unknown>,
    { claimId: string | null; comment: string }
>('/claimprocessor/claims/claimId/comment', async ({ claimId, comment }, { rejectWithValue }) => {
    if (!claimId) {
        return rejectWithValue("Claim ID is required");
    }
    const url = `/claimprocessor/claims/${claimId}/comment`;

    return handleApiThunk(
        httpUtility.post<Record<string, unknown>>(url, { comment: comment }),
        rejectWithValue,
        'Failed to save claim comment',
        url
    );
});

interface SaveContentJsonArgs {
    processId: string | null;
    contentJson: string;
    comments: string;
    savedComments: string;
}

export const saveContentJson = createAsyncThunk<
    Record<string, unknown>,
    SaveContentJsonArgs
>('SaveContentJSON-Comments', async ({ processId, contentJson, comments, savedComments }, { rejectWithValue }) => {
    if (!processId) {
        return rejectWithValue('Process ID is required');
    }

    const url = `/contentprocessor/processed/${processId}`;
    const requests: Promise<unknown>[] = [];

    if (contentJson && Object.keys(contentJson).length > 0) {
        requests.push(
            handleApiThunk(
                httpUtility.put(url, {
                    process_id: processId,
                    modified_result: contentJson,
                }),
                rejectWithValue,
                'Failed to save content JSON',
                url
            )
        );
    }

    if (comments.trim() !== '' || (savedComments !== '' && comments.trim() === '')) {
        requests.push(
            handleApiThunk(
                httpUtility.put(url, {
                    process_id: processId,
                    comment: comments,
                }),
                rejectWithValue,
                'Failed to save comments',
                url
            )
        );
    }

    if (requests.length === 0) {
        return { message: 'No updates were made' };
    }

    const responses = await Promise.all(requests);
    return responses[0] as Record<string, unknown>;
});


const initialState: CenterPanelState = {
    contentData: {},
    cLoader: false,
    cError: '',
    modified_result: {},
    comments: '',
    isSavingInProgress: false,
    activeProcessId: '',
    processStepsData: [],
    isJSONEditorSearchEnabled: true,
    claimDetails: null,
    claimDetailsLoader: false,
    claimCommentSaving: false,
};

const centerPanelSlice = createSlice({
    name: 'Center Panel',
    initialState,
    reducers: {
        setModifiedResult: (state, action: PayloadAction<Record<string, unknown>>) => {
            state.modified_result = action.payload;
        },
        setUpdateComments: (state, action: PayloadAction<string>) => {
            state.comments = action.payload;
        },
        setActiveProcessId: (state, action: PayloadAction<string>) => {
            state.activeProcessId = action.payload;
        },
    },
    extraReducers: (builder) => {
        builder
            .addCase(fetchContentJsonData.pending, (state) => {
                state.cLoader = true;
                state.cError = null;
                state.modified_result = {};
                state.comments = '';
            })
            .addCase(fetchContentJsonData.fulfilled, (state, action) => {
                const payload = action.payload as Record<string, unknown>;
                if (state.activeProcessId === payload.process_id) {
                    state.contentData = payload;
                    state.comments = (payload.comment as string) ?? "";
                    state.cLoader = false;
                }
            })
            .addCase(fetchContentJsonData.rejected, (state, action) => {
                state.cError = action.error.message || 'An error occurred';
                state.cLoader = false;
                state.contentData = {};
                state.comments = "";
                toast.error(getDisplayMessage(action.payload as string));
            });

        builder
            .addCase(saveContentJson.pending, (state) => {
                state.modified_result = {};
                state.isSavingInProgress = true;
            })
            .addCase(saveContentJson.fulfilled, (state) => {
                toast.success("Data saved successfully!");
                state.isSavingInProgress = false;
            })
            .addCase(saveContentJson.rejected, (state, action) => {
                toast.error(getDisplayMessage(action.payload as string));
                state.isSavingInProgress = false;
            });

        builder
            .addCase(fetchProcessSteps.pending, (state) => {
                state.processStepsData = [];
            })
            .addCase(fetchProcessSteps.fulfilled, (state, action) => {
                state.processStepsData = action.payload as Record<string, unknown>[];
            })
            .addCase(fetchProcessSteps.rejected, (state, action) => {
                if (action.payload === "Reset store") {
                    state.processStepsData = [];
                }
            });

        builder
            .addCase(fetchClaimDetails.pending, (state) => {
                state.claimDetailsLoader = true;
                state.claimDetails = null;
            })
            .addCase(fetchClaimDetails.fulfilled, (state, action) => {
                state.claimDetails = action.payload as Record<string, unknown>;
                state.claimDetailsLoader = false;
            })
            .addCase(fetchClaimDetails.rejected, (state, action) => {
                state.claimDetailsLoader = false;
                state.claimDetails = null;
                if (action.payload !== "Reset store") {
                    toast.error('Failed to fetch claim details');
                }
            });

        builder
            .addCase(saveClaimComment.pending, (state) => {
                state.claimCommentSaving = true;
            })
            .addCase(saveClaimComment.fulfilled, (state, action) => {
                state.claimCommentSaving = false;
                if (state.claimDetails) {
                    const data = state.claimDetails.data as Record<string, unknown> | undefined;
                    if (data) {
                        data.process_comment = action.meta.arg.comment;
                    }
                }
                toast.success('Comment saved successfully');
            })
            .addCase(saveClaimComment.rejected, (state) => {
                state.claimCommentSaving = false;
                toast.error('Failed to save comment');
            });
    },
});

export const { setModifiedResult, setUpdateComments, setActiveProcessId } = centerPanelSlice.actions;
export default centerPanelSlice.reducer;
