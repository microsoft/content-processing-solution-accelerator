// src/store/rootReducer.ts
import { combineReducers } from '@reduxjs/toolkit';
import loaderSlice from './slices/loaderSlice';
import leftPanelSlice from './slices/leftPanelSlice';
import centerPanelSlice from './slices/centerPanelSlice';
import rightPanelSlice from './slices/rightPanelSlice'
import defaultPageSlice from './slices/defaultPageSlice';

// Combine all reducers here
const rootReducer = combineReducers({
  loader : loaderSlice,
  leftPanel: leftPanelSlice,
  centerPanel : centerPanelSlice,
  rightPanel : rightPanelSlice,
  defaultPage : defaultPageSlice,
});

export default rootReducer;
