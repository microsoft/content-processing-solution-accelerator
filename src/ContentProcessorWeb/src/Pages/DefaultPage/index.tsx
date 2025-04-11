import * as React from "react";
import PanelCenter from "./PanelCenter.tsx";
import PanelLeft from "./PanelLeft.tsx";
import PanelRight from "./PanelRight.tsx";
import './Panels.styles.scss';

const Page: React.FC = () => {
  return (
    <div className="layout">
      <div className="panelLeft">
        <PanelLeft />
      </div>

      <div className="panelCenter">
        <PanelCenter />
      </div>
      
      <div className="panelRight">
        <PanelRight />
      </div>
    </div>
  );
};

export default Page;

