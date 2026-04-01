// Copyright (c) Microsoft Corporation.
// Licensed under the MIT License.

/**
 * Renders an inline document viewer that selects the correct embed strategy
 * (Office Online, native PDF, image zoom, TIFF, or generic iframe) based on
 * the file’s MIME type.
 */

import React, { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { TIFFViewer } from 'react-tiff';

import Zoom from "react-medium-image-zoom";
import "react-medium-image-zoom/dist/styles.css";

import './DocumentViewer.styles.scss';

/** Metadata describing the document to be rendered. */
interface DocumentMetadata {
  /** MIME type of the document (e.g. "application/pdf"). */
  readonly mimeType: string;
}

/** Props for the {@link DocumentViewer} component. */
interface DocumentViewerProps {
  /** Optional CSS class name applied to the outer container. */
  readonly className?: string;
  /** Document metadata containing at least the MIME type. */
  readonly metadata?: DocumentMetadata;
  /** Pre-signed URL (with SAS token) to the document blob. */
  readonly urlWithSasToken: string | undefined;
  /** Key used to force iframe re-mount when the document changes. */
  readonly iframeKey: number;
}

/**
 * Selects and renders the appropriate viewer for the given document based on MIME type.
 */
const DocumentViewer: React.FC<DocumentViewerProps> = ({ className, metadata, urlWithSasToken, iframeKey }) => {
    const { t } = useTranslation();
    const [imgError, setImageError] = useState(false);

    useEffect(() => {
        setImageError(false)
    }, [urlWithSasToken])

    const getContentComponent = () => {
        if (!metadata || !urlWithSasToken) {
            return <div className={"noDataDocContainer"}><p>{t("components.document.none", "No document available")}</p></div>;
        }

        switch (metadata.mimeType) {
            case "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet":
            case "application/vnd.ms-excel.sheet.macroEnabled.12":
            case "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
            case "application/vnd.openxmlformats-officedocument.presentationml.presentation": {
                return (
                    <iframe
                        key={iframeKey}
                        src={`https://view.officeapps.live.com/op/embed.aspx?src=${encodeURIComponent(
                            urlWithSasToken
                        )}`}
                        width="100%"
                        height="100%"
                        title={getTitle(metadata.mimeType)}
                    />
                );
            }
            case "application/pdf": {
                return <iframe style={{ border: '1px solid lightgray' }} title="PDF Viewer" key={iframeKey} src={urlWithSasToken.toString()} width="100%" height="100%" />;
            }
            case "image/jpeg":
            case "image/png":
            case "image/gif":
            case "image/bmp":
            case "image/svg+xml": {
                return <div className="imageContainer">
                    <Zoom>
                        <img src={urlWithSasToken} alt={"Document"} onError={() => setImageError(true)} width="100%" height="100%" className="document-image" />
                    </Zoom>
                </div>;
            }
            case "image/tiff": {
                return (
                    <div
                        style={{
                            width: "100%",
                            height: "100%",
                            objectFit: "contain",
                            overflowX: "scroll",
                            overflowY: "auto",
                        }}
                    >
                        <TIFFViewer tiff={urlWithSasToken} style={{ width: 100, height: 100, objectFit: "contain" }} />
                    </div>
                );
            }

            default: {
                return (
                    <iframe key={iframeKey} src={urlWithSasToken} width="100%" height="100%" title="Doc visualizer" />
                );
            }
        }
    };

    const getTitle = (mimeType: string) => {
        switch (mimeType) {
            case "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet":
            case "application/vnd.ms-excel.sheet.macroEnabled.12":
                return "Excel viewer";
            case "application/vnd.openxmlformats-officedocument.presentationml.presentation":
                return "PowerPoint viewer";
            case "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
                return "Word viewer";
            case "application/pdf":
                return "PDF Viewer";
            default:
                return "Doc visualizer";
        }
    };

    return (
        <div className={`${className} ${imgError ? 'imageErrorContainer' : ''}`}>
            {imgError ?
                <div className={"invalidImagePopup"}>
                    <span className="imgEH">We can't open this file</span>
                    <p className="imgCtn">Something went wrong.</p>
                </div>
                : getContentComponent()
            }
        </div>
    );
}

export default DocumentViewer;