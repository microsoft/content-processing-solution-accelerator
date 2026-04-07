// Copyright (c) Microsoft Corporation.
// Licensed under the MIT License.

/**
 * Center panel of the Default Page layout.
 * Provides tabbed views for Extracted Results and Process Steps (document mode)
 * and AI Summary with Gap Analysis (parent record), along with a comments
 * section and save functionality.
 */

import React, { useCallback, useEffect, useState } from "react";
import {
  makeStyles,
  SelectTabData,
  SelectTabEvent,
  Tab,
  TabList,
  TabValue,
  Textarea,
  Divider,
  Button,
  Field,
  tokens,
} from "@fluentui/react-components";
import { bundleIcon, ChevronDoubleLeft20Filled, ChevronDoubleLeft20Regular } from "@fluentui/react-icons";

import { useDispatch, useSelector, shallowEqual } from 'react-redux';
import { RootState, AppDispatch } from '../../store';
import {
  saveContentJson,
  fetchProcessSteps,
  setUpdateComments,
  fetchClaimDetails,
  saveClaimComment,
  fetchContentJsonData,
  setActiveProcessId,
  setModifiedResult,
} from '../../store/slices/centerPanelSlice';
import { startLoader, stopLoader } from "../../store/slices/loaderSlice";
import { setRefreshGrid } from "../../store/slices/leftPanelSlice";

import PanelToolbar from "../../Hooks/usePanelHooks";
import JSONEditor from "../../Components/JSONEditor/JSONEditor";
import ProcessSteps from './Components/ProcessSteps/ProcessSteps';

import "../../Styles/App.css";
const ChevronDoubleLeft = bundleIcon(ChevronDoubleLeft20Regular, ChevronDoubleLeft20Filled);
/** Props for the {@link PanelCenter} component. */
interface PanelCenterProps {
  /** Callback to collapse/expand a named panel. */
  readonly togglePanel: (panel: string) => void;
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
    color: tokens.colorNeutralForeground1,
    paddingLeft: '10px'
  },
  tabItemCotnent: {
    height: 'calc(100vh - 383px)',
    border: `1px solid ${tokens.colorNeutralStroke1}`,
    overflow: 'auto',
    background: tokens.colorNeutralBackground3,
    padding: '5px 5px',
    boxSizing: 'border-box'
  },

  processTabItemCotnent: {
    height: 'calc(100vh - 200px)',
    border: `1px solid ${tokens.colorNeutralStroke1}`,
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

/**
 * Renders the center panel with tabbed views for extracted results, process steps,
 * AI summaries (claim mode), and a comments/save section.
 */
const PanelCenter: React.FC<PanelCenterProps> = ({ togglePanel }) => {

  const styles = useStyles();
  const dispatch = useDispatch<AppDispatch>();
  const [comment, setComment] = React.useState("");
  const [claimComment, setClaimComment] = React.useState("");
  const [selectedTab, setSelectedTab] = React.useState<TabValue>("extracted-results");
  const [apiLoader, setApiLoader] = useState(false);
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
    selectionType: state.leftPanel.selectionType,
    selectedClaim: state.leftPanel.selectedClaim,
    claimDetails: state.centerPanel.claimDetails,
    claimDetailsLoader: state.centerPanel.claimDetailsLoader,
    claimCommentSaving: state.centerPanel.claimCommentSaving,
  }), shallowEqual
  );

  useEffect(() => {
    dispatch(setActiveProcessId(store.processId))
    setComment('');
    // Reset tab to appropriate default when selection changes
    if (store.selectionType === 'claim') {
      setSelectedTab('ai-summary');
    } else {
      setSelectedTab('extracted-results');
    }
  }, [store.processId, store.selectionType])

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
    // Only fetch for document selection
    if (store.selectionType === 'document' && (store.activeProcessId != null || store.activeProcessId !== '') && !status.includes(store.selectedItem.status) && store.selectedItem?.process_id === store.activeProcessId) {
      fetchContent();
    }
  }, [store.activeProcessId, store.selectedItem, store.selectionType])

  // Fetch claim details when a claim is selected or its status changes (e.g., processing → Completed)
  useEffect(() => {
    if (store.selectionType === 'claim' && store.selectedClaim?.id) {
      setClaimComment('');
      dispatch(fetchClaimDetails({ claimId: store.selectedClaim.id }));
    }
  }, [store.selectionType, store.selectedClaim?.id, store.selectedClaim?.status, dispatch])

  // Sync claim comment with API response
  useEffect(() => {
    if (store.claimDetails?.data?.process_comment !== undefined) {
      setClaimComment(store.claimDetails.data.process_comment || '');
    }
  }, [store.claimDetails])

  const getProcessGapsData = React.useCallback((): Record<string, unknown> => {
    const claimData = (store.claimDetails?.data ?? {}) as Record<string, unknown>;
    const rawProcessGaps = claimData.process_gaps;

    if (typeof rawProcessGaps === 'string') {
      try {
        return JSON.parse(rawProcessGaps) as Record<string, unknown>;
      } catch {
        return {};
      }
    }

    if (typeof rawProcessGaps === 'object' && rawProcessGaps !== null) {
      return rawProcessGaps as Record<string, unknown>;
    }

    return {};
  }, [store.claimDetails]);

  const AISummary = React.useCallback(() => {
    return (
    <div role="tabpanel" className={styles.tabItemCotnent} aria-labelledby="AI Summary">
      {store.claimDetailsLoader ? (
        <div className={styles.apiLoader}><p>Loading...</p></div>
      ) : store.claimDetails ? (
        <div style={{ padding: '16px' }}>
          <div style={{ marginBottom: '16px' }}>
            <h4 style={{ margin: '0 0 8px 0', color: tokens.colorNeutralForeground1 }}>Summary</h4>
            <p style={{ margin: 0, color: tokens.colorNeutralForeground2, whiteSpace: 'pre-wrap' }}>
              {store.claimDetails.data.process_summary || 'No summary available'}
            </p>
          </div>
        </div>
      ) : <p style={{ textAlign: 'center' }}>No claim selected</p>}
    </div>
  )}, [store.claimDetails, store.claimDetailsLoader, styles.tabItemCotnent, styles.apiLoader]);

  const GapAnalysis = React.useCallback(() => {
    const processGaps = getProcessGapsData();

    const narrativeReport = typeof processGaps.narrative_report === 'string'
      ? processGaps.narrative_report
      : '';

    return (
    <div role="tabpanel" className={styles.tabItemCotnent} aria-labelledby="Gap Analysis">
      {store.claimDetailsLoader ? (
        <div className={styles.apiLoader}><p>Loading...</p></div>
      ) : store.claimDetails ? (
        <div style={{ padding: '16px' }}>
          <div style={{ marginBottom: '16px' }}>
            <h4 style={{ margin: '0 0 8px 0', color: tokens.colorNeutralForeground1 }}>Gap Analysis</h4>
            <p style={{ margin: 0, color: tokens.colorNeutralForeground2, whiteSpace: 'pre-wrap' }}>
              {narrativeReport || 'No gaps identified'}
            </p>
          </div>
        </div>
      ) : <p style={{ textAlign: 'center' }}>No claim selected</p>}
    </div>
  )}, [getProcessGapsData, store.claimDetails, store.claimDetailsLoader, styles.tabItemCotnent, styles.apiLoader]);

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
      {apiLoader ? <div className={styles.apiLoader}><p>Loading...</p></div>
        : (store.processStepsData?.length === 0 || status.includes(store.selectedItem.status)) ? <p style={{ textAlign: 'center' }}> No data available</p>
          : <ProcessSteps />
      }
    </div>
  ), [store.processStepsData, store.activeProcessId, styles.tabItemCotnent, apiLoader]);

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

  const isButtonSaveDisabledCheck = () => {
    if(!store.activeProcessId) return true;
    if (status.includes(store.selectedItem.status)) return true;
    if (Object.keys(store.modified_result).length > 0) return false;
    if (comment.trim() !== store.comments && comment.trim() !== '') return false;
    if (store.comments !== '' && comment.trim() === '') return false;
    return true;
  }

  const isClaimSaveDisabled = () => {
    if (!store.claimDetails) return true;
    if (store.claimCommentSaving) return true;
    const savedComment = store.claimDetails?.data?.process_comment || '';
    // Enable save if comment has changed
    if (claimComment.trim() !== savedComment) return false;
    return true;
  }

  const handleClaimSave = async () => {
    if (store.selectedClaim?.id) {
      await dispatch(saveClaimComment({ claimId: store.selectedClaim.id, comment: claimComment }));
    }
  }

  // Render claim view (AI Summary + Gap Analysis tabs)
  const renderClaimView = () => (
    <>
      <div className={styles.panelCenterTopSection} >
        <div className={styles.tabContainer}>
          <TabList selectedValue={selectedTab} onTabSelect={onTabSelect} className="custom-test" >
            <Tab value="ai-summary">AI Summary</Tab>
            <Tab value="gap-analysis">AI Gap Analysis</Tab>
          </TabList>
        </div>
        <Divider />
        <div className={styles.tabContent}>
          {selectedTab === "ai-summary" && <AISummary />}
          {selectedTab === "gap-analysis" && <GapAnalysis />}
        </div>
      </div>
      {(selectedTab === "ai-summary" || selectedTab === "gap-analysis") &&
        <>
          <Divider />
          <div className={styles.panelCenterBottomSeciton}>
            <Field label="Comments" className={styles.fieldLabel}>
              <Textarea value={claimComment} onChange={(ev, data) => setClaimComment(data.value)} className={styles.textAreaClass} size="large" />
            </Field>
            <div className="saveBtnDiv">
              {store.claimCommentSaving && <b className="msgp">Please wait, saving...</b>}
              <Button
                appearance="primary"
                className={styles.saveButton}
                onClick={handleClaimSave}
                disabled={isClaimSaveDisabled()}>
                Save</Button>
            </div>
          </div>
        </>
      }
    </>
  );

  // Render document view (Extracted Results + Process Steps tabs)
  const renderDocumentView = () => (
    <>
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
                disabled={isButtonSaveDisabledCheck()}>
                Save</Button>
            </div>
          </div>
        </>
      }
    </>
  );

  return (
    <div className={`pc ${styles.panelCenter}`}>
      <PanelToolbar icon={null} header={store.selectionType === 'claim' ? <>Output Review <span style={{ fontWeight: 'normal' }}>(for Illustrative purposes only)</span></> : "Output Review"}>
        <Button icon={<ChevronDoubleLeft />} title="Collapse Panel" onClick={() => togglePanel('Center')} />
      </PanelToolbar>
      {store.selectionType === 'claim' ? renderClaimView() : renderDocumentView()}
    </div>
  );
};

export default PanelCenter;
