import React from "react";
import { Body1Strong } from "@fluentui/react-components";

interface PanelToolbarProps {
  icon: React.ReactNode;
  header: string;
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
