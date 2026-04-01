// Copyright (c) Microsoft Corporation.
// Licensed under the MIT License.

/**
 * @file Tests for defaultPageSlice — panel collapse state management.
 */

import reducer, { updatePanelCollapse } from './defaultPageSlice';
import type { DefaultPageState } from './defaultPageSlice';

// ── Initial State ──────────────────────────────────────────────────────

const initialState: DefaultPageState = {
    isLeftPanelCollapse: false,
    isCenterPanelCollapse: false,
    isRightPanelCollapse: false,
};

describe('defaultPageSlice', () => {
    describe('initial state', () => {
        it('should return the initial state when passed an unknown action', () => {
            expect(reducer(undefined, { type: 'unknown' })).toEqual(initialState);
        });

        it('should default all panels to not collapsed', () => {
            const state = reducer(undefined, { type: 'unknown' });
            expect(state.isLeftPanelCollapse).toBe(false);
            expect(state.isCenterPanelCollapse).toBe(false);
            expect(state.isRightPanelCollapse).toBe(false);
        });
    });

    // ── updatePanelCollapse ────────────────────────────────────────────────

    describe('updatePanelCollapse', () => {
        it('should toggle the left panel when dispatched with "Left"', () => {
            const state1 = reducer(initialState, updatePanelCollapse('Left'));
            expect(state1.isLeftPanelCollapse).toBe(true);
            expect(state1.isCenterPanelCollapse).toBe(false);
            expect(state1.isRightPanelCollapse).toBe(false);

            // Toggle back
            const state2 = reducer(state1, updatePanelCollapse('Left'));
            expect(state2.isLeftPanelCollapse).toBe(false);
        });

        it('should toggle the right panel when dispatched with "Right"', () => {
            const state1 = reducer(initialState, updatePanelCollapse('Right'));
            expect(state1.isRightPanelCollapse).toBe(true);
            expect(state1.isLeftPanelCollapse).toBe(false);
            expect(state1.isCenterPanelCollapse).toBe(false);

            const state2 = reducer(state1, updatePanelCollapse('Right'));
            expect(state2.isRightPanelCollapse).toBe(false);
        });

        it('should toggle the center panel when dispatched with "Center"', () => {
            const state1 = reducer(initialState, updatePanelCollapse('Center'));
            expect(state1.isCenterPanelCollapse).toBe(true);
            expect(state1.isLeftPanelCollapse).toBe(false);
            expect(state1.isRightPanelCollapse).toBe(false);

            const state2 = reducer(state1, updatePanelCollapse('Center'));
            expect(state2.isCenterPanelCollapse).toBe(false);
        });

        it('should collapse all panels when dispatched with "All"', () => {
            const state = reducer(initialState, updatePanelCollapse('All'));
            expect(state.isLeftPanelCollapse).toBe(true);
            expect(state.isCenterPanelCollapse).toBe(true);
            expect(state.isRightPanelCollapse).toBe(true);
        });

        it('should reset all panels to expanded for an unrecognised target', () => {
            const allCollapsed: DefaultPageState = {
                isLeftPanelCollapse: true,
                isCenterPanelCollapse: true,
                isRightPanelCollapse: true,
            };
            // Any string that isn't Left/Right/Center/All hits the default branch
            const state = reducer(allCollapsed, updatePanelCollapse('Reset' as never));
            expect(state.isLeftPanelCollapse).toBe(false);
            expect(state.isCenterPanelCollapse).toBe(false);
            expect(state.isRightPanelCollapse).toBe(false);
        });

        it('should not affect other panels when toggling one', () => {
            const partialCollapsed: DefaultPageState = {
                isLeftPanelCollapse: true,
                isCenterPanelCollapse: false,
                isRightPanelCollapse: true,
            };
            const state = reducer(partialCollapsed, updatePanelCollapse('Center'));
            expect(state.isLeftPanelCollapse).toBe(true);
            expect(state.isCenterPanelCollapse).toBe(true);
            expect(state.isRightPanelCollapse).toBe(true);
        });
    });
});
