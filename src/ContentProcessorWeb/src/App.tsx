// Copyright (c) Microsoft Corporation.
// Licensed under the MIT License.

/**
 * Root application shell that provides routing, global loading spinner, and toast notifications.
 *
 * Mounted inside the FluentProvider / Redux Provider in index.tsx.
 */
import React, { useEffect } from "react";

import { HashRouter as Router, Routes, Route, Navigate } from "react-router-dom";
import { ToastContainer } from "react-toastify";
import { useSelector, shallowEqual } from "react-redux";

import { RootState } from "./store";
import Header from "./Components/Header/Header";
import Spinner from "./Components/Spinner/Spinner";
import HomePage from "./Pages/HomePage";
import DefaultPage from "./Pages/DefaultPage";
import NotFound from "./Pages/NotFound";

import "react-toastify/dist/ReactToastify.css";
import "./Styles/App.css";

/** Props accepted by the root {@link App} component. */
interface AppProps {
  /** Whether the UI is currently rendered in dark mode. */
  readonly isDarkMode: boolean;
  /** Callback to toggle between light and dark themes. */
  readonly toggleTheme: () => void;
}

/**
 * Renders the top-level application layout including the header, route definitions,
 * a global loading spinner, and the toast notification container.
 */
const App: React.FC<AppProps> = ({ isDarkMode, toggleTheme }) => {
  const loadingStack = useSelector(
    (state: RootState) => state.loader.loadingStack,
    shallowEqual
  );

  useEffect(() => {
    document.body.classList.toggle("dark-mode", isDarkMode);
  }, [isDarkMode]);

  return (
    <div className="app-container">
      <Spinner isLoading={loadingStack.length > 0} label="please wait..." />
      <Router>
        <Header toggleTheme={toggleTheme} isDarkMode={isDarkMode} />

        <main>
          <Routes>
            <Route path="/" element={<Navigate to="/default" />} />
            <Route path="/home" element={<HomePage />} />
            <Route path="/default" element={<DefaultPage />} />
            <Route path="*" element={<NotFound />} />
          </Routes>
        </main>
      </Router>
      <ToastContainer position="top-right" autoClose={3000} />
    </div>
  );
};

export default App;
