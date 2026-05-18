// Copyright (c) Microsoft Corporation.
// Licensed under the MIT License.

/**
 * Configures and exports the Redux store along with the inferred
 * `RootState` and `AppDispatch` types used throughout the application.
 */
import { configureStore } from '@reduxjs/toolkit';

import rootReducer from './rootReducer';

export const store = configureStore({
  reducer: rootReducer,
});

export type RootState = ReturnType<typeof store.getState>;
export type AppDispatch = typeof store.dispatch;
