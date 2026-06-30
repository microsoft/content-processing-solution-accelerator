// Copyright (c) Microsoft Corporation.
// Licensed under the MIT License.

/**
 * Redux slice that tracks a stack of active loading identifiers.
 *
 * Components push an identifier when an async operation starts and pop it
 * when the operation completes, enabling a global loading spinner.
 */
import { createSlice, PayloadAction } from "@reduxjs/toolkit";

export interface LoaderState {
  /** Stack of active loading operation identifiers. */
  readonly loadingStack: string[];
}

const initialState: LoaderState = {
  loadingStack: [],
};

const loaderSlice = createSlice({
  name: "loader",
  initialState,
  reducers: {
    startLoader: (state, action: PayloadAction<string>) => {
      state.loadingStack.push(action.payload);
    },
    stopLoader: (state, action: PayloadAction<string>) => {
      state.loadingStack = state.loadingStack.filter(
        (item) => item !== action.payload
      );
    },
  },
});

export const { startLoader, stopLoader } = loaderSlice.actions;
export default loaderSlice.reducer;
