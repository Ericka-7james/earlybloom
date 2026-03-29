import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App";
import "./styles/index.css";

/**
 * Boots the React application into the root DOM node.
 *
 * The global stylesheet is loaded here so the entire application
 * shares the same design tokens, layout rules, and base UI system.
 */
ReactDOM.createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);