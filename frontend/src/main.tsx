import React from "react";
import ReactDOM from "react-dom/client";
import { ClerkProvider } from "./lib/auth";

import App from "./App";
import "./index.css";

// Retrieve Clerk Publishable Key (automatically supplied or default to local fallback for dev)
const CLERK_PUBLISHABLE_KEY = import.meta.env.VITE_CLERK_PUBLISHABLE_KEY || "pk_test_bW9jay1jbGVyay1rZXktMTAwLmNsZXJrLmFjY291bnRzLmRldiQ";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <ClerkProvider publishableKey={CLERK_PUBLISHABLE_KEY}>
      <App />
    </ClerkProvider>
  </React.StrictMode>
);
