import * as React from "react";
import PanelCenter from "./PanelCenter.tsx";
import PanelLeft from "./PanelLeft.tsx";
import PanelRight from "./PanelRight.tsx";
import './Panels.styles.scss';

import { useDispatch, useSelector, shallowEqual } from 'react-redux';
import { AppDispatch, RootState } from '../../store/index.ts';
import { updatePanelCollapse } from "../../store/slices/defaultPageSlice.ts";

import { makeStyles, Button } from "@fluentui/react-components";

const Page: React.FC = () => {

  const dispatch = useDispatch<AppDispatch>();

  const store = useSelector((state: RootState) => ({
    isLeftPanelCollapse: state.defaultPage.isLeftPanelCollapse,
    isRightPanelCollapse: state.defaultPage.isRightPanelCollapse,
    isCenterPanelCollapse: state.defaultPage.isCenterPanelCollapse,
  }), shallowEqual);

  const togglePanel = (panel: string) => {
    dispatch(updatePanelCollapse(panel))
  }
  return (
    <div className="layout">
      <div className={`panelLeftLayout ${store.isLeftPanelCollapse ? 'collapse' : 'expand'}`} >
        <div className="collapseButtonDiv ">
          <Button className="rotate-button" title="Expand Panel" onClick={() => togglePanel('Left')} appearance="primary">
            Processing Queue
          </Button>
        </div>
        <PanelLeft togglePanel={togglePanel} />
      </div>

      <div className={`panelCenter ${store.isCenterPanelCollapse ? 'collapse' : 'expand'}`}>
        <div className="collapseButtonDiv">
          <Button className="rotate-button" title="Expand Panel" onClick={() => togglePanel('Center')} appearance="primary">Output Review </Button>
        </div>
        <PanelCenter togglePanel={togglePanel} />
      </div>

      <div className={`panelRight ${store.isRightPanelCollapse ? 'collapse' : 'expand'}`}>
        <div className="collapseButtonDiv">
          <Button className="rotate-button" title="Expand Panel" onClick={() => togglePanel('Right')} appearance="primary">Source Document</Button>
        </div>
        <PanelRight togglePanel={togglePanel} />
      </div>
    </div>
  );
};

export default Page;

