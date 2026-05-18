// Copyright (c) Microsoft Corporation.
// Licensed under the MIT License.

/**
 * Determines the MIME type of a file based on its extension or browser-reported type.
 *
 * @param file - The file object with at least a `name` property.
 * @returns An object containing the resolved `fileType` string and a `getMimeType` helper.
 */
import { useState, useEffect } from 'react';

interface FileTypeMapping {
  [key: string]: string;
}

export interface FileWithExtension {
  name: string;
  type?: string;
}

const MIME_TYPES: FileTypeMapping = {
  'jpg': 'image/jpeg',
  'jpeg': 'image/jpeg',
  'png': 'image/png',
  'gif': 'image/gif',
  'bmp': 'image/bmp',
  'pdf': 'application/pdf',
  'txt': 'text/plain',
  'html': 'text/html',
  'csv': 'text/csv',
  'zip': 'application/zip',
  'mp3': 'audio/mp3',
  'mp4': 'video/mp4',
  'json': 'application/json',
  'xml': 'application/xml',
};

const getFileExtension = (fileName: string): string =>
  fileName.split('.').pop()?.toLowerCase() || '';

const getMimeType = (file: FileWithExtension): string => {
  const extension = getFileExtension(file.name);
  return MIME_TYPES[extension] || file.type || 'application/octet-stream';
};

const useFileType = (file: FileWithExtension | null) => {
  const [fileType, setFileType] = useState<string>('');

  useEffect(() => {
    if (file) {
      setFileType(getMimeType(file));
    }
  }, [file]);

  return {
    fileType,
    getMimeType,
  };
};

export default useFileType;
