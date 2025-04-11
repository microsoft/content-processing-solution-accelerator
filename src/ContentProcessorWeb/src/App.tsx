import * as React from "react";
import { useEffect } from "react";
import Header from "./Components/Header/Header.tsx"; // Import Header
import "./Styles/App.css";
import HomePage from "./Pages/HomePage.tsx";
import DefaultPage from "./Pages/DefaultPage";
//import AuxiliaryPage from "./Pages/AuxiliaryPage/AuxiliaryPage.tsx";
import NotFound from "./Pages/NotFound.tsx";
import { ToastContainer } from "react-toastify";
import "react-toastify/dist/ReactToastify.css";
import {
  HashRouter as Router,
  Routes,
  Route,
  Navigate,
} from "react-router-dom";
import Spinner from "./Components/Spinner/Spinner.tsx";

import { useDispatch, useSelector, shallowEqual } from 'react-redux';
import { RootState } from './store';


type AppProps = {
  isDarkMode: boolean; // Prop to control dark mode
  toggleTheme: () => void; // Function to toggle dark mode
};

const App: React.FC<AppProps> = ({ isDarkMode, toggleTheme }) => {

  const store = useSelector((state: RootState) => ({
    loader: state.loader.loadingStack
  }), shallowEqual);

  // Apply or remove the "dark-mode" class on the body element based on isDarkMode
  useEffect(() => {
    if (isDarkMode) {
      document.body.classList.add("dark-mode");
    } else {
      document.body.classList.remove("dark-mode");
    }
  }, [isDarkMode]);

  return (
    <div className="app-container">
      <Spinner isLoading={store.loader.length > 0} label="please wait..." />
      <Router>
        <Header toggleTheme={toggleTheme} isDarkMode={isDarkMode} />

        {/* Main Layout */}
        <main>
          <Routes>
            <Route path="/" element={<Navigate to="/default" />} /> {/*Default route (i.e., landing page) */}
            <Route path="/home" element={<HomePage />} />
            <Route path="/default" element={<DefaultPage />} />
            {/* <Route path="/auxiliary" element={<AuxiliaryPage />} /> */}
            <Route path="*" element={<NotFound />} />
          </Routes>
        </main>
      </Router>
      <ToastContainer position="top-right" autoClose={3000} />
    </div>
  );
};

export default App;
