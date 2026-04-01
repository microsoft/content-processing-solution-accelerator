// Copyright (c) Microsoft Corporation.
// Licensed under the MIT License.

/**
 * Default page layout that arranges the Processing Queue (left), Output Review
 * (center), and Source Document (right) panels in a collapsible three-column layout.
 */

import * as React from "react";
import { Button } from "@fluentui/react-components";

import { useDispatch, useSelector, shallowEqual } from 'react-redux';
import { AppDispatch, RootState } from '../../store';
import { updatePanelCollapse } from "../../store/slices/defaultPageSlice";

import PanelCenter from "./PanelCenter";
import PanelLeft from "./PanelLeft";
import PanelRight from "./PanelRight";

import './Panels.styles.scss';

/**
 * Three-panel layout page with collapsible Processing Queue, Output Review,
 * and Source Document panels.
 */
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

