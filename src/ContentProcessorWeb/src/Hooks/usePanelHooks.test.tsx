// Copyright (c) Microsoft Corporation.
// Licensed under the MIT License.

/**
 * @file Tests for PanelToolbar — reusable panel header toolbar component.
 */

import React from 'react';
import { screen } from '@testing-library/react';
import { renderWithProviders } from '../test-utils';
import PanelToolbar from './usePanelHooks';

describe('PanelToolbar', () => {
  it('should render the header text', () => {
    renderWithProviders(
      <PanelToolbar icon={<span>📄</span>} header="Documents" />
    );
    expect(screen.getByText('Documents')).toBeInTheDocument();
  });

  it('should render the icon element', () => {
    renderWithProviders(
      <PanelToolbar icon={<span data-testid="icon">📄</span>} header="Docs" />
    );
    expect(screen.getByTestId('icon')).toBeInTheDocument();
  });

  it('should render children when provided', () => {
    renderWithProviders(
      <PanelToolbar icon={<span>📄</span>} header="Docs">
        <button>Action</button>
      </PanelToolbar>
    );
    expect(screen.getByText('Action')).toBeInTheDocument();
  });

  it('should render without children', () => {
    const { container } = renderWithProviders(
      <PanelToolbar icon={<span>📄</span>} header="Empty" />
    );
    expect(container.querySelector('.panelToolbar')).toBeInTheDocument();
  });
});
