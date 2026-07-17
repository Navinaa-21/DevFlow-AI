import React from "react";
import { BrowserRouter as Router, Routes, Route, Navigate } from "react-router-dom";
import { createTheme, ThemeProvider } from "@mui/material/styles";
import CssBaseline from "@mui/material/CssBaseline";
import { Toaster } from "react-hot-toast";

import { Login } from "./pages/Login";
import { Register } from "./pages/Register";
import { ForgotPassword } from "./pages/ForgotPassword";
import { ResetPassword } from "./pages/ResetPassword";
import { Callback } from "./pages/Callback";
import { Dashboard } from "./pages/Dashboard";
import { WorkspaceList } from "./pages/WorkspaceList";
import { WorkspaceCreate } from "./pages/WorkspaceCreate";
import { WorkspaceView } from "./pages/WorkspaceView";
import { RepositoryList } from "./pages/RepositoryList";
import { RepositoryConnect } from "./pages/RepositoryConnect";
import { WorkspaceInvitation } from "./pages/WorkspaceInvitation";

import { MainLayout } from "./components/MainLayout";
import { isAuthenticated } from "./utils/auth";

// MUI Clean Enterprise Theme Setup
const theme = createTheme({
  palette: {
    primary: {
      main: "#0066cc", // Clean blue primary
      light: "#f0f7ff", // Very soft blue list highlight background
    },
    background: {
      default: "#fcfdfe", // Soft background white-gray
      paper: "#ffffff", // Crisp white components
    },
    text: {
      primary: "#1a1f36", // Slate-dark text
      secondary: "#6a737d", // Muted gray text
    },
    divider: "#eaeaea", // Soft border divider
  },
  shape: {
    borderRadius: 10, // Rounded corners (10-12px)
  },
  typography: {
    fontFamily: [
      "Inter",
      "-apple-system",
      "BlinkMacSystemFont",
      '"Segoe UI"',
      "Roboto",
      '"Helvetica Neue"',
      "Arial",
      "sans-serif",
    ].join(","),
    h5: {
      fontWeight: 700,
    },
    subtitle1: {
      fontWeight: 600,
    },
  },
  components: {
    MuiButton: {
      styleOverrides: {
        root: {
          textTransform: "none",
          boxShadow: "none",
          "&:hover": {
            boxShadow: "none",
          },
        },
      },
    },
  },
});

// Guard component checking active session and injecting Layout structure
const ProtectedRoute: React.FC<{ element: React.ReactElement }> = ({ element }) => {
  const authed = isAuthenticated();
  return authed ? <MainLayout>{element}</MainLayout> : <Navigate to="/login" replace />;
};

export default function App() {
  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <Router>
        <Routes>
          {/* Public Routes */}
          <Route path="/login" element={<Login />} />
          <Route path="/register" element={<Register />} />
          <Route path="/auth/callback" element={<Callback />} />
          <Route path="/invitations/:token" element={<WorkspaceInvitation />} />
          <Route path="/forgot-password" element={<ForgotPassword />} />
          <Route path="/reset-password" element={<ResetPassword />} />

          {/* Protected Routes (MainLayout wrapped) */}
          <Route path="/" element={<ProtectedRoute element={<Dashboard />} />} />
          <Route path="/workspaces" element={<ProtectedRoute element={<WorkspaceList />} />} />
          <Route path="/workspaces/new" element={<ProtectedRoute element={<WorkspaceCreate />} />} />
          <Route path="/workspaces/:workspaceId" element={<ProtectedRoute element={<WorkspaceView />} />} />
          <Route path="/workspaces/:workspaceId/connect-repos" element={<ProtectedRoute element={<RepositoryConnect />} />} />
          <Route path="/repositories" element={<ProtectedRoute element={<RepositoryList />} />} />
          <Route path="/invitations" element={<ProtectedRoute element={<WorkspaceInvitation />} />} />

          {/* Catch-all redirect */}
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </Router>
      <Toaster
        position="top-right"
        toastOptions={{
          style: {
            borderRadius: "8px",
            background: "#333",
            color: "#fff",
            fontSize: "0.875rem",
            fontFamily: "Inter, sans-serif",
          },
        }}
      />
    </ThemeProvider>
  );
}
