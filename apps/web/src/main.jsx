import React from "react";
import { createRoot } from "react-dom/client";
import { inject } from '@vercel/analytics';
import App from "./App.jsx";
import "./styles.css";

inject();

createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
