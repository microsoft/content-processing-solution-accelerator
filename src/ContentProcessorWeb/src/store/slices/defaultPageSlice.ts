// Copyright (c) Microsoft Corporation.
// Licensed under the MIT License.

/**
 * Redux slice managing panel collapse state for the Default Page layout
 * (left, center, and right panels).
 */
import { createSlice, PayloadAction } from '@reduxjs/toolkit';

export interface DefaultPageState {
    readonly isLeftPanelCollapse: boolean;
    readonly isCenterPanelCollapse: boolean;
    readonly isRightPanelCollapse: boolean;
}

type PanelTarget = 'Left' | 'Right' | 'Center' | 'All';

const initialState: DefaultPageState = {
    isLeftPanelCollapse: false,
    isCenterPanelCollapse: false,
    isRightPanelCollapse: false,
};

const defaultPageSlice = createSlice({
    name: 'Default Page',
    initialState,
    reducers: {
        updatePanelCollapse: (state, action: PayloadAction<PanelTarget>) => {
            switch (action.payload) {
                case 'Left':
                    state.isLeftPanelCollapse = !state.isLeftPanelCollapse;
                    break;
                case 'Right':
                    state.isRightPanelCollapse = !state.isRightPanelCollapse;
                    break;
                case 'Center':
                    state.isCenterPanelCollapse = !state.isCenterPanelCollapse;
                    break;
                case 'All':
                    state.isLeftPanelCollapse = true;
                    state.isCenterPanelCollapse = true;
                    state.isRightPanelCollapse = true;
                    break;
                default:
                    state.isLeftPanelCollapse = false;
                    state.isCenterPanelCollapse = false;
                    state.isRightPanelCollapse = false;
                    break;
            }
        },
    },
});

export const { updatePanelCollapse } = defaultPageSlice.actions;
export default defaultPageSlice.reducer;
