// Copyright (c) Microsoft Corporation.
// Licensed under the MIT License.

/**
 * Header-related hook and presentational `Header` component.
 *
 * `useHeaderHooks` manages the keyboard shortcut for theme toggling.
 * `Header` renders the logo, title, optional subtitle/badge, and child navigation elements.
 */
import React, { useEffect, useCallback, useState } from "react";

import {
  Avatar,
  Subtitle2,
  Tag,
} from "@fluentui/react-components";
import { Link } from "react-router-dom";

interface HeaderHooksProps {
  /** Callback to toggle between light and dark themes. */
  toggleTheme: () => void;
  /** Whether the UI is currently in dark mode. */
  isDarkMode: boolean;
}

/**
 * Registers a Ctrl+D / ⌘+D keyboard shortcut to toggle the theme.
 *
 * @returns An object containing the platform-appropriate `shortcutLabel`.
 */
export const useHeaderHooks = ({ toggleTheme, isDarkMode }: HeaderHooksProps) => {
  const [shortcutLabel, setShortcutLabel] = useState("Ctrl+D");

  const handleKeyPress = useCallback(
    (event: KeyboardEvent) => {
      if ((event.metaKey || event.ctrlKey) && event.key === "d") {
        toggleTheme();
        event.preventDefault(); // Prevent browser's default action (bookmarking)
        event.stopPropagation(); // Stop further propagation
      }
    },
    [toggleTheme]
  );

  useEffect(() => {
    const isMac = navigator.platform.toLowerCase().includes("mac");
    setShortcutLabel(isMac ? "⌘+D" : "Ctrl+D");

    window.addEventListener("keydown", handleKeyPress);
    return () => {
      window.removeEventListener("keydown", handleKeyPress);
    };
  }, [handleKeyPress]);

  return {
    shortcutLabel,
  };
};

/** Props for the {@link Header} presentational component. */
interface HeaderProps {
  /** Avatar image source URL. */
  avatarSrc: string;
  /** Primary header title text. */
  title: string;
  /** Optional subtitle appended after the title. */
  subtitle?: string;
  /** Optional badge label displayed next to the title. */
  badge?: string;
  /** Navigation tabs, toolbar buttons, and other header content. */
  children?: React.ReactNode;
}

/**
 * Presentational header component that renders the logo, title, and child navigation elements.
 */

export const Header: React.FC<HeaderProps> = ({
  avatarSrc,
  title,
  subtitle,
  badge,
  children,
}) => {
  return (
    <header>
      {/* Title Section */}
      <Link to="/default" style={{ textDecoration: "none", color: "inherit" }}>
      <div className="headerTitle">
        <Avatar
          image={{ src: avatarSrc }}
          shape="square"
          //color= {null}
        
        />
        <div className="headerTitleText">
        <Subtitle2 style={{ whiteSpace: "nowrap" }}>
          {title}
          {subtitle && <span style={{ fontWeight: 400 }}> | {subtitle}</span>}
        </Subtitle2>
        {badge && (
          <Tag size="small" style={{ marginTop: 4, marginLeft: '6px' }}>
            {badge}
          </Tag>
        )}
        </div>

      </div>
      </Link>

      {/* Dynamic Content */}
      {children}
    </header>
  );
};
