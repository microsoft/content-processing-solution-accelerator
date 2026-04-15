// Copyright (c) Microsoft Corporation.
// Licensed under the MIT License.

/**
 * Right panel of the Default Page layout.
 * Fetches and displays the source document for the currently selected process
 * item using the {@link DocumentViewer} component.
 */

import React, { useEffect, useState } from "react";
import { Button } from "@fluentui/react-components";
import { bundleIcon, ChevronDoubleLeft20Filled, ChevronDoubleLeft20Regular } from "@fluentui/react-icons";

import { useDispatch, useSelector, shallowEqual } from 'react-redux';
import { AppDispatch, RootState } from '../../store';
import { fetchContentFileData } from '../../store/slices/rightPanelSlice';

import PanelToolbar from "../../Hooks/usePanelHooks";
import DocumentViewer from '../../Components/DocumentViewer/DocumentViewer';
const ChevronDoubleLeft = bundleIcon(ChevronDoubleLeft20Regular, ChevronDoubleLeft20Filled);
/** Props for the {@link PanelRight} component. */
interface PanelRightProps {
  /** Callback to collapse/expand a named panel. */
  readonly togglePanel: (panel: string) => void;
}

/**
 * Renders the right panel displaying the source document for the selected process item.
 */
const PanelRight: React.FC<PanelRightProps> = ({ togglePanel }) => {

  const dispatch = useDispatch<AppDispatch>();
  const [fileData, setFileData] = useState({ 'urlWithSasToken': '', 'mimeType': '' })

  const store = useSelector((state: RootState) => ({
    processId: state.leftPanel.processId,
    fileHeaders: state.rightPanel.fileHeaders,
    blobURL: state.rightPanel.blobURL,
    rLoader: state.rightPanel.rLoader,
    fileResponse: state.rightPanel.fileResponse
  }), shallowEqual);

  const isBlobExists = () => {
    const isfileExists = store.fileResponse.find(i => i.processId === store.processId)
    return isfileExists;
  }
  useEffect(() => {
    if (store.processId !== null && store.processId !== '' && !isBlobExists()) {
      dispatch(fetchContentFileData({ processId: store.processId }))
    }
  }, [store.processId])


  useEffect(() => {
    const isExists = isBlobExists();
    if (store.fileResponse.length > 0 && isExists && isExists.processId === store.processId) {
      setFileData({ 'urlWithSasToken': isExists.blobURL, 'mimeType': isExists.headers['content-type'] })
    } else {
      setFileData({ 'urlWithSasToken': '', 'mimeType': '' })
    }
  }, [store.processId, store.fileResponse])

  return (
    <div className="pr panelRight">
      <PanelToolbar icon={null} header="Source Document">
        <Button icon={<ChevronDoubleLeft />} title="Collapse Panel" onClick={() => togglePanel('Right')} />
      </PanelToolbar>
      <div className="panelRightContent">
        {
          store.rLoader ? <div className={"right-loader"}><p>Loading...</p></div>
            :
            <DocumentViewer
              className="fullHeight"
              metadata={{ mimeType: fileData.mimeType }}
              urlWithSasToken={fileData.urlWithSasToken}
              iframeKey={1}
            />
        }
      </div>
    </div>
  );
};

export default PanelRight;
