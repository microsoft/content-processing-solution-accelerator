// Copyright (c) Microsoft Corporation.
// Licensed under the MIT License.

/**
 * @file Tests for centerPanelSlice — content JSON, process steps,
 * claim details, save operations, and their async state transitions.
 */

import reducer, {
    setModifiedResult,
    setUpdateComments,
    setActiveProcessId,
    fetchContentJsonData,
    saveContentJson,
    fetchProcessSteps,
    fetchClaimDetails,
    saveClaimComment,
} from './centerPanelSlice';
import type { CenterPanelState } from './centerPanelSlice';

// ── Helpers ────────────────────────────────────────────────────────────

const getInitialState = (): CenterPanelState => ({
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
});

describe('centerPanelSlice', () => {
    // ── Initial State ────────────────────────────────────────────────────

    describe('initial state', () => {
        it('should return the correct initial state', () => {
            expect(reducer(undefined, { type: 'unknown' })).toEqual(getInitialState());
        });
    });

    // ── Synchronous Reducers ─────────────────────────────────────────────

    describe('setModifiedResult', () => {
        it('should update modified_result', () => {
            const payload = { field: 'value' };
            const state = reducer(getInitialState(), setModifiedResult(payload));
            expect(state.modified_result).toEqual(payload);
        });
    });

    describe('setUpdateComments', () => {
        it('should update the comments string', () => {
            const state = reducer(getInitialState(), setUpdateComments('New comment'));
            expect(state.comments).toBe('New comment');
        });

        it('should allow setting an empty comment', () => {
            const withComment = { ...getInitialState(), comments: 'Old comment' };
            const state = reducer(withComment, setUpdateComments(''));
            expect(state.comments).toBe('');
        });
    });

    describe('setActiveProcessId', () => {
        it('should set the active process ID', () => {
            const state = reducer(getInitialState(), setActiveProcessId('p-123'));
            expect(state.activeProcessId).toBe('p-123');
        });
    });

    // ── fetchContentJsonData ─────────────────────────────────────────────

    describe('fetchContentJsonData', () => {
        it('should set cLoader and clear data on pending', () => {
            const state = reducer(
                getInitialState(),
                fetchContentJsonData.pending('', { processId: 'p-1' })
            );
            expect(state.cLoader).toBe(true);
            expect(state.cError).toBeNull();
            expect(state.modified_result).toEqual({});
            expect(state.comments).toBe('');
        });

        it('should populate contentData on fulfilled when activeProcessId matches', () => {
            const initial: CenterPanelState = {
                ...getInitialState(),
                activeProcessId: 'p-1',
            };
            const payload = { process_id: 'p-1', comment: 'A note', data: {} };
            const state = reducer(
                initial,
                fetchContentJsonData.fulfilled(payload, '', { processId: 'p-1' })
            );
            expect(state.contentData).toEqual(payload);
            expect(state.comments).toBe('A note');
            expect(state.cLoader).toBe(false);
        });

        it('should not update contentData when activeProcessId does not match', () => {
            const initial: CenterPanelState = {
                ...getInitialState(),
                activeProcessId: 'p-other',
            };
            const payload = { process_id: 'p-1', data: {} };
            const state = reducer(
                initial,
                fetchContentJsonData.fulfilled(payload, '', { processId: 'p-1' })
            );
            // contentData stays empty because process IDs don't match
            expect(state.contentData).toEqual({});
        });

        it('should set cError and clear contentData on rejected', () => {
            const error = new Error('Server error');
            const action = {
                type: fetchContentJsonData.rejected.type,
                error: { message: 'Server error' },
                payload: 'Server error',
                meta: { arg: { processId: 'p-1' }, requestId: '', rejectedWithValue: true, requestStatus: 'rejected' as const, aborted: false, condition: false },
            };
            const state = reducer(getInitialState(), action);
            expect(state.cError).toBe('Server error');
            expect(state.cLoader).toBe(false);
            expect(state.contentData).toEqual({});
            expect(state.comments).toBe('');
        });
    });

    // ── saveContentJson ──────────────────────────────────────────────────

    describe('saveContentJson', () => {
        const saveArgs = {
            processId: 'p-1',
            contentJson: '{"key":"val"}',
            comments: 'Test',
            savedComments: '',
        };

        it('should set isSavingInProgress and clear modified_result on pending', () => {
            const state = reducer(
                getInitialState(),
                saveContentJson.pending('', saveArgs)
            );
            expect(state.isSavingInProgress).toBe(true);
            expect(state.modified_result).toEqual({});
        });

        it('should clear isSavingInProgress on fulfilled', () => {
            const saving: CenterPanelState = {
                ...getInitialState(),
                isSavingInProgress: true,
            };
            const state = reducer(
                saving,
                saveContentJson.fulfilled({}, '', saveArgs)
            );
            expect(state.isSavingInProgress).toBe(false);
        });

        it('should clear isSavingInProgress on rejected', () => {
            const saving: CenterPanelState = {
                ...getInitialState(),
                isSavingInProgress: true,
            };
            const action = {
                type: saveContentJson.rejected.type,
                error: { message: 'fail' },
                payload: 'Failed to save',
                meta: { arg: saveArgs, requestId: '', rejectedWithValue: true, requestStatus: 'rejected' as const, aborted: false, condition: false },
            };
            const state = reducer(saving, action);
            expect(state.isSavingInProgress).toBe(false);
        });
    });

    // ── fetchProcessSteps ────────────────────────────────────────────────

    describe('fetchProcessSteps', () => {
        it('should clear processStepsData on pending', () => {
            const withSteps: CenterPanelState = {
                ...getInitialState(),
                processStepsData: [{ step: 1 }],
            };
            const state = reducer(
                withSteps,
                fetchProcessSteps.pending('', { processId: 'p-1' })
            );
            expect(state.processStepsData).toEqual([]);
        });

        it('should populate processStepsData on fulfilled', () => {
            const payload = [{ step: 1, name: 'Extract' }, { step: 2, name: 'Validate' }];
            const state = reducer(
                getInitialState(),
                fetchProcessSteps.fulfilled(payload, '', { processId: 'p-1' })
            );
            expect(state.processStepsData).toEqual(payload);
        });

        it('should reset processStepsData when rejected with "Reset store"', () => {
            const state = reducer(
                getInitialState(),
                fetchProcessSteps.rejected(null, '', { processId: null })
            );
            // The rejected handler checks for "Reset store" payload
            expect(state.processStepsData).toEqual([]);
        });
    });

    // ── fetchClaimDetails ────────────────────────────────────────────────

    describe('fetchClaimDetails', () => {
        it('should set claimDetailsLoader and clear claimDetails on pending', () => {
            const state = reducer(
                getInitialState(),
                fetchClaimDetails.pending('', { claimId: 'c-1' })
            );
            expect(state.claimDetailsLoader).toBe(true);
            expect(state.claimDetails).toBeNull();
        });

        it('should populate claimDetails on fulfilled', () => {
            const payload = { claim_id: 'c-1', status: 'approved' };
            const state = reducer(
                getInitialState(),
                fetchClaimDetails.fulfilled(payload, '', { claimId: 'c-1' })
            );
            expect(state.claimDetails).toEqual(payload);
            expect(state.claimDetailsLoader).toBe(false);
        });

        it('should clear claimDetails on rejected', () => {
            const state = reducer(
                getInitialState(),
                fetchClaimDetails.rejected(new Error('fail'), '', { claimId: 'c-1' })
            );
            expect(state.claimDetails).toBeNull();
            expect(state.claimDetailsLoader).toBe(false);
        });
    });

    // ── saveClaimComment ─────────────────────────────────────────────────

    describe('saveClaimComment', () => {
        const commentArgs = { claimId: 'c-1', comment: 'New comment' };

        it('should set claimCommentSaving on pending', () => {
            const state = reducer(
                getInitialState(),
                saveClaimComment.pending('', commentArgs)
            );
            expect(state.claimCommentSaving).toBe(true);
        });

        it('should clear claimCommentSaving on fulfilled and update process_comment', () => {
            const initial: CenterPanelState = {
                ...getInitialState(),
                claimCommentSaving: true,
                claimDetails: { claim_id: 'c-1', data: { process_comment: '' } },
            };
            const state = reducer(
                initial,
                saveClaimComment.fulfilled({}, '', commentArgs)
            );
            expect(state.claimCommentSaving).toBe(false);
            // The comment is updated on the nested data object
            const data = (state.claimDetails as Record<string, unknown>)?.data as Record<string, unknown>;
            expect(data.process_comment).toBe('New comment');
        });

        it('should clear claimCommentSaving on rejected', () => {
            const saving: CenterPanelState = {
                ...getInitialState(),
                claimCommentSaving: true,
            };
            const state = reducer(
                saving,
                saveClaimComment.rejected(new Error('fail'), '', commentArgs)
            );
            expect(state.claimCommentSaving).toBe(false);
        });
    });
});
