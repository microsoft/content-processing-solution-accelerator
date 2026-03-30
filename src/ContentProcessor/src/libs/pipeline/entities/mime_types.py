# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""MIME type constants, file-extension mappings, and detection logic.

Used across the pipeline to identify content types of source files and
processed artifacts.
"""

import os


class MimeTypes:
    """String constants for common MIME types."""

    PlainText = "text/plain"
    MarkDown = "text/markdown"
    MarkDownOld1 = "text/x-markdown"
    MarkDownOld2 = "text/plain-markdown"
    Html = "text/html"
    XHTML = "application/xhtml+xml"
    XML = "application/xml"
    XML2 = "text/xml"
    JSONLD = "application/ld+json"
    CascadingStyleSheet = "text/css"
    JavaScript = "text/javascript"
    BourneShellScript = "application/x-sh"
    ImageBmp = "image/bmp"
    ImageGif = "image/gif"
    ImageJpeg = "image/jpeg"
    ImagePng = "image/png"
    ImageTiff = "image/tiff"
    ImageWebP = "image/webp"
    ImageSVG = "image/svg+xml"
    WebPageUrl = "text/x-uri"
    TextEmbeddingVector = "float[]"
    Json = "application/json"
    CSVData = "text/csv"
    Pdf = "application/pdf"
    RTFDocument = "application/rtf"
    MsWord = "application/msword"
    MsWordX = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    MsPowerPoint = "application/vnd.ms-powerpoint"
    MsPowerPointX = (
        "application/vnd.openxmlformats-officedocument.presentationml.presentation"
    )
    MsExcel = "application/vnd.ms-excel"
    MsExcelX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    OpenDocumentText = "application/vnd.oasis.opendocument.text"
    OpenDocumentSpreadsheet = "application/vnd.oasis.opendocument.spreadsheet"
    OpenDocumentPresentation = "application/vnd.oasis.opendocument.presentation"
    ElectronicPublicationZip = "application/epub+zip"
    AudioAAC = "audio/aac"
    AudioMP3 = "audio/mpeg"
    AudioWaveform = "audio/wav"
    AudioOGG = "audio/ogg"
    AudioOpus = "audio/opus"
    AudioWEBM = "audio/webm"
    VideoMP4 = "video/mp4"
    VideoMPEG = "video/mpeg"
    VideoOGG = "video/ogg"
    VideoOGGGeneric = "application/ogg"
    VideoWEBM = "video/webm"
    ArchiveTar = "application/x-tar"
    ArchiveGzip = "application/gzip"
    ArchiveZip = "application/zip"
    ArchiveRar = "application/vnd.rar"
    Archive7Zip = "application/x-7z-compressed"


class FileExtensions:
    """String constants for common file extensions."""

    PlainText = ".txt"
    MarkDown = ".md"
    Htm = ".htm"
    Html = ".html"
    XHTML = ".xhtml"
    XML = ".xml"
    JSONLD = ".jsonld"
    CascadingStyleSheet = ".css"
    JavaScript = ".js"
    BourneShellScript = ".sh"
    ImageBmp = ".bmp"
    ImageGif = ".gif"
    ImageJpeg = ".jpeg"
    ImageJpg = ".jpg"
    ImagePng = ".png"
    ImageTiff = ".tiff"
    ImageTiff2 = ".tif"
    ImageWebP = ".webp"
    ImageSVG = ".svg"
    WebPageUrl = ".url"
    TextEmbeddingVector = ".text_embedding"
    Json = ".json"
    CSVData = ".csv"
    Pdf = ".pdf"
    RTFDocument = ".rtf"
    MsWord = ".doc"
    MsWordX = ".docx"
    MsPowerPoint = ".ppt"
    MsPowerPointX = ".pptx"
    MsExcel = ".xls"
    MsExcelX = ".xlsx"
    OpenDocumentText = ".odt"
    OpenDocumentSpreadsheet = ".ods"
    OpenDocumentPresentation = ".odp"
    ElectronicPublicationZip = ".epub"
    AudioAAC = ".aac"
    AudioMP3 = ".mp3"
    AudioWaveform = ".wav"
    AudioOGG = ".oga"
    AudioOpus = ".opus"
    AudioWEBM = ".weba"
    VideoMP4 = ".mp4"
    VideoMPEG = ".mpeg"
    VideoOGG = ".ogv"
    VideoOGGGeneric = ".ogx"
    VideoWEBM = ".webm"
    ArchiveTar = ".tar"
    ArchiveGzip = ".gz"
    ArchiveZip = ".zip"
    ArchiveRar = ".rar"
    Archive7Zip = ".7z"


class MimeTypeException(Exception):
    def __init__(self, message, is_transient):
        super().__init__(message)
        self.is_transient = is_transient


class MimeTypesDetection:
    """Look up MIME types from file extensions using a static mapping."""

    _extension_types = {
        FileExtensions.PlainText: MimeTypes.PlainText,
        FileExtensions.MarkDown: MimeTypes.MarkDown,
        FileExtensions.Htm: MimeTypes.Html,
        FileExtensions.Html: MimeTypes.Html,
        FileExtensions.XHTML: MimeTypes.XHTML,
        FileExtensions.XML: MimeTypes.XML,
        FileExtensions.JSONLD: MimeTypes.JSONLD,
        FileExtensions.CascadingStyleSheet: MimeTypes.CascadingStyleSheet,
        FileExtensions.JavaScript: MimeTypes.JavaScript,
        FileExtensions.BourneShellScript: MimeTypes.BourneShellScript,
        FileExtensions.ImageBmp: MimeTypes.ImageBmp,
        FileExtensions.ImageGif: MimeTypes.ImageGif,
        FileExtensions.ImageJpeg: MimeTypes.ImageJpeg,
        FileExtensions.ImageJpg: MimeTypes.ImageJpeg,
        FileExtensions.ImagePng: MimeTypes.ImagePng,
        FileExtensions.ImageTiff: MimeTypes.ImageTiff,
        FileExtensions.ImageTiff2: MimeTypes.ImageTiff,
        FileExtensions.ImageWebP: MimeTypes.ImageWebP,
        FileExtensions.ImageSVG: MimeTypes.ImageSVG,
        FileExtensions.WebPageUrl: MimeTypes.WebPageUrl,
        FileExtensions.TextEmbeddingVector: MimeTypes.TextEmbeddingVector,
        FileExtensions.Json: MimeTypes.Json,
        FileExtensions.CSVData: MimeTypes.CSVData,
        FileExtensions.Pdf: MimeTypes.Pdf,
        FileExtensions.RTFDocument: MimeTypes.RTFDocument,
        FileExtensions.MsWord: MimeTypes.MsWord,
        FileExtensions.MsWordX: MimeTypes.MsWordX,
        FileExtensions.MsPowerPoint: MimeTypes.MsPowerPoint,
        FileExtensions.MsPowerPointX: MimeTypes.MsPowerPointX,
        FileExtensions.MsExcel: MimeTypes.MsExcel,
        FileExtensions.MsExcelX: MimeTypes.MsExcelX,
        FileExtensions.OpenDocumentText: MimeTypes.OpenDocumentText,
        FileExtensions.OpenDocumentSpreadsheet: MimeTypes.OpenDocumentSpreadsheet,
        FileExtensions.OpenDocumentPresentation: MimeTypes.OpenDocumentPresentation,
        FileExtensions.ElectronicPublicationZip: MimeTypes.ElectronicPublicationZip,
        FileExtensions.AudioAAC: MimeTypes.AudioAAC,
        FileExtensions.AudioMP3: MimeTypes.AudioMP3,
        FileExtensions.AudioWaveform: MimeTypes.AudioWaveform,
        FileExtensions.AudioOGG: MimeTypes.AudioOGG,
        FileExtensions.AudioOpus: MimeTypes.AudioOpus,
        FileExtensions.AudioWEBM: MimeTypes.AudioWEBM,
        FileExtensions.VideoMP4: MimeTypes.VideoMP4,
        FileExtensions.VideoMPEG: MimeTypes.VideoMPEG,
        FileExtensions.VideoOGG: MimeTypes.VideoOGG,
        FileExtensions.VideoOGGGeneric: MimeTypes.VideoOGGGeneric,
        FileExtensions.VideoWEBM: MimeTypes.VideoWEBM,
        FileExtensions.ArchiveTar: MimeTypes.ArchiveTar,
        FileExtensions.ArchiveGzip: MimeTypes.ArchiveGzip,
        FileExtensions.ArchiveZip: MimeTypes.ArchiveZip,
        FileExtensions.ArchiveRar: MimeTypes.ArchiveRar,
        FileExtensions.Archive7Zip: MimeTypes.Archive7Zip,
    }

    @staticmethod
    def get_file_type(filename):
        """
        Determine the MIME type of a file based on its extension.

        Args:
            filename (str): The name of the file whose MIME type is to be determined.

        Raises:
            MimeTypeException: If the file extension is not supported.

        Returns:
            str: The MIME type corresponding to the file extension.
        """
        extension = os.path.splitext(filename)[1]
        if extension in MimeTypesDetection._extension_types:
            return MimeTypesDetection._extension_types[extension]
        raise MimeTypeException(
            f"File type not supported: {filename}", is_transient=False
        )

    @staticmethod
    def try_get_file_type(filename):
        """
        Tries to get the MIME type of a file based on its extension.

        Args:
            filename (str): The name of the file whose MIME type is to be determined.

        Returns:
            str or None: The MIME type if the extension is recognized, otherwise None.
        """
        extension = os.path.splitext(filename)[1]
        return MimeTypesDetection._extension_types.get(extension, None)
