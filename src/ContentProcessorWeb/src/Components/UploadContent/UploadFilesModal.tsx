// Copyright (c) Microsoft Corporation.
// Licensed under the MIT License.

/**
 * Modal dialog for importing content files via drag-and-drop or file browser.
 * Uploads files to the backend through the Redux `uploadFile` thunk and
 * displays per-file progress and error feedback.
 */

import React, { useState, useRef, useEffect } from "react";
import {
  Dialog,
  DialogSurface,
  DialogBody,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  ProgressBar,
  makeStyles,
  Combobox,
  Option,
  MessageBar,
  MessageBarTitle,
  MessageBarBody,
  tokens,
} from "@fluentui/react-components";
import { CheckmarkCircle16Filled, DismissCircle16Filled, DocumentPdfRegular, ImageRegular } from "@fluentui/react-icons";

import { useDispatch, useSelector, shallowEqual } from "react-redux";
import { setRefreshGrid, createBatch, uploadFile, submitBatchClaim } from "../../store/slices/leftPanelSlice";
import { AppDispatch, RootState } from "../../store";

import "./UploadFilesModal.styles.scss";

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
  },
  fileRow: {
    display: "flex",
    alignItems: "center",
    gap: "12px",
    marginTop: "16px",
  },
  fileInfo: {
    flex: 1,
    minWidth: 0,
  },
  schemaDropdown: {
    minWidth: "180px",
  },
  statusIcon: {
    flexShrink: 0,
  },
  fileNameGroup: {
    display: "flex",
    alignItems: "flex-start",
    gap: "8px",
    minWidth: 0,
    flex: 1,
  },
  fileTypeIcon: {
    flexShrink: 0,
    marginTop: "2px",
  },
  fileNameText: {
    flex: 1,
    minWidth: 0,
    whiteSpace: "normal",
    overflowWrap: "anywhere",
    wordBreak: "break-word",
    lineHeight: "1.3",
  },
  messageContainer: {
    display: "flex",
    flexDirection: "column" as const,
    gap: "10px",
    marginBottom: "10px",
  },
  dialogSurface: {
    maxHeight: "90vh",
    display: "flex",
    flexDirection: "column",
  },
  dialogContent: {
    flex: 1,
    minHeight: 0,
    overflow: "hidden",
    display: "flex",
    flexDirection: "column",
  },
  dialogActions: {
    justifyContent: "flex-end",
    backgroundColor: tokens.colorNeutralBackground1,
    zIndex: 1,
  },
});


/** Props for the {@link UploadFilesModal} component. */
interface UploadFilesModalProps {
  /** Whether the upload dialog is open. */
  readonly open: boolean;
  /** Callback to close the dialog. */
  readonly onClose: () => void;
}

const MAX_FILES = 10;

/** Error information for a single file upload attempt. */
interface FileError {
  /** Human-readable error message. */
  readonly message: string;
}

/** Map of file names to their upload error details. */
interface FileErrors {
  [fileName: string]: FileError;
}

interface SchemaOption {
  readonly key: string;
  readonly value: string;
}

/**
 * Modal dialog that lets users import content files via drag-and-drop or file browser.
 * Files are uploaded sequentially with per-file progress tracking.
 */
const UploadFilesModal: React.FC<UploadFilesModalProps> = ({ open, onClose }) => {

  const styles = useStyles();

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
  const [fileSchemas, setFileSchemas] = useState<{ [fileName: string]: string }>({});

  const store = useSelector((state: RootState) => ({
    schemaData: state.leftPanel.schemaData,
    schemaSelectedOption: state.leftPanel.schemaSelectedOption,
    page_size: state.leftPanel.gridData.page_size,
    pageSize: state.leftPanel.pageSize
  }), shallowEqual);

  /** Schema options derived from store data. */
  const schemaOptions: SchemaOption[] = store.schemaData
    .map((item) => ({
      key: typeof item.Id === 'string' ? item.Id : '',
      value: typeof item.Description === 'string' ? item.Description : '',
    }))
    .filter((item) => item.key !== '' && item.value !== '');

  // Clear file schemas when files change
  useEffect(() => {
    if (files.length === 0) {
      setFileSchemas({});
    }
  }, [files]);

  /** Handler for schema selection per file. */
  const handleSchemaSelect = (fileName: string, schemaId: string | undefined) => {
    setFileSchemas((prev) => ({
      ...prev,
      [fileName]: schemaId ?? '',
    }));
  };

  /** Check if all files have a schema selected. */
  const allFilesHaveSchema = files.length > 0 && files.every((file) => fileSchemas[file.name]);

  const isFileDuplicate = (newFile: File) => {
    return files.some((file) => file.name === newFile.name);
  };

  const getFileTypeIcon = (file: File) => {
    const fileName = file.name.toLowerCase();
    if (file.type === 'application/pdf' || fileName.endsWith('.pdf')) {
      return <DocumentPdfRegular />;
    }
    if (file.type.startsWith('image/') || /\.(png|jpe?g|gif|bmp|webp|tiff|svg)$/i.test(fileName)) {
      return <ImageRegular />;
    }
    return null;
  };


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

  const handleUpload = async () => {
    setUploading(true);
    let uploadCount = 0;

    const schemaCollectionId = store.schemaSelectedOption?.optionValue as string | undefined;
    if (!schemaCollectionId) {
      setError('Please select a Collection before uploading.');
      setUploading(false);
      return;
    }

    try {
      // Step 1: Create a batch for the selected collection
      const batch = await dispatch(createBatch({ schemaCollectionId })).unwrap();
      const claimId = (batch as { claim_id: string }).claim_id;

      // Step 2: Upload each file to the batch
      for (const file of files) {
        const schemaId = fileSchemas[file.name];
        if (!schemaId) continue;

        setUploadProgress((prev) => ({ ...prev, [file.name]: 0 }));

        try {
          await dispatch(uploadFile({ file, claimId, schemaId })).unwrap();
          uploadCount++;
          setUploadProgress((prev) => ({ ...prev, [file.name]: 100 }));
        } catch (uploadError: unknown) {
          const message = typeof uploadError === 'string' ? uploadError : 'Upload failed';
          setFileErrors((prev) => ({
            ...prev,
            [file.name]: { message }
          }));
          setUploadProgress((prev) => ({ ...prev, [file.name]: -1 }));
        }
      }

      // Step 3: Submit the batch claim after all files are uploaded
      if (uploadCount > 0) {
        await dispatch(submitBatchClaim({ claimProcessId: claimId })).unwrap();
      }
    } catch (batchError: unknown) {
      const message = typeof batchError === 'string' ? batchError : 'Failed to create batch';
      setError(message);
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
    setFileSchemas({});
  };
  const onCloseHandler = () => {
    resetState();
    onClose();
  };
  return (
    <Dialog open={open} modalType="modal" >
      <DialogSurface className={styles.dialogSurface}>
        <DialogBody style={{ display: "flex", flexDirection: "column", overflow: "hidden", flex: 1 }}>
        <DialogTitle>Import Content</DialogTitle>
        <DialogContent className={styles.dialogContent}>
          <div className="dialogBody">
            <div className={styles.messageContainer}>
              <MessageBar intent="warning">
                <MessageBarBody>
                  <MessageBarTitle>Selected Collection: {store.schemaSelectedOption?.optionText as string}</MessageBarTitle>
                  <br />Please import files specific to &quot;{store.schemaSelectedOption?.optionText as string}&quot;
                </MessageBarBody>
              </MessageBar>
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

            {/* File List with Schema Selection and Progress */}
            <div className="filesList">
              {error && <p className="error">{error}</p>}
              {files.length > 0 && (
                <div className="fiiles">
                  {files.map((file) => (
                    <div key={file.name} className={styles.fileRow}>
                      <div className={styles.fileInfo}>
                        <div className="file-item">
                          <div className={styles.fileNameGroup}>
                            <span className={styles.fileTypeIcon}>{getFileTypeIcon(file)}</span>
                            <strong className={styles.fileNameText}>{file.name}</strong>
                          </div>
                          <span className={styles.statusIcon}>
                            {uploadProgress[file.name] === 100 &&
                              <CheckmarkCircle16Filled className={styles.CheckmarkCircle} />
                            }
                            {fileErrors[file.name]?.message &&
                              <DismissCircle16Filled className={styles.DismissCircle} />}
                          </span>
                        </div>
                        <ProgressBar
                          className={styles.container}
                          shape="square"
                          thickness="large"
                          value={uploadProgress[file.name] || 0}
                        />
                        <p className="error">{fileErrors[file.name]?.message ?? ""}</p>
                      </div>
                      <Combobox
                        className={styles.schemaDropdown}
                        placeholder="Select Schema"
                        disabled={uploading || uploadProgress[file.name] === 100}
                        value={schemaOptions.find((opt) => opt.key === fileSchemas[file.name])?.value ?? ''}
                        onOptionSelect={(_, data) => handleSchemaSelect(file.name, data.optionValue)}
                      >
                        {schemaOptions.map((option) => (
                          <Option key={option.key} value={option.key}>
                            {option.value}
                          </Option>
                        ))}
                      </Combobox>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </DialogContent>

        <DialogActions className={styles.dialogActions}>
          <Button onClick={onCloseHandler} disabled={uploading}>
            Close
          </Button>
          <Button
            appearance="primary"
            onClick={handleUpload}
            disabled={uploading || !allFilesHaveSchema || !startUpload}
          >
            {uploading ? "Importing..." : "Import"}
          </Button>
        </DialogActions>
        </DialogBody>
      </DialogSurface>
    </Dialog>
  );
};

export default UploadFilesModal;
