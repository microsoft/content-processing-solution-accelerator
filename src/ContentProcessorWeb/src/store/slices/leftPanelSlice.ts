import { createSlice, createAsyncThunk, PayloadAction } from '@reduxjs/toolkit';

import httpUtility from '../../Services/httpUtility';

import { toast } from "react-toastify";

interface LeftPanelState {
    schemaData: any;
    schemaError: string | null;
    schemaLoader: boolean;
    schemaSelectedOption: any;
    gridData: any;
    gridLoader: boolean;
    processId: string | null;
    selectedItem: any;
    pageSize: number;
    deleteFilesLoader: string[],
    isGridRefresh: boolean;
    swaggerJSON: any;
}

interface UploadMetadata {
    Metadata_Id: string;
    Schema_Id: string;
}

interface UploadFileResponse {
    success: boolean;
    message: string;
    data?: any; // You can specify a more precise type for the response data if needed
}

export const fetchSwaggerData = createAsyncThunk<any, void>('/openapi', async (): Promise<any> => {
    const url = '/openapi.json';
    const response = await httpUtility.get(url);
    return response;
});

// Async thunk for fetching data
export const fetchSchemaData = createAsyncThunk<any, void>('/schemavault', async (): Promise<any> => {
    const url = '/schemavault/';
    const response = await httpUtility.get(url);
    return response;
});

export const fetchContentTableData = createAsyncThunk<any, { pageSize: number; pageNumber: number }>('/contentprocessor/processed', async ({ pageSize, pageNumber }): Promise<any> => {
    const url = '/contentprocessor/processed';
    const response = await httpUtility.post(url, {
        page_size: pageSize,
        page_number: pageNumber,
    });
    return response;
});

interface DeleteApiResponse {
    process_id: string;
    status: string;
    message: string;
}
export const deleteProcessedFile = createAsyncThunk<any, { processId: string | null }>('/contentprocessor/deleteProcessedFile/', async ({ processId }, { rejectWithValue }) => {
    if (!processId) {
        return rejectWithValue("Reset store");
    }
    const url = '/contentprocessor/processed/' + processId;
    const response = await httpUtility.delete(url);
    console.log("response", response);
    return response as DeleteApiResponse;;
});

export const uploadFile = createAsyncThunk<
    any,  // Type for fulfilled response
    { file: File; schema: string }  // Type for the input payload
// Type for rejected value (error payload)
>(
    '/contentprocessor/submit',
    async ({ file, schema }, { rejectWithValue }): Promise<any> => {
        const url = '/contentprocessor/submit';

        const metadata: UploadMetadata = {
            Metadata_Id: crypto.randomUUID(),
            Schema_Id: schema,
        };

        const formData = new FormData();
        formData.append('file', file); // Attach the file
        formData.append('data', JSON.stringify(metadata)); // Attach JSON metadata

        try {
            // Assuming httpUtility.upload returns a Response object, cast it explicitly
            const response = await httpUtility.upload(url, formData) as Response;

            return response;
        } catch (error: any) {
            // Handle any unexpected errors (e.g., network issues)
            return rejectWithValue({
                success: false,
                message: JSON.parse(error?.message)?.message || 'An unexpected error occurred',
            });
        }
    }
);

const gridDefaultVal = {
    total_count: 0, total_pages: 0, current_page: 1, page_size: 500,
    items: []
}


const initialState: LeftPanelState = {
    schemaData: [],
    schemaSelectedOption: {},
    schemaLoader: false,
    schemaError: null,

    gridData: { ...gridDefaultVal },
    gridLoader: false,
    processId: null,
    selectedItem: {},
    isGridRefresh: false,
    pageSize: 500,

    deleteFilesLoader: [],
    swaggerJSON: null
};

const leftPanelSlice = createSlice({
    name: 'Left Panel',
    initialState,
    reducers: {
        setSchemaSelectedOption: (state, action) => {
            state.schemaSelectedOption = action.payload;
        },
        setSelectedGridRow: (state, action) => {
            state.processId = action.payload.processId;
            state.selectedItem = action.payload.item;
        },
        setRefreshGrid: (state, action) => {
            state.isGridRefresh = action.payload;
        },
    },
    extraReducers: (builder) => {
        //Fetch Dropdown values

        builder
            .addCase(fetchSwaggerData.pending, (state) => {
                state.swaggerJSON = null;
            })
            .addCase(fetchSwaggerData.fulfilled, (state, action: PayloadAction<any>) => { // Adjust `any` to the response data type
                state.swaggerJSON = action.payload;
            })
            .addCase(fetchSwaggerData.rejected, (state, action) => {
                state.swaggerJSON = null;
            });


        builder
            .addCase(fetchSchemaData.pending, (state) => {
                state.schemaLoader = true; // You can manage loading state if necessary
                state.schemaError = null;
            })
            .addCase(fetchSchemaData.fulfilled, (state, action: PayloadAction<any>) => { // Adjust `any` to the response data type
                state.schemaData = action.payload;
                state.schemaLoader = false;
            })
            .addCase(fetchSchemaData.rejected, (state, action) => {
                state.schemaError = action.error.message || 'An error occurred';
                state.schemaLoader = false;
            });

        //Fetch Grid Data
        builder
            .addCase(fetchContentTableData.pending, (state) => {
                //state.schemaError = null;
                state.gridLoader = true;
                state.gridData = { ...gridDefaultVal };
            })
            .addCase(fetchContentTableData.fulfilled, (state, action: PayloadAction<any>) => { // Adjust `any` to the response data type
                //state.schemaLoader = false;
                state.gridData = action.payload;
                state.gridLoader = false;
            })
            .addCase(fetchContentTableData.rejected, (state, action) => {
                state.gridLoader = false;
                toast.error('Something went wrong!')
            });


        //Fetch Grid Data
        builder
            .addCase(uploadFile.pending, (state) => {
                //state.schemaError = null;
            })
            .addCase(uploadFile.fulfilled, (state, action: PayloadAction<any>) => { // Adjust `any` to the response data type
                //state.schemaLoader = false;
                //console.log("file upload Success !")
            })
            .addCase(uploadFile.rejected, (state, action) => {
                // state.schemaError = action.error.message || 'An error occurred';
                //state.schemaLoader = false;
                //console.error("Error fetching content table data : ", action.error.message || 'An error occurred');
            });


        //Fetch Grid Data
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
                if (action.payload.status === 'Success')
                    toast.success("File deleted successfully.")
                else
                    toast.error(action.payload.message)
            })
            .addCase(deleteProcessedFile.rejected, (state, action) => {
                const processId = action.meta.arg.processId;
                if (processId) {
                    state.deleteFilesLoader = state.deleteFilesLoader.filter(id => id !== processId);
                    toast.error("Failed to delete the file. Please try again.")
                }
            });
    },
});

export const { setSchemaSelectedOption, setSelectedGridRow, setRefreshGrid } = leftPanelSlice.actions;
export default leftPanelSlice.reducer;
