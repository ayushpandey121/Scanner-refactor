import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App";
import './utils/axiosConfig.js'
import { BrowserRouter, HashRouter } from "react-router-dom";
import './styles/Constant.css';

// Detect Electron renderer environment
const isElectron = () => {
  try {
    return Boolean(window?.electron?.isElectron || process?.versions?.electron);
  } catch {
    return false;
  }
};

const Router = isElectron() ? HashRouter : BrowserRouter;

ReactDOM.createRoot(document.getElementById("root")).render(
  // <React.StrictMode>
        <Router>
          <App className="root" />
        </Router>
  // </React.StrictMode>
);
