// Copyright (c) Microsoft Corporation.
// Licensed under the MIT License.

/**
 * @file Tests for useConsoleSuppression — silences console in non-localhost environments.
 */

import { renderHook } from '@testing-library/react';
import useConsoleSuppression from './useConsoleSuppression';

// ── Helpers ────────────────────────────────────────────────────────────

const originalHostname = window.location.hostname;
const originalEnv = process.env.REACT_APP_CONSOLE_LOG_ENABLED;

/** Override `window.location.hostname` for tests. */
function setHostname(value: string): void {
    Object.defineProperty(window, 'location', {
        writable: true,
        value: { ...window.location, hostname: value },
    });
}

describe('useConsoleSuppression', () => {
    let originalLog: typeof console.log;
    let originalWarn: typeof console.warn;
    let originalError: typeof console.error;
    let originalInfo: typeof console.info;

    beforeEach(() => {
        originalLog = console.log;
        originalWarn = console.warn;
        originalError = console.error;
        originalInfo = console.info;
    });

    afterEach(() => {
        // Restore everything
        console.log = originalLog;
        console.warn = originalWarn;
        console.error = originalError;
        console.info = originalInfo;
        setHostname(originalHostname);
        process.env.REACT_APP_CONSOLE_LOG_ENABLED = originalEnv;
    });

    it('should NOT suppress console on localhost', () => {
        setHostname('localhost');
        delete process.env.REACT_APP_CONSOLE_LOG_ENABLED;

        renderHook(() => useConsoleSuppression());

        // On localhost the hook returns early — console functions should be untouched
        expect(console.log).toBe(originalLog);
        expect(console.warn).toBe(originalWarn);
        expect(console.error).toBe(originalError);
        expect(console.info).toBe(originalInfo);
    });

    it('should NOT suppress console when REACT_APP_CONSOLE_LOG_ENABLED is "true"', () => {
        setHostname('myapp.azurewebsites.net');
        process.env.REACT_APP_CONSOLE_LOG_ENABLED = 'true';

        renderHook(() => useConsoleSuppression());

        expect(console.log).toBe(originalLog);
    });

    it('should suppress console on non-localhost when flag is not set', () => {
        setHostname('myapp.azurewebsites.net');
        delete process.env.REACT_APP_CONSOLE_LOG_ENABLED;

        renderHook(() => useConsoleSuppression());

        // Console methods should now be no-ops
        expect(console.log).not.toBe(originalLog);
        expect(console.warn).not.toBe(originalWarn);
        expect(console.error).not.toBe(originalError);
        expect(console.info).not.toBe(originalInfo);

        // Verify they don't throw
        expect(() => console.log('test')).not.toThrow();
        expect(() => console.warn('test')).not.toThrow();
        expect(() => console.error('test')).not.toThrow();
        expect(() => console.info('test')).not.toThrow();
    });

    it('should restore console methods on unmount', () => {
        setHostname('myapp.azurewebsites.net');
        delete process.env.REACT_APP_CONSOLE_LOG_ENABLED;

        const { unmount } = renderHook(() => useConsoleSuppression());

        // Suppressed while mounted
        expect(console.log).not.toBe(originalLog);

        unmount();

        // Restored after unmount
        expect(console.log).toBe(originalLog);
        expect(console.warn).toBe(originalWarn);
        expect(console.error).toBe(originalError);
        expect(console.info).toBe(originalInfo);
    });
});
