import { createSlice, createAsyncThunk, PayloadAction } from '@reduxjs/toolkit';

interface defaultPageState {
    isLeftPanelCollapse: boolean;
    isCenterPanelCollapse: boolean;
    isRightPanelCollapse: boolean;
}

const initialState: defaultPageState = {
    isLeftPanelCollapse: false,
    isCenterPanelCollapse: false,
    isRightPanelCollapse: false
};

const defaultPageSlice = createSlice({
    name: 'Default Page',
    initialState,
    reducers: {
        updatePanelCollapse: (state, action) => {
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
                    state.isRightPanelCollapse = true;
                    state.isLeftPanelCollapse = true;
                    break;
                default:
                    state.isLeftPanelCollapse = false;
                    state.isRightPanelCollapse = false;
                    state.isLeftPanelCollapse = false;
                    break;
            }
        },

    },
    extraReducers: (builder) => {

    },
});

export const { updatePanelCollapse } = defaultPageSlice.actions;
export default defaultPageSlice.reducer;
