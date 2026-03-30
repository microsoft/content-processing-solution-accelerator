// Copyright (c) Microsoft Corporation.
// Licensed under the MIT License.

/**
 * @file Tests for Confirmation dialog component.
 */

import React from 'react';
import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { renderWithProviders } from '../../test-utils';
import { Confirmation } from './DialogComponent';
import type { FooterButton } from './DialogComponentTypes';

// ── Helpers ────────────────────────────────────────────────────────────

function renderDialog(overrides: Partial<React.ComponentProps<typeof Confirmation>> = {}) {
  const defaultButtons: FooterButton[] = [
    { text: 'Confirm', appearance: 'primary', onClick: jest.fn() },
    { text: 'Cancel', appearance: 'secondary', onClick: jest.fn() },
  ];

  const defaultProps: React.ComponentProps<typeof Confirmation> = {
    title: 'Test Dialog',
    content: 'Are you sure?',
    isDialogOpen: true,
    onDialogClose: jest.fn(),
    footerButtons: defaultButtons,
    ...overrides,
  };

  return {
    ...renderWithProviders(<Confirmation {...defaultProps} />),
    props: defaultProps,
  };
}

// ── Tests ──────────────────────────────────────────────────────────────

describe('Confirmation', () => {
  it('should render the dialog title', () => {
    renderDialog();
    expect(screen.getByText('Test Dialog')).toBeInTheDocument();
  });

  it('should render the dialog content', () => {
    renderDialog();
    expect(screen.getByText('Are you sure?')).toBeInTheDocument();
  });

  it('should render all footer buttons', () => {
    renderDialog();
    expect(screen.getByText('Confirm')).toBeInTheDocument();
    expect(screen.getByText('Cancel')).toBeInTheDocument();
  });

  it('should call button onClick and onDialogClose when a button is clicked', async () => {
    const user = userEvent.setup();
    const onConfirm = jest.fn();
    const onClose = jest.fn();

    renderDialog({
      onDialogClose: onClose,
      footerButtons: [
        { text: 'Yes', appearance: 'primary', onClick: onConfirm },
      ],
    });

    await user.click(screen.getByText('Yes'));
    expect(onConfirm).toHaveBeenCalledTimes(1);
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it('should render custom React node content', () => {
    renderDialog({
      content: <span data-testid="custom-content">Custom JSX</span>,
    });
    expect(screen.getByTestId('custom-content')).toBeInTheDocument();
  });
});
