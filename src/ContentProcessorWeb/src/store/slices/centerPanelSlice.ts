import { createSlice, createAsyncThunk, PayloadAction } from '@reduxjs/toolkit';

import httpUtility from '../../Services/httpUtility';
import { toast } from "react-toastify";

interface CenterPanelState {
    contentData: any;
    cLoader: boolean;
    cError: string | null;
    modified_result: any;
    comments: string;
    isSavingInProgress: boolean;
    activeProcessId : string,
    processStepsData: any[];
    isJSONEditorSearchEnabled: boolean;
}


// Create the async thunk with the argument and return types
export const fetchContentJsonData = createAsyncThunk<any, { processId: string | null }>('/contentprocessor/processed/', async ({ processId }, {rejectWithValue}) => {
    if (!processId) {
        return rejectWithValue("Reset store");
    }
    const url = '/contentprocessor/processed/' + processId;
    const response = await httpUtility.get(url);
    //console.log("response", response);
    return response;
});

export const fetchProcessSteps = createAsyncThunk<any, { processId: string | null }>('/contentprocessor/processed/processId/steps', async ({ processId }, { rejectWithValue }) => {
    if (!processId) {
        return rejectWithValue("Reset store");
    }
    const url = '/contentprocessor/processed/' + processId + "/steps";
    const response = await httpUtility.get(url);
    //console.log("response", response);
    return response;
});

export const saveContentJson = createAsyncThunk<any, { processId: string | null, contentJson: string, comments: string ,savedComments: string }>('SaveContentJSON-Comments', async ({ processId, contentJson, comments ,savedComments }) => {
    try {
        if (!processId) throw new Error("Process ID is required");

        const url = `/contentprocessor/processed/${processId}`;
        const requests: Promise<any>[] = [];

        if (contentJson && Object.keys(contentJson).length > 0) {
            requests.push(
                httpUtility.put(url, {
                    process_id: processId,
                    modified_result: contentJson,
                })
            );
        }
        if (comments.trim() !== '' || (savedComments!='' && comments.trim()=='') ) {
            requests.push(
                httpUtility.put(url, {
                    process_id: processId,
                    comment: comments,
                })
            );
        }
        if (requests.length === 0) {
            return { message: "No updates were made" };
        }
        const responses = await Promise.all(requests);

        return responses;
    } catch (error) {
        return Promise.reject(error);
    }
});


const initialState: CenterPanelState = {
    contentData: {},
    cLoader: false,
    cError: '',
    modified_result: {},
    comments: '',
    isSavingInProgress: false,
    activeProcessId : '',
    processStepsData: [],
    isJSONEditorSearchEnabled : true,
};

const centerPanelSlice = createSlice({
    name: 'Center Panel',
    initialState,
    reducers: {
        setModifiedResult: (state, action) => {
            state.modified_result = action.payload;
        },
        setUpdateComments :  (state, action) => {
           state.comments = action.payload
        },
       setActiveProcessId :(state,action) =>{
          state.activeProcessId = action.payload
       }
    },
    extraReducers: (builder) => {
        //Fetch Dropdown values
        builder
            .addCase(fetchContentJsonData.pending, (state) => {
                state.cLoader = true; // You can manage loading state if necessary
                state.cError = null;
                state.modified_result = {};
                state.comments = '';
            })
            .addCase(fetchContentJsonData.fulfilled, (state, action) => { // Adjust `any` to the response data type
                if(state.activeProcessId == action.payload.process_id){
                    state.contentData = action.payload;
                    state.comments = action.payload.comment?? "" ;
                    state.cLoader = false;
                }
            })
            .addCase(fetchContentJsonData.rejected, (state, action) => {
                state.cError = action.error.message || 'An error occurred';
                state.cLoader = false;
                state.contentData = [];
                state.comments = "";
                //console.error("Error fetching JSON data:", action.error.message || 'An error occurred');
            });

        builder
            .addCase(saveContentJson.pending, (state,action) => {
                state.modified_result = {};
                state.isSavingInProgress = true;
            })
            .addCase(saveContentJson.fulfilled, (state, action) => { // Adjust `any` to the response data type
                toast.success("Data saved successfully!"); // Success toast
                state.isSavingInProgress = false;
            })
            .addCase(saveContentJson.rejected, (state, action : any) => {
                console.log("action", action)
                toast.error(JSON.parse(action.error.message).message);
                state.isSavingInProgress = false;
            });

        builder
            .addCase(fetchProcessSteps.pending, (state) => {
                state.processStepsData = [];
                //state.isSavingInProgress = true;
            })
            .addCase(fetchProcessSteps.fulfilled, (state, action) => { // Adjust `any` to the response data type
                state.processStepsData = action.payload;
            })
            .addCase(fetchProcessSteps.rejected, (state, action) => {
                if (action.payload === "Reset store") {
                    state.processStepsData = []; // Reset store when processId is null
                } else {
                    //console.error("Error fetching Process Steps Data:", action.error.message || 'An error occurred');
                }
            });

    },
});

export const { setModifiedResult ,setUpdateComments, setActiveProcessId} = centerPanelSlice.actions;
export default centerPanelSlice.reducer;
