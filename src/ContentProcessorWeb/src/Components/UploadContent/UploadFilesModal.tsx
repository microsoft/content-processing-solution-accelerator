import React, { useState, useRef, useEffect } from "react";
import {
  Dialog,
  DialogSurface,
  DialogTitle,
  DialogContent,
  DialogActions,
} from "@fluentui/react-dialog";
import { Button } from "@fluentui/react-button";
import { Field, ProgressBar, makeStyles } from "@fluentui/react-components";
import { useDispatch, useSelector, shallowEqual } from "react-redux";
import { fetchContentTableData, setRefreshGrid, uploadFile } from "../../store/slices/leftPanelSlice";
import { AppDispatch, RootState } from "../../store";
import "./UploadFilesModal.styles.scss";

import { CheckmarkCircle16Filled, DismissCircle16Filled } from "@fluentui/react-icons";

import {
  MessageBar,
  MessageBarTitle,
  MessageBarBody,
  MessageBarIntent,
  Link,
} from "@fluentui/react-components";

const useStyles = makeStyles({
  container: {
    margin: "10px 0px",
    color: 'green'
  },

  CheckmarkCircle: {
    color: 'green'
  },
  DismissCircle: {
    color: 'red'
  }
});

const useClasses = makeStyles({
  messageContainer: {
    display: "flex",
    flexDirection: "column",
    gap: "10px",
    marginBottom: "10px"
  },
});


interface UploadFilesModalProps {
  open: boolean;
  onClose: () => void;
}

const MAX_FILES = 10;

interface FileError {
  message: string;
}

interface FileErrors {
  [fileName: string]: FileError; // Maps file names to their error messages
}

const UploadFilesModal: React.FC<UploadFilesModalProps> = ({ open, onClose }) => {

  const styles = useStyles();
  const classes = useClasses();

  const [files, setFiles] = useState<File[]>([]);
  const [startUpload, setStartUpload] = useState(false);
  const [uploadProgress, setUploadProgress] = useState<{ [key: string]: number }>({});
  const [uploading, setUploading] = useState(false);
  const [dragging, setDragging] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const dispatch = useDispatch<AppDispatch>();
  const [fileErrors, setFileErrors] = useState<FileErrors>({});
  const [error, setError] = useState('');
  const [uploadCompleted, setUploadCompleted] = useState(false);


  const intents: MessageBarIntent[] = ["warning"];
  const store = useSelector((state: RootState) => ({
    schemaSelectedOption: state.leftPanel.schemaSelectedOption,
    page_size: state.leftPanel.gridData.page_size,
    pageSize: state.leftPanel.pageSize
  }), shallowEqual);

  const isFileDuplicate = (newFile: File) => {
    return files.some((file) => file.name === newFile.name);
  };


  // Handle file selection
  const handleFileSelect = (event: React.ChangeEvent<HTMLInputElement>) => {
    if (event.target.files && !uploading) {
      const selectedFiles = Array.from(event.target.files);
      if (selectedFiles.length > MAX_FILES) {
        setError(`You can only upload up to ${MAX_FILES} files at a time.`);
        return;
      }
      setError('');

      if (uploadCompleted) {
        setFiles(selectedFiles);
        setUploadProgress({})
        setFileErrors({})
        setUploadCompleted(false)
        setStartUpload(true);
      } else {
        const newFiles = selectedFiles.filter(file => !isFileDuplicate(file));
        if (newFiles.length > 0) {
          setFiles((prevFiles) => [...prevFiles, ...newFiles]);
          setStartUpload(true);
        } else {
          setError('Some files are duplicates and will not be added.');
        }
      }
    }
  };

  // Handle Drag & Drop
  const handleDragOver = (event: React.DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    setDragging(true);
  };

  const handleDragLeave = () => {
    setDragging(false);
  };

  const handleDrop = (event: React.DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    setDragging(false);

    if (event.dataTransfer.files && !uploading) {
      const droppedFiles = Array.from(event.dataTransfer.files);

      if (droppedFiles.length > MAX_FILES) {
        setError(`You can only upload up to ${MAX_FILES} files at a time.`);
        return;
      }
      setError('');
      // Filter out duplicates from the dropped files
      if (uploadCompleted) {
        setFiles(droppedFiles);
        setUploadProgress({})
        setFileErrors({})
        setUploadCompleted(false)
        setStartUpload(true);
      } else {
        const newFiles = droppedFiles.filter(file => !isFileDuplicate(file));
        if (newFiles.length > 0) {
          setFiles((prevFiles) => [...prevFiles, ...newFiles]);
          setStartUpload(true);
        } else {
          setError('Some of the files are duplicates and will not be added.');
        }
      }

    }
  };

  // Upload files
  const handleUpload = async () => {
    setUploading(true);
    let uploadCount = 0;
    try {
      const schema = store.schemaSelectedOption?.optionValue ?? "defaultSchema";

      for (const file of files) {
        setUploadProgress((prev) => ({ ...prev, [file.name]: 0 }));

        try {
          await dispatch(uploadFile({ file, schema })).unwrap();
          uploadCount++;
          setUploadProgress((prev) => ({ ...prev, [file.name]: 100 })); // Set progress to 100% after upload
        } catch (error: any) {
          // Capture and log the error specific to the file
          setFileErrors((prev) => ({
            ...prev,
            [file.name]: { message: error }
          }));
          setUploadProgress((prev) => ({ ...prev, [file.name]: -1 })); // Optional: Indicate failure with -1 or another value
        }
      }
    } catch (error) {
      //console.error("Overall upload failed:", error);
    } finally {
      setUploading(false);
      setStartUpload(false);
      setUploadCompleted(true);
      if (fileInputRef.current) {
        fileInputRef.current.value = '';  // Reset the file input
      }
      if (uploadCount > 0)
        dispatch(setRefreshGrid(true));
    }
  };

  const handleButtonClick = () => {
    fileInputRef.current?.click(); // Open file selector
  };

  const resetState = () => {
    setFiles([])
    setStartUpload(false);
    setUploadProgress({})
    setError('');
    setUploading(false);
    setFileErrors({})
    setUploadCompleted(false);
  }
  const isSchemaSelectedOptionEmpty = !store.schemaSelectedOption || Object.keys(store.schemaSelectedOption).length === 0;
  const onCloseHandler = () => {
    resetState();
    onClose();
  }
  return (
    <Dialog open={open} modalType="alert" >
      <DialogSurface>
        <DialogTitle>Import Content</DialogTitle>
        <DialogContent>
          <div className="dialogBody">
            <div className={classes.messageContainer}>
              {intents.map((intent) => (
                <MessageBar key={intent} intent={intent}>
                  <MessageBarBody>
                    <MessageBarTitle>Selected Schema  : {store.schemaSelectedOption.optionText} </MessageBarTitle>
                    <br />Please upload files specific to "{store.schemaSelectedOption.optionText}"
                  </MessageBarBody>
                </MessageBar>
              ))}
            </div>
            {/* Drag & Drop Area with Centered Button & Message */}
            <div
              className={`drop-area ${dragging ? "dragging" : ""}`}
              onDragOver={handleDragOver}
              onDragLeave={handleDragLeave}
              onDrop={handleDrop}
              onClick={handleButtonClick}
            >
              <input
                type="file"
                ref={fileInputRef}
                style={{ display: "none" }}
                multiple
                onChange={handleFileSelect}
              />
              <div className="drop-message">
                <p>Drag & drop files here or</p>
                <Button appearance="primary">Browse Files</Button>
              </div>
            </div>

            {/* File List with Progress Bar */}
            <div className="filesList">
              {error && <p className="error">{error}</p>}
              {files.length > 0 && (
                <div className="fiiles">
                  {files.map((file) => (
                    <div key={file.name} style={{ marginTop: 16 }}>
                      <div className={"file-item"}>
                        <strong>{file.name}</strong>
                        {uploadProgress[file.name] == 100 &&
                          <CheckmarkCircle16Filled className={styles.CheckmarkCircle} />
                        }
                        {fileErrors[file.name]?.message &&
                          <DismissCircle16Filled className={styles.DismissCircle} />}
                      </div>

                      <ProgressBar
                        className={styles.container}
                        shape="square"
                        thickness="large"
                        value={uploadProgress[file.name] || 0}
                      />

                      <p className="error">{fileErrors[file.name]?.message ?? ""}</p>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </DialogContent>

        <DialogActions>
          <Button onClick={onCloseHandler} disabled={uploading}>
            Close
          </Button>
          <Button
            appearance="primary"
            onClick={handleUpload}
            disabled={uploading || isSchemaSelectedOptionEmpty || !startUpload}
          >
            {uploading ? "Uploading..." : "Upload"}
          </Button>
        </DialogActions>
      </DialogSurface>
    </Dialog>
  );
};

export default UploadFilesModal;
