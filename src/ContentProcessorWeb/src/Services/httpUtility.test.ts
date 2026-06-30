// Copyright (c) Microsoft Corporation.
// Licensed under the MIT License.

/**
 * @file Tests for httpUtility — handleApiThunk helper and httpUtility methods.
 */

import { handleApiThunk } from './httpUtility';

// ── handleApiThunk ─────────────────────────────────────────────────────

describe('handleApiThunk', () => {
    const rejectWithValue = jest.fn((reason: string) => reason);

    beforeEach(() => {
        rejectWithValue.mockClear();
        // Silence console.log from handleApiThunk's internal logging
        jest.spyOn(console, 'log').mockImplementation(() => { });
    });

    afterEach(() => {
        jest.restoreAllMocks();
    });

    it('should return data when response status is 200', async () => {
        const apiCall = Promise.resolve({ data: { id: '1' }, status: 200 });
        const result = await handleApiThunk(apiCall, rejectWithValue, 'Error');
        expect(result).toEqual({ id: '1' });
        expect(rejectWithValue).not.toHaveBeenCalled();
    });

    it('should return data when response status is 202', async () => {
        const apiCall = Promise.resolve({ data: { queued: true }, status: 202 });
        const result = await handleApiThunk(apiCall, rejectWithValue, 'Error');
        expect(result).toEqual({ queued: true });
    });

    it('should call rejectWithValue for non-200/202 status', async () => {
        const apiCall = Promise.resolve({ data: null, status: 500 });
        await handleApiThunk(apiCall, rejectWithValue, 'Server error');
        expect(rejectWithValue).toHaveBeenCalledWith('Server error. Status: 500');
    });

    it('should call rejectWithValue for 400 status', async () => {
        const apiCall = Promise.resolve({ data: null, status: 400 });
        await handleApiThunk(apiCall, rejectWithValue, 'Bad request');
        expect(rejectWithValue).toHaveBeenCalledWith('Bad request. Status: 400');
    });

    it('should handle 415 errors with data message', async () => {
        const error = { status: 415, data: { message: 'Unsupported media type' } };
        const apiCall = Promise.reject(error);
        await handleApiThunk(apiCall, rejectWithValue, 'Upload error');
        expect(rejectWithValue).toHaveBeenCalledWith('Unsupported media type');
    });

    it('should handle 404 errors with data message', async () => {
        const error = { status: 404, data: { message: 'Not found' } };
        const apiCall = Promise.reject(error);
        await handleApiThunk(apiCall, rejectWithValue, 'Fetch error');
        expect(rejectWithValue).toHaveBeenCalledWith('Not found');
    });

    it('should use fallback message for 415 without data message', async () => {
        const error = { status: 415, data: null };
        const apiCall = Promise.reject(error);
        await handleApiThunk(apiCall, rejectWithValue, 'Upload error');
        expect(rejectWithValue).toHaveBeenCalledWith('Unexpected error: Upload error');
    });

    it('should use error.message for other thrown errors', async () => {
        const error = { status: 0, message: 'Network down' };
        const apiCall = Promise.reject(error);
        await handleApiThunk(apiCall, rejectWithValue, 'Request failed');
        expect(rejectWithValue).toHaveBeenCalledWith('Network down');
    });

    it('should use fallback when error has no message', async () => {
        const error = { status: 0 };
        const apiCall = Promise.reject(error);
        await handleApiThunk(apiCall, rejectWithValue, 'Request failed');
        expect(rejectWithValue).toHaveBeenCalledWith('Unexpected error: Request failed');
    });

    it('should include the endpoint name in the console log', async () => {
        const logSpy = jest.spyOn(console, 'log');
        const apiCall = Promise.resolve({ data: {}, status: 200 });
        await handleApiThunk(apiCall, rejectWithValue, 'Error', '/api/schemavault/');
        expect(logSpy).toHaveBeenCalledWith(
            expect.stringContaining('schemavault'),
            expect.anything()
        );
    });
});
