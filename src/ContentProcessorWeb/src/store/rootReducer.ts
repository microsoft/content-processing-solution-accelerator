// Copyright (c) Microsoft Corporation.
// Licensed under the MIT License.

/**
 * Combines all feature-level slice reducers into a single root reducer
 * consumed by the Redux store.
 */
import { combineReducers } from '@reduxjs/toolkit';

import loaderSlice from './slices/loaderSlice';
import leftPanelSlice from './slices/leftPanelSlice';
import centerPanelSlice from './slices/centerPanelSlice';
import rightPanelSlice from './slices/rightPanelSlice';
import defaultPageSlice from './slices/defaultPageSlice';

const rootReducer = combineReducers({
  loader: loaderSlice,
  leftPanel: leftPanelSlice,
  centerPanel: centerPanelSlice,
  rightPanel: rightPanelSlice,
  defaultPage: defaultPageSlice,
});

export default rootReducer;
