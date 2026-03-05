// Copyright (c) Microsoft Corporation.
// Licensed under the MIT License.

/**
 * Reusable toolbar component displayed at the top of each panel.
 *
 * Renders an icon, a header label, and optional child action buttons.
 */
import React from "react";

import { Body1Strong } from "@fluentui/react-components";

interface PanelToolbarProps {
  /** Icon element displayed before the header text. */
  icon: React.ReactNode;
  /** Panel header label. */
  header: string;
  /** Optional action buttons or controls rendered to the right. */
  children?: React.ReactNode;
}

const PanelToolbar: React.FC<PanelToolbarProps> = ({ icon, header, children }) => {
  return (
    <div className="panelToolbar">
      <div className="headerTitleGroup">
        {icon}
        <Body1Strong style={{ color: "var(--colorNeutralForeground2)" }}>
          {header}
        </Body1Strong>
      </div>
      {children}
    </div>
  );
};

export default PanelToolbar;
