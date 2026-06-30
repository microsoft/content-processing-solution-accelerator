// Copyright (c) Microsoft Corporation.
// Licensed under the MIT License.

/**
 * @file Custom render function that wraps components with all app-level providers.
 *
 * Tests should import `renderWithProviders` and other RTL utilities from this file
 * instead of importing from `@testing-library/react` directly.
 */

import React, { type PropsWithChildren, type ReactElement } from 'react';
import { render, type RenderOptions } from '@testing-library/react';
import { configureStore, type EnhancedStore } from '@reduxjs/toolkit';
import { Provider } from 'react-redux';
import { MemoryRouter } from 'react-router-dom';
import { FluentProvider, webLightTheme } from '@fluentui/react-components';

import rootReducer from './store/rootReducer';
import type { RootState } from './store';

/** Options for the custom render function. */
interface ExtendedRenderOptions extends Omit<RenderOptions, 'queries'> {
  readonly preloadedState?: Partial<RootState>;
  readonly store?: EnhancedStore;
  readonly route?: string;
}

/**
 * Renders a component wrapped in Redux Provider, FluentProvider, and MemoryRouter.
 * Use this instead of bare `render()` for any component that depends on app context.
 */
export function renderWithProviders(
  ui: ReactElement,
  {
    preloadedState = {},
    store = configureStore({ reducer: rootReducer, preloadedState: preloadedState as RootState }),
    route = '/',
    ...renderOptions
  }: ExtendedRenderOptions = {},
) {
  function Wrapper({ children }: PropsWithChildren) {
    return (
      <Provider store={store}>
        <FluentProvider theme={webLightTheme}>
          <MemoryRouter initialEntries={[route]}>
            {children}
          </MemoryRouter>
        </FluentProvider>
      </Provider>
    );
  }

  return { store, ...render(ui, { wrapper: Wrapper, ...renderOptions }) };
}

// Re-export everything from RTL so tests only need one import source.
export * from '@testing-library/react';
