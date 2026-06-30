// Copyright (c) Microsoft Corporation.
// Licensed under the MIT License.

/**
 * Type definitions for the reusable Dialog/Confirmation component.
 * Shared across any consumer that renders a confirmation dialog.
 */

import { ReactNode } from 'react';

/** Describes a single action button rendered in the dialog footer. */
export interface FooterButton {
  /** Button label text. */
  readonly text: string;
  /** Fluent UI button appearance variant. */
  readonly appearance: 'primary' | 'secondary';
  /** Callback invoked when the button is clicked. */
  readonly onClick: () => void;
}

/** Props for the {@link Confirmation} dialog component. */
export interface ConfirmationProps {
  /** Dialog title displayed in the header. */
  readonly title: string;
  /** Body content — plain text or React nodes. */
  readonly content: string | ReactNode;
  /** Whether the dialog is currently visible (controlled). */
  readonly isDialogOpen: boolean;
  /** Callback to close the dialog. */
  readonly onDialogClose: () => void;
  /** Action buttons rendered in the dialog footer. */
  readonly footerButtons: FooterButton[];
}