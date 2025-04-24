import React, { useCallback, useEffect, useState } from "react";
import "../../Styles/App.css";
import { makeStyles, SelectTabData, SelectTabEvent, Tab, TabList, TabValue, Textarea, Divider, Button } from "@fluentui/react-components";
import { Field,tokens } from "@fluentui/react-components";
import PanelToolbar from "../../Hooks/usePanelHooks.tsx";
import JSONEditor from "../../Components/JSONEditor/JSONEditor"
import { useDispatch, useSelector, shallowEqual } from 'react-redux';
import { saveContentJson, fetchProcessSteps, setUpdateComments } from '../../store/slices/centerPanelSlice';
import { RootState, AppDispatch } from '../../store';
import { startLoader, stopLoader } from "../../store/slices/loaderSlice.ts";
import { fetchContentJsonData, setActiveProcessId } from '../../store/slices/centerPanelSlice';
import ProcessSteps from './Components/ProcessSteps/ProcessSteps';
import { setRefreshGrid } from "../../store/slices/leftPanelSlice.ts";

import { bundleIcon, ChevronDoubleLeft20Filled, ChevronDoubleLeft20Regular } from "@fluentui/react-icons";
const ChevronDoubleLeft = bundleIcon(ChevronDoubleLeft20Regular, ChevronDoubleLeft20Filled);
interface PanelCenterProps {
  togglePanel: (panel: string) => void;
}

const useStyles = makeStyles({
  tabContainer: {
    display: "flex",
    flexDirection: "column",
    //borderBottom: "1px solid #ddd",
    position: 'relative',
    left: '-11px'
  },
  tabContent: {
    paddingTop: '16px'
  },
  panelCenter: {
    width: '100%',
    height: '100%',
  },
  panelCenterTopSection: {
    padding: '0px 16px 16px 16px',
    boxSizing: 'border-box'
  },
  panelCenterBottomSeciton: {
    padding: '10px 16px',
    boxSizing: 'border-box',
    background: tokens.colorNeutralBackground2,
    position: 'relative'
  },
  panelLabel: {
    fontWeight: 'bold',
    color: '#424242',
    paddingLeft: '10px'
  },
  tabItemCotnent: {
    height: 'calc(100vh - 383px)',
    border: '1px solid #DBDBDB',
    overflow: 'auto',
    background: '#f6f6f6',
    padding: '5px 5px',
    boxSizing: 'border-box'
  },

  processTabItemCotnent: {
    height: 'calc(100vh - 200px)',
    border: '1px solid #DBDBDB',
    overflow: 'auto',
    background: tokens.colorNeutralBackground3,
    padding: '5px',
    boxSizing: 'border-box'
  },
  fieldLabel: {
    fontWeight: 'bold',
    color: tokens.colorNeutralForeground2,
  },
  textAreaClass: {
    minHeight: '90px',
  },
  commentsIcon: {
    position: 'absolute',
    right: '31px',
    bottom: '16px'
  },
  saveButton: {
    marginTop: '10px',
  },
  apiLoader: {
    display: 'flex',
    justifyContent: 'center',
    alignItems: 'center',
    height: '100%'
  }
})

const PanelCenter: React.FC<PanelCenterProps> = ({ togglePanel }) => {

  const styles = useStyles();
  const dispatch = useDispatch<AppDispatch>();
  const [comment, setComment] = React.useState("");
  const [selectedTab, setSelectedTab] = React.useState<TabValue>("extracted-results");
  const [ApiLoader, setApiLoader] = useState(false);
  const status = ['extract', 'processing', 'map', 'evaluate'];

  const store = useSelector((state: RootState) => ({
    processId: state.leftPanel.processId,
    comments: state.centerPanel.comments,
    contentData: state.centerPanel.contentData,
    modified_result: state.centerPanel.modified_result,
    isSavingInProgress: state.centerPanel.isSavingInProgress,
    processStepsData: state.centerPanel.processStepsData,
    selectedItem: state.leftPanel.selectedItem,
    activeProcessId: state.centerPanel.activeProcessId,
  }), shallowEqual
  );

  useEffect(() => {
    dispatch(setActiveProcessId(store.processId))
    setComment('');
  }, [store.processId])

  useEffect(() => {
    setComment(store.comments)
  }, [store.comments])


  useEffect(() => {
    const fetchContent = async () => {
      try {
        setApiLoader(true);
        await Promise.allSettled([
          dispatch(fetchContentJsonData({ processId: store.activeProcessId })),
          dispatch(fetchProcessSteps({ processId: store.activeProcessId }))
        ]);
      } catch (error) {
        console.error("Error fetching data:", error);
      } finally {
        setApiLoader(false);
      }
    }
    if ((store.activeProcessId != null || store.activeProcessId != '') && !status.includes(store.selectedItem.status) && store.selectedItem?.process_id === store.activeProcessId) {
      fetchContent();
    }
  }, [store.activeProcessId, store.selectedItem])


  const ExtractedResults = React.useCallback(() => (
    <div role="tabpanel" className={styles.tabItemCotnent} aria-labelledby="Extracted Results">
      {store.activeProcessId && !status.includes(store.selectedItem.status) ? (
        <JSONEditor
          processId={store.activeProcessId}
        />
      ) : <p style={{ textAlign: 'center' }}>No data available</p>}
    </div>
  ), [store.activeProcessId, store.selectedItem, store.contentData]);

  const ProcessHistory = useCallback(() => (
    <div role="tabpanel" className={styles.processTabItemCotnent} aria-labelledby="Process Steps">
      {ApiLoader ? <div className={styles.apiLoader}><p>Loading...</p></div>
        : (store.processStepsData?.length == 0 || status.includes(store.selectedItem.status)) ? <p style={{ textAlign: 'center' }}> No data available</p>
          : <ProcessSteps />
      }
    </div>
  ), [store.processStepsData, store.activeProcessId, styles.tabItemCotnent, ApiLoader]);

  const onTabSelect = (event: SelectTabEvent, data: SelectTabData) => {
    setSelectedTab(data.value);
  }

  const handleSave = async () => {
    try {
      dispatch(startLoader("1"));
      dispatch(setUpdateComments(comment))
      const result = await dispatch(saveContentJson({ 'processId': store.activeProcessId, 'contentJson': store.modified_result, 'comments': comment, 'savedComments': store.comments }))
      if (result?.type === 'SaveContentJSON-Comments/fulfilled') {
        dispatch(setRefreshGrid(true));
      }
    } catch (error) {
      console.error('API Error:', error);
    } finally {
      dispatch(stopLoader("1"));
    }
  }

  const IsButtonSaveDisalbedCheck = () => {
    if(!store.activeProcessId) return true;
    if (status.includes(store.selectedItem.status)) return true;
    if (Object.keys(store.modified_result).length > 0) return false;
    if (comment.trim() !== store.comments && comment.trim() !== '') return false;
    if (store.comments !== '' && comment.trim() === '') return false;
    return true;
  }

  return (
    <div className={`pc ${styles.panelCenter}`}>
      <PanelToolbar icon={null} header="Output Review">
        <Button icon={<ChevronDoubleLeft />} title="Collapse Panel" onClick={() => togglePanel('Center')} />
      </PanelToolbar>
      <div className={styles.panelCenterTopSection} >
        <div className={styles.tabContainer}>
          <TabList selectedValue={selectedTab} onTabSelect={onTabSelect} className="custom-test" >
            <Tab value="extracted-results" >Extracted Results</Tab>
            <Tab value="process-history">Process Steps</Tab>
          </TabList>
        </div>
        <Divider />
        <div className={styles.tabContent}>
          {selectedTab === "extracted-results" && <ExtractedResults />}
          {selectedTab === "process-history" && <ProcessHistory />}
        </div>
      </div>
      {selectedTab !== "process-history" &&
        <>
          <Divider />
          <div className={styles.panelCenterBottomSeciton}>
            <Field label="Comments" className={styles.fieldLabel}>
              <Textarea value={comment} onChange={(ev, data) => setComment(data.value)} className={styles.textAreaClass} size="large" />
            </Field>
            <div className="saveBtnDiv">
              {store.isSavingInProgress && <b className="msgp">Please wait data saving....</b>}
              <Button
                appearance="primary"
                className={styles.saveButton}
                onClick={handleSave}
                disabled={IsButtonSaveDisalbedCheck()}>
                Save</Button>
            </div>
          </div>
        </>
      }
    </div>
  );
};

export default PanelCenter;
