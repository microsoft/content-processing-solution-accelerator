// Copyright (c) Microsoft Corporation.
// Licensed under the MIT License.

/**
 * Left panel of the Default Page layout.
 * Contains the schema dropdown, import content button, refresh button,
 * and the main process queue grid.
 */

import React, { useState, useEffect } from "react";
import { Button } from "@fluentui/react-components";
import { ArrowClockwiseRegular, ArrowUploadRegular, ChevronDoubleLeft20Regular, ChevronDoubleLeft20Filled, bundleIcon } from "@fluentui/react-icons";
import { toast } from "react-toastify";

import { useDispatch, useSelector, shallowEqual } from 'react-redux';
import { fetchSchemaData, fetchSchemasetData, fetchContentTableData, setRefreshGrid, fetchSwaggerData } from '../../store/slices/leftPanelSlice';
import { AppDispatch, RootState } from '../../store';
import { startLoader, stopLoader } from "../../store/slices/loaderSlice";

import PanelToolbar from "../../Hooks/usePanelHooks";
import ProcessQueueGrid from './Components/ProcessQueueGrid/ProcessQueueGrid';
import SchemaDropdown from './Components/SchemaDropdown/SchemaDropdown';
import UploadFilesModal from "../../Components/UploadContent/UploadFilesModal";

const ChevronDoubleLeft = bundleIcon(ChevronDoubleLeft20Regular, ChevronDoubleLeft20Filled);

/** Props for the {@link PanelLeft} component. */
interface PanelLeftProps {
  /** Callback to collapse/expand a named panel. */
  readonly togglePanel: (panel: string) => void;
}

/**
 * Renders the left panel with schema selection, content import, and the process queue grid.
 */
const PanelLeft: React.FC<PanelLeftProps> = ({ togglePanel }) => {

  const [isModalOpen, setIsModalOpen] = useState(false);
  const dispatch = useDispatch<AppDispatch>();

  const store = useSelector((state: RootState) => ({
    schemaSelectedOption: state.leftPanel.schemaSelectedOption,
    page_size: state.leftPanel.gridData.page_size,
    pageSize: state.leftPanel.pageSize,
    isGridRefresh: state.leftPanel.isGridRefresh,
    gridItems: state.leftPanel.gridData.items,
  }), shallowEqual);

  useEffect(() => {
    const fetchData = async () => {
      try {
        dispatch(startLoader("1"));
        await Promise.allSettled([
          dispatch(fetchSwaggerData()).unwrap(),
          dispatch(fetchSchemaData()).unwrap(),
          dispatch(fetchSchemasetData()).unwrap(),
          dispatch(fetchContentTableData({ pageSize: store.pageSize, pageNumber: 1 })).unwrap(),
        ]);
      } catch (error) {
        console.error("Error fetching data:", error);
      } finally {
        dispatch(stopLoader("1"));
      }
    };
    fetchData();

  }, [dispatch]);

  useEffect(() => {
    if (store.isGridRefresh) {
      refreshGrid();
    }
  }, [store.isGridRefresh, dispatch]);

  // Auto-poll grid data while any claim is still processing
  useEffect(() => {
    const hasProcessingItems = store.gridItems?.some(
      (item: Record<string, unknown>) => {
        const itemStatus = item.status as string;
        return itemStatus && itemStatus !== 'Completed' && itemStatus !== 'Error';
      }
    );

    if (!hasProcessingItems) return;

    const intervalId = setInterval(() => {
      dispatch(fetchContentTableData({ pageSize: store.pageSize, pageNumber: 1 }));
    }, 10000);

    return () => clearInterval(intervalId);
  }, [store.gridItems, store.pageSize, dispatch]);

  const refreshGrid = async () => {
    try {
      dispatch(startLoader("1"));
      await dispatch(fetchContentTableData({ pageSize: store.pageSize, pageNumber: 1 })).unwrap()
    } catch (error) {
      console.error("Error fetching data:", error);
    } finally {
      dispatch(stopLoader("1"));
      dispatch(setRefreshGrid(false));
    }
  }

  const handleImportContent = () => {
    const { schemaSelectedOption } = store;
    if (Object.keys(schemaSelectedOption).length === 0) {
      toast.error("Please select collection");
      return;
    }
    setIsModalOpen(true);
  };

  return (
    <div className="panelLeft">
      <PanelToolbar icon={null} header="Processing Queue">
        <Button icon={<ChevronDoubleLeft />} title="Collapse Panel" onClick={() => togglePanel('Left')}>
        </Button>
      </PanelToolbar>
      <div className="topContainer">
        <SchemaDropdown />
        <Button appearance="primary" icon={<ArrowUploadRegular />} onClick={handleImportContent}>
          Import Document(s)
        </Button>
        <UploadFilesModal open={isModalOpen} onClose={() => setIsModalOpen(false)} />
        <Button appearance="outline" onClick={refreshGrid} icon={<ArrowClockwiseRegular />}>
          Refresh
        </Button>
      </div>
      <div className="leftcontent">
        <ProcessQueueGrid />
      </div>
    </div>
  );
};

export default PanelLeft;
