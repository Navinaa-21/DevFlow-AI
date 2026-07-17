import axios from "axios";
import { getAccessToken, getRefreshToken, saveTokens, clearTokens } from "../utils/auth";

const baseURL = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

export const apiClient = axios.create({
  baseURL,
  headers: {
    "Content-Type": "application/json",
  },
});

// Request Interceptor: Inject Access Token
apiClient.interceptors.request.use(
  (config) => {
    const accessToken = getAccessToken();
    if (accessToken && config.headers) {
      config.headers.Authorization = `Bearer ${accessToken}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Response Interceptor: Auto-Refresh Expired Tokens & Centralized Redirects
apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;

    // Check if error is 401 and request has not already been retried
    if (error.response?.status === 401 && originalRequest && !originalRequest._retry) {
      originalRequest._retry = true;
      const refreshToken = getRefreshToken();

      if (refreshToken) {
        try {
          // Use isolated axios call to prevent authorization header injection loops
          const res = await axios.post(`${baseURL}/auth/refresh`, {
            refresh_token: refreshToken,
          });

          const { access_token, refresh_token } = res.data;

          // Detect whether to use localStorage or sessionStorage based on where it was found
          const isRemembered = !!localStorage.getItem("access_token");
          
          // Save new credentials
          saveTokens(access_token, refresh_token, isRemembered);

          // Retry original request with new token
          if (originalRequest.headers) {
            originalRequest.headers.Authorization = `Bearer ${access_token}`;
          }
          return apiClient(originalRequest);
        } catch (refreshError) {
          // Refresh token is expired or revoked. Discard session.
          clearTokens();
          window.location.href = "/login";
          return Promise.reject(refreshError);
        }
      }
    }

    return Promise.reject(error);
  }
);
