// Copyright (c) Microsoft Corporation.
// Licensed under the MIT License.

/**
 * Suppresses `console.log`, `console.warn`, `console.error`, and `console.info`
 * in non-localhost environments unless the `REACT_APP_CONSOLE_LOG_ENABLED` flag is set.
 *
 * Restores the original console methods on unmount.
 */
import { useEffect } from "react";

const useConsoleSuppression = (): void => {
  const toBoolean = (value: unknown): boolean =>
    window.location.hostname === "localhost" || String(value).toLowerCase() === "true";

  useEffect(() => {
    const isConsoleFlag = toBoolean(process.env.REACT_APP_CONSOLE_LOG_ENABLED);
    if (isConsoleFlag) return;

    const originalConsoleError = console.error;
    const originalConsoleWarn = console.warn;
    const originalConsoleLog = console.log;
    const originalConsoleInfo = console.info;

    console.error = () => { };
    console.warn = () => { };
    console.log = () => { };
    console.info = () => { };

    return () => {
      console.error = originalConsoleError;
      console.warn = originalConsoleWarn;
      console.log = originalConsoleLog;
      console.info = originalConsoleInfo;
    };
  }, []);
};

export default useConsoleSuppression;
