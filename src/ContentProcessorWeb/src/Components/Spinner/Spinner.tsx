// Copyright (c) Microsoft Corporation.
// Licensed under the MIT License.

/**
 * Full-screen loading overlay with a CSS spinner animation.
 * Blocks user interaction while an async operation is in progress.
 */

import React from "react";

import "./Spinner.styles.scss";

/** Props for the {@link Spinner} overlay component. */
interface SpinnerProps {
  /** Whether the loading overlay is currently visible. */
  readonly isLoading: boolean;
  /** Optional text label displayed beneath the spinner. */
  readonly label?: string;
}

/**
 * Renders a full-screen semi-transparent overlay with a spinning loader.
 * Returns `null` when `isLoading` is `false`.
 */
const Spinner: React.FC<SpinnerProps> = ({ isLoading, label }) => {
  if (!isLoading) {
    return null;
  }

  return (
    <div className="overlay">
      <div className="loader">
        <div className="spinner"></div>
        {label && <div className="loader-label">{label}</div>}
      </div>
    </div>
  );
};

export default Spinner;
