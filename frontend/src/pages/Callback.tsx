import React, { useEffect, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { Box, Paper, Typography, CircularProgress } from "@mui/material";
import { saveTokens } from "../utils/auth";
import toast from "react-hot-toast";

export const Callback: React.FC = () => {
  const [searchParams] = useSearchParams();
  const [error, setError] = useState<string | null>(null);
  const navigate = useNavigate();

  useEffect(() => {
    const accessToken = searchParams.get("access_token");
    const refreshToken = searchParams.get("refresh_token");

    if (accessToken && refreshToken) {
      saveTokens(accessToken, refreshToken, true);
      toast.success("OAuth Login Successful!");
      
      const timer = setTimeout(() => {
        navigate("/");
      }, 800);
      
      return () => clearTimeout(timer);
    } else {
      const errorMsg = searchParams.get("error") || "No tokens found in callback query parameters.";
      setError(errorMsg);
      toast.error(`Authentication failed: ${errorMsg}`);
    }
  }, [searchParams, navigate]);

  return (
    <Box
      sx={{
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        minHeight: "80vh",
        px: 2,
      }}
    >
      <Paper
        elevation={0}
        sx={{
          maxWidth: 400,
          width: "100%",
          p: 4,
          border: "1px solid",
          borderColor: "divider",
          borderRadius: 3,
          textAlign: "center",
          boxShadow: "0 1px 3px rgba(0,0,0,0.02), 0 4px 12px rgba(0,0,0,0.01)",
        }}
      >
        <Typography variant="h6" sx={{ fontWeight: 700, letterSpacing: -0.5, mb: 3 }}>
          OAuth Authentication
        </Typography>

        {error ? (
          <Box>
            <Typography variant="body2" color="error.main" sx={{ mb: 3 }}>
              {error}
            </Typography>
            <Typography
              variant="body2"
              color="primary"
              onClick={() => navigate("/login")}
              sx={{ cursor: "pointer", fontWeight: 600, "&:hover": { textDecoration: "underline" } }}
            >
              Return to Sign In
            </Typography>
          </Box>
        ) : (
          <Box sx={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 2 }}>
            <CircularProgress size={36} thickness={4} />
            <Typography variant="body2" color="text.secondary">
              Finalizing credentials and logging you in...
            </Typography>
          </Box>
        )}
      </Paper>
    </Box>
  );
};
