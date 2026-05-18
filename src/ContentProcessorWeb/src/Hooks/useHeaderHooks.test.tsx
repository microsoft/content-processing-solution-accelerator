// Copyright (c) Microsoft Corporation.
// Licensed under the MIT License.

/**
 * @file Tests for useHeaderHooks — Ctrl+D / ⌘+D keyboard shortcut and
 * the Header presentational component.
 */

import React from 'react';
import { renderHook, act } from '@testing-library/react';
import { screen } from '@testing-library/react';
import { renderWithProviders } from '../test-utils';
import { useHeaderHooks, Header } from './useHeaderHooks';

// ── useHeaderHooks ─────────────────────────────────────────────────────

describe('useHeaderHooks', () => {
  it('should return a shortcut label', () => {
    const toggleTheme = jest.fn();
    const { result } = renderHook(() =>
      useHeaderHooks({ toggleTheme, isDarkMode: false })
    );
    // Should be either "Ctrl+D" or "⌘+D" depending on platform
    expect(result.current.shortcutLabel).toMatch(/Ctrl\+D|⌘\+D/);
  });

  it('should call toggleTheme when Ctrl+D is pressed', () => {
    const toggleTheme = jest.fn();
    renderHook(() =>
      useHeaderHooks({ toggleTheme, isDarkMode: false })
    );

    act(() => {
      window.dispatchEvent(
        new KeyboardEvent('keydown', { key: 'd', ctrlKey: true })
      );
    });

    expect(toggleTheme).toHaveBeenCalledTimes(1);
  });

  it('should not call toggleTheme for other key combos', () => {
    const toggleTheme = jest.fn();
    renderHook(() =>
      useHeaderHooks({ toggleTheme, isDarkMode: false })
    );

    act(() => {
      window.dispatchEvent(
        new KeyboardEvent('keydown', { key: 'a', ctrlKey: true })
      );
    });

    expect(toggleTheme).not.toHaveBeenCalled();
  });

  it('should remove the event listener on unmount', () => {
    const toggleTheme = jest.fn();
    const { unmount } = renderHook(() =>
      useHeaderHooks({ toggleTheme, isDarkMode: false })
    );

    unmount();

    act(() => {
      window.dispatchEvent(
        new KeyboardEvent('keydown', { key: 'd', ctrlKey: true })
      );
    });

    expect(toggleTheme).not.toHaveBeenCalled();
  });
});

// ── Header component ───────────────────────────────────────────────────

describe('Header', () => {
  it('should render the title', () => {
    renderWithProviders(
      <Header avatarSrc="/logo.png" title="Content Processor" />
    );
    expect(screen.getByText('Content Processor')).toBeInTheDocument();
  });

  it('should render the subtitle when provided', () => {
    renderWithProviders(
      <Header avatarSrc="/logo.png" title="App" subtitle="Admin" />
    );
    expect(screen.getByText(/Admin/)).toBeInTheDocument();
  });

  it('should render the badge when provided', () => {
    renderWithProviders(
      <Header avatarSrc="/logo.png" title="App" badge="Beta" />
    );
    expect(screen.getByText('Beta')).toBeInTheDocument();
  });

  it('should render children', () => {
    renderWithProviders(
      <Header avatarSrc="/logo.png" title="App">
        <nav data-testid="nav">Navigation</nav>
      </Header>
    );
    expect(screen.getByTestId('nav')).toBeInTheDocument();
  });

  it('should contain a link to /default', () => {
    renderWithProviders(
      <Header avatarSrc="/logo.png" title="App" />
    );
    const link = screen.getByRole('link');
    expect(link).toHaveAttribute('href', '/default');
  });
});
