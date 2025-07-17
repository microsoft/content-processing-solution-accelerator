import React, { useState, useEffect } from "react";
import { Button } from "@fluentui/react-components";
import { ArrowClockwiseRegular, ArrowUploadRegular, ChevronDoubleLeft20Regular, ChevronDoubleLeft20Filled, bundleIcon } from "@fluentui/react-icons";
import PanelToolbar from "../../Hooks/usePanelHooks.tsx";
import ProcessQueueGrid from './Components/ProcessQueueGrid/ProcessQueueGrid.tsx';
import SchemaDropdown from './Components/SchemaDropdown/SchemaDropdown';
import UploadFilesModal from "../../Components/UploadContent/UploadFilesModal.tsx";

import { useDispatch, useSelector, shallowEqual } from 'react-redux';
import { fetchSchemaData, fetchContentTableData, setRefreshGrid, fetchSwaggerData } from '../../store/slices/leftPanelSlice.ts';
import { AppDispatch, RootState } from '../../store/index.ts';
import { startLoader, stopLoader } from "../../store/slices/loaderSlice.ts";
import { toast } from "react-toastify";

const ChevronDoubleLeft = bundleIcon(ChevronDoubleLeft20Regular, ChevronDoubleLeft20Filled);

interface PanelLeftProps {
  togglePanel: (panel: string) => void;
}

const PanelLeft: React.FC<PanelLeftProps> = ({ togglePanel }) => {

  const [isModalOpen, setIsModalOpen] = useState(false);
  const dispatch = useDispatch<AppDispatch>();

  const store = useSelector((state: RootState) => ({
    schemaSelectedOption: state.leftPanel.schemaSelectedOption,
    page_size: state.leftPanel.gridData.page_size,
    pageSize: state.leftPanel.pageSize,
    isGridRefresh: state.leftPanel.isGridRefresh,
  }), shallowEqual);

  useEffect(() => {
    const fetchData = async () => {
      try {
        dispatch(startLoader("1"));
        await Promise.allSettled([
          dispatch(fetchSwaggerData()).unwrap(),
          dispatch(fetchSchemaData()).unwrap(),
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
      toast.error("Please Select Schema");
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
          Import Content
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
