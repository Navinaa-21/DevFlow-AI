/**
 * Authentication and token storage utility helper module.
 * Manages JWT tokens in localStorage (for persistent remember-me logins)
 * and sessionStorage (for temporary browser sessions).
 */

export const getAccessToken = (): string | null => {
  return localStorage.getItem("access_token") || sessionStorage.getItem("access_token");
};

export const getRefreshToken = (): string | null => {
  return localStorage.getItem("refresh_token") || sessionStorage.getItem("refresh_token");
};

export const saveTokens = (
  accessToken: string,
  refreshToken: string,
  rememberMe: boolean = false
): void => {
  // Clear any existing tokens first to avoid duplication
  clearTokens();

  const storage = rememberMe ? localStorage : sessionStorage;
  storage.setItem("access_token", accessToken);
  storage.setItem("refresh_token", refreshToken);
};

export const clearTokens = (): void => {
  localStorage.removeItem("access_token");
  localStorage.removeItem("refresh_token");
  sessionStorage.removeItem("access_token");
  sessionStorage.removeItem("refresh_token");
};

export const isAuthenticated = (): boolean => {
  return !!getAccessToken();
};
