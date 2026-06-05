import axios from "axios";

// Determine the API base URL dynamically (e.g. for Vercel production to Render backend)
let apiBaseUrl = import.meta.env.VITE_API_BASE_URL || "/api";

if (apiBaseUrl && apiBaseUrl.startsWith("http")) {
  // Ensure we append /api if it's an absolute backend URL and doesn't end with it
  if (!apiBaseUrl.endsWith("/api") && !apiBaseUrl.endsWith("/api/")) {
    apiBaseUrl = apiBaseUrl.replace(/\/$/, "") + "/api";
  }
}

const api = axios.create({
  baseURL: apiBaseUrl,
  headers: {
    "Content-Type": "application/json",
  },
});

// Optional: inject Clerk JWT token on requests if token exists
export const setAuthToken = (token: string | null) => {
  if (token) {
    api.defaults.headers.common["Authorization"] = `Bearer ${token}`;
  } else {
    delete api.defaults.headers.common["Authorization"];
  }
};

export default api;
