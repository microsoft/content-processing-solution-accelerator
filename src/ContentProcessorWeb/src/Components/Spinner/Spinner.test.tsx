// Copyright (c) Microsoft Corporation.
// Licensed under the MIT License.

/**
 * @file Tests for Spinner — loading overlay component.
 */

import React from 'react';
import { render, screen } from '@testing-library/react';
import Spinner from './Spinner';

describe('Spinner', () => {
  it('should render nothing when isLoading is false', () => {
    const { container } = render(<Spinner isLoading={false} />);
    expect(container.firstChild).toBeNull();
  });

  it('should render the overlay when isLoading is true', () => {
    const { container } = render(<Spinner isLoading={true} />);
    expect(container.querySelector('.overlay')).toBeInTheDocument();
    expect(container.querySelector('.spinner')).toBeInTheDocument();
  });

  it('should display the label when provided', () => {
    render(<Spinner isLoading={true} label="Loading data..." />);
    expect(screen.getByText('Loading data...')).toBeInTheDocument();
  });

  it('should not display a label element when label is omitted', () => {
    const { container } = render(<Spinner isLoading={true} />);
    expect(container.querySelector('.loader-label')).not.toBeInTheDocument();
  });

  it('should not display a label element when label is empty', () => {
    const { container } = render(<Spinner isLoading={true} label="" />);
    expect(container.querySelector('.loader-label')).not.toBeInTheDocument();
  });
});
