// Copyright (c) Microsoft Corporation.
// Licensed under the MIT License.

/**
 * Application entry point that bootstraps React, Fluent UI theming,
 * MSAL authentication, and the Redux store.
 */
import React, { useEffect, useState } from "react";
import ReactDOM from "react-dom/client";

import {
  FluentProvider,
  teamsLightTheme,
  teamsDarkTheme,
  tokens,
  makeStyles,
} from "@fluentui/react-components";
import { Provider } from "react-redux";

import { store } from "./store";
import AuthProvider from "./msal-auth/AuthProvider";
import useConsoleSuppression from "./Hooks/useConsoleSuppression";
import App from "./App";

import "./Styles/index.css";

const useStyles = makeStyles({
  appContainer: {
    height: "100vh",
    backgroundColor: tokens.colorNeutralBackground3,
  },
});

/** Root component that wires up providers and manages the light / dark theme. */
const Index: React.FC = () => {
  useConsoleSuppression();

  const [isDarkMode, setIsDarkMode] = useState(() =>
    window.matchMedia("(prefers-color-scheme: dark)").matches
  );

  useEffect(() => {
    const mediaQuery = window.matchMedia("(prefers-color-scheme: dark)");
    const handleChange = (event: MediaQueryListEvent) => {
      setIsDarkMode(event.matches);
    };

    mediaQuery.addEventListener("change", handleChange);
    return () => mediaQuery.removeEventListener("change", handleChange);
  }, []);

  const toggleTheme = () => {
    setIsDarkMode((prev) => !prev);
  };

  const styles = useStyles();

  return (
    <AuthProvider>
      <Provider store={store}>
        <FluentProvider theme={isDarkMode ? teamsDarkTheme : teamsLightTheme}>
          <div className={styles.appContainer}>
            <App isDarkMode={isDarkMode} toggleTheme={toggleTheme} />
          </div>
        </FluentProvider>
      </Provider>
    </AuthProvider>
  );
};

const root = ReactDOM.createRoot(
  document.getElementById("root") as HTMLElement
);

root.render(<Index />);
