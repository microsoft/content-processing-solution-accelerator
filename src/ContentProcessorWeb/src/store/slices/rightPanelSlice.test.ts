// Copyright (c) Microsoft Corporation.
// Licensed under the MIT License.

/**
 * @file Tests for rightPanelSlice — file blob fetching and response caching.
 */

import reducer, { fetchContentFileData } from './rightPanelSlice';
import type { RightPanelState } from './rightPanelSlice';

// ── Helpers ────────────────────────────────────────────────────────────

const getInitialState = (): RightPanelState => ({
    fileHeaders: {},
    blobURL: '',
    rLoader: false,
    rError: '',
    fileResponse: [],
});

describe('rightPanelSlice', () => {
    describe('initial state', () => {
        it('should return the correct initial state', () => {
            expect(reducer(undefined, { type: 'unknown' })).toEqual(getInitialState());
        });
    });

    // ── fetchContentFileData ─────────────────────────────────────────────

    describe('fetchContentFileData', () => {
        it('should set rLoader and clear blobURL/headers on pending', () => {
            const state = reducer(
                getInitialState(),
                fetchContentFileData.pending('', { processId: 'p-1' })
            );
            expect(state.rLoader).toBe(true);
            expect(state.blobURL).toBe('');
            expect(state.fileHeaders).toEqual({});
            expect(state.rError).toBe('');
        });

        it('should populate fileHeaders and blobURL on fulfilled', () => {
            const payload = {
                headers: { 'content-type': 'application/pdf' },
                blobURL: 'blob:http://localhost/abc',
                processId: 'p-1',
            };
            const state = reducer(
                getInitialState(),
                fetchContentFileData.fulfilled(payload, '', { processId: 'p-1' })
            );
            expect(state.fileHeaders).toEqual(payload.headers);
            expect(state.blobURL).toBe(payload.blobURL);
            expect(state.rLoader).toBe(false);
        });

        it('should cache the response in fileResponse array', () => {
            const payload = {
                headers: { 'content-type': 'image/png' },
                blobURL: 'blob:http://localhost/123',
                processId: 'p-1',
            };
            const state = reducer(
                getInitialState(),
                fetchContentFileData.fulfilled(payload, '', { processId: 'p-1' })
            );
            expect(state.fileResponse).toHaveLength(1);
            expect(state.fileResponse[0].processId).toBe('p-1');
        });

        it('should not duplicate entries in fileResponse for the same processId', () => {
            const initial: RightPanelState = {
                ...getInitialState(),
                fileResponse: [
                    {
                        headers: { 'content-type': 'application/pdf' },
                        blobURL: 'blob:old',
                        processId: 'p-1',
                    },
                ],
            };
            const payload = {
                headers: { 'content-type': 'application/pdf' },
                blobURL: 'blob:new',
                processId: 'p-1',
            };
            const state = reducer(
                initial,
                fetchContentFileData.fulfilled(payload, '', { processId: 'p-1' })
            );
            // Should still have only one entry for p-1
            expect(state.fileResponse).toHaveLength(1);
        });

        it('should add a new entry for a different processId', () => {
            const initial: RightPanelState = {
                ...getInitialState(),
                fileResponse: [
                    { headers: {}, blobURL: 'blob:a', processId: 'p-1' },
                ],
            };
            const payload = {
                headers: { 'content-type': 'text/plain' },
                blobURL: 'blob:b',
                processId: 'p-2',
            };
            const state = reducer(
                initial,
                fetchContentFileData.fulfilled(payload, '', { processId: 'p-2' })
            );
            expect(state.fileResponse).toHaveLength(2);
        });

        it('should set rError on rejected', () => {
            const state = reducer(
                getInitialState(),
                fetchContentFileData.rejected(
                    new Error('Network failure'),
                    '',
                    { processId: 'p-1' }
                )
            );
            expect(state.rLoader).toBe(false);
            expect(state.rError).toBe('Network failure');
        });

        it('should set a default error message when none is provided', () => {
            const state = reducer(
                getInitialState(),
                fetchContentFileData.rejected(
                    new Error(),
                    '',
                    { processId: 'p-1' }
                )
            );
            expect(state.rError).toBe('An error occurred');
        });
    });
});
