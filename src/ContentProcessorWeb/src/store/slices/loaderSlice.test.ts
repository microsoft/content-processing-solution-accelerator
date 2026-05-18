// Copyright (c) Microsoft Corporation.
// Licensed under the MIT License.

/**
 * @file Tests for loaderSlice — loading stack management.
 */

import reducer, { startLoader, stopLoader } from './loaderSlice';
import type { LoaderState } from './loaderSlice';

// ── Initial State ──────────────────────────────────────────────────────

const initialState: LoaderState = {
    loadingStack: [],
};

describe('loaderSlice', () => {
    describe('initial state', () => {
        it('should return the initial state with an empty loading stack', () => {
            expect(reducer(undefined, { type: 'unknown' })).toEqual(initialState);
        });
    });

    // ── startLoader ────────────────────────────────────────────────────────

    describe('startLoader', () => {
        it('should push an identifier onto the loading stack', () => {
            const state = reducer(initialState, startLoader('fetchSchema'));
            expect(state.loadingStack).toEqual(['fetchSchema']);
        });

        it('should allow multiple identifiers on the stack', () => {
            let state = reducer(initialState, startLoader('fetchSchema'));
            state = reducer(state, startLoader('fetchGrid'));
            expect(state.loadingStack).toEqual(['fetchSchema', 'fetchGrid']);
        });

        it('should allow duplicate identifiers', () => {
            let state = reducer(initialState, startLoader('fetchSchema'));
            state = reducer(state, startLoader('fetchSchema'));
            expect(state.loadingStack).toHaveLength(2);
        });
    });

    // ── stopLoader ─────────────────────────────────────────────────────────

    describe('stopLoader', () => {
        it('should remove the matching identifier from the stack', () => {
            const populated: LoaderState = {
                loadingStack: ['fetchSchema', 'fetchGrid'],
            };
            const state = reducer(populated, stopLoader('fetchSchema'));
            expect(state.loadingStack).toEqual(['fetchGrid']);
        });

        it('should remove all duplicates of the identifier', () => {
            const duplicated: LoaderState = {
                loadingStack: ['fetchSchema', 'fetchGrid', 'fetchSchema'],
            };
            const state = reducer(duplicated, stopLoader('fetchSchema'));
            expect(state.loadingStack).toEqual(['fetchGrid']);
        });

        it('should do nothing when the identifier is not in the stack', () => {
            const populated: LoaderState = {
                loadingStack: ['fetchSchema'],
            };
            const state = reducer(populated, stopLoader('nonExistent'));
            expect(state.loadingStack).toEqual(['fetchSchema']);
        });

        it('should return an empty stack when removing the last identifier', () => {
            const single: LoaderState = {
                loadingStack: ['fetchSchema'],
            };
            const state = reducer(single, stopLoader('fetchSchema'));
            expect(state.loadingStack).toEqual([]);
        });
    });
});
