import React, { useEffect, useState } from "react";
import { Button } from "@fluentui/react-components";
import PanelToolbar from "../../Hooks/usePanelHooks.tsx";
import DocumentViewer from '../../Components/DocumentViewer/DocumentViewer.tsx'
import { useDispatch, useSelector,shallowEqual  } from 'react-redux';
import { AppDispatch, RootState } from '../../store';
import { fetchContentFileData } from '../../store/slices/rightPanelSlice'

interface PanelRightProps {
}

const PanelRight: React.FC<PanelRightProps> = () => {

  const dispatch = useDispatch<AppDispatch>();
  const [fileData, setFileData] = useState({ 'urlWithSasToken': '', 'mimeType': '' })

  const store = useSelector((state: RootState) => ({
    processId: state.leftPanel.processId,
    fileHeaders: state.rightPanel.fileHeaders,
    blobURL : state.rightPanel.blobURL,
    rLoader: state.rightPanel.rLoader,
    fileResponse : state.rightPanel.fileResponse
  }),shallowEqual );

  const isBlobExists = ()=>{
    const isfileExists = store.fileResponse.find(i =>i.processId == store.processId)
    return isfileExists;
  }
  useEffect(() => {
    if (store.processId != null && store.processId != '' && !isBlobExists()) {
      dispatch(fetchContentFileData({ processId: store.processId }))
    }
  }, [store.processId])

  // useEffect(() => {
  //   if (Object.keys(store.fileHeaders).length > 0) {
  //     //const fileURL = `${process.env.REACT_APP_API_BASE_URL}/contentprocessor/processed/files/${store.processId}`;
  //     setFileData({ 'urlWithSasToken': store.blobURL, 'mimeType': store.fileHeaders['content-type'] })
  //   }
  // }, [store.fileHeaders])

  useEffect(()=>{
    const isExists = isBlobExists();
    if(store.fileResponse.length > 0 && isExists && isExists.processId == store.processId){
      setFileData({ 'urlWithSasToken': isExists.blobURL, 'mimeType': isExists.headers['content-type'] })
    }
  },[store.processId, store.fileResponse])


  return (
    <div className="panelRight">
      <PanelToolbar icon={null} header="Source Document"></PanelToolbar>

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
