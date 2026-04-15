// Copyright (c) Microsoft Corporation.
// Licensed under the MIT License.

/**
 * @file Tests for useFileType — MIME type resolution based on file extension.
 */

import { renderHook } from '@testing-library/react';
import useFileType from './useFileType';
import type { FileWithExtension } from './useFileType';

// ── getMimeType (via hook) ─────────────────────────────────────────────

describe('useFileType', () => {
    describe('fileType state from hook', () => {
        it('should return an empty string when file is null', () => {
            const { result } = renderHook(() => useFileType(null));
            expect(result.current.fileType).toBe('');
        });

        it('should resolve PDF files', () => {
            const file: FileWithExtension = { name: 'report.pdf' };
            const { result } = renderHook(() => useFileType(file));
            expect(result.current.fileType).toBe('application/pdf');
        });

        it('should resolve JPEG files (jpg)', () => {
            const file: FileWithExtension = { name: 'photo.jpg' };
            const { result } = renderHook(() => useFileType(file));
            expect(result.current.fileType).toBe('image/jpeg');
        });

        it('should resolve JPEG files (jpeg)', () => {
            const file: FileWithExtension = { name: 'photo.jpeg' };
            const { result } = renderHook(() => useFileType(file));
            expect(result.current.fileType).toBe('image/jpeg');
        });

        it('should resolve PNG files', () => {
            const file: FileWithExtension = { name: 'icon.png' };
            const { result } = renderHook(() => useFileType(file));
            expect(result.current.fileType).toBe('image/png');
        });

        it('should resolve JSON files', () => {
            const file: FileWithExtension = { name: 'config.json' };
            const { result } = renderHook(() => useFileType(file));
            expect(result.current.fileType).toBe('application/json');
        });

        it('should resolve CSV files', () => {
            const file: FileWithExtension = { name: 'data.csv' };
            const { result } = renderHook(() => useFileType(file));
            expect(result.current.fileType).toBe('text/csv');
        });

        it('should resolve XML files', () => {
            const file: FileWithExtension = { name: 'schema.xml' };
            const { result } = renderHook(() => useFileType(file));
            expect(result.current.fileType).toBe('application/xml');
        });

        it('should use the file.type property when extension is unknown', () => {
            const file: FileWithExtension = { name: 'archive.tar', type: 'application/x-tar' };
            const { result } = renderHook(() => useFileType(file));
            expect(result.current.fileType).toBe('application/x-tar');
        });

        it('should return application/octet-stream for completely unknown files', () => {
            const file: FileWithExtension = { name: 'binary.xyz' };
            const { result } = renderHook(() => useFileType(file));
            expect(result.current.fileType).toBe('application/octet-stream');
        });

        it('should handle case-insensitive extensions', () => {
            const file: FileWithExtension = { name: 'IMAGE.PNG' };
            const { result } = renderHook(() => useFileType(file));
            expect(result.current.fileType).toBe('image/png');
        });

        it('should handle files with multiple dots in the name', () => {
            const file: FileWithExtension = { name: 'my.report.final.pdf' };
            const { result } = renderHook(() => useFileType(file));
            expect(result.current.fileType).toBe('application/pdf');
        });
    });

    // ── getMimeType helper (returned from hook) ──────────────────────────

    describe('getMimeType helper', () => {
        it('should be a callable function', () => {
            const { result } = renderHook(() => useFileType(null));
            expect(typeof result.current.getMimeType).toBe('function');
        });

        it('should resolve independently of hook state', () => {
            const { result } = renderHook(() => useFileType(null));
            expect(result.current.getMimeType({ name: 'doc.txt' })).toBe('text/plain');
        });

        it('should return application/octet-stream for files without extension', () => {
            const { result } = renderHook(() => useFileType(null));
            expect(result.current.getMimeType({ name: 'noext' })).toBe('application/octet-stream');
        });
    });

    // ── Re-render behavior ──────────────────────────────────────────────

    describe('re-render with new file', () => {
        it('should update fileType when file prop changes', () => {
            const { result, rerender } = renderHook(
                ({ file }: { file: FileWithExtension | null }) => useFileType(file),
                { initialProps: { file: { name: 'a.pdf' } } }
            );
            expect(result.current.fileType).toBe('application/pdf');

            rerender({ file: { name: 'b.png' } });
            expect(result.current.fileType).toBe('image/png');
        });
    });
});
