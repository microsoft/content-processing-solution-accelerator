import { useEffect } from "react";

// Custom hook to suppress console logs, warnings, and errors in localhost
const useConsoleSuppression = () => {

  function toBoolean(value: unknown): boolean {
    return (window.location.hostname === "localhost") ? true : String(value).toLowerCase() === "true";
  }

  useEffect(() => {
    const isConsoleFlag = toBoolean(process.env.REACT_APP_CONSOLE_LOG_ENABLED);
    if (isConsoleFlag !== true) {
      // Save the original console methods
      const originalConsoleError = console.error;
      const originalConsoleWarn = console.warn;
      const originalConsoleLog = console.log;
      const originalConsoleInfo = console.info;

      // Suppress console methods
      console.error = () => { };
      console.warn = () => { };
      console.log = () => { };
      console.info = () => { };

      // Clean up when component unmounts
      return () => {
        console.error = originalConsoleError;
        console.warn = originalConsoleWarn;
        console.log = originalConsoleLog;
        console.info = originalConsoleInfo;
      };
    }
  }, []);
};

export default useConsoleSuppression;
