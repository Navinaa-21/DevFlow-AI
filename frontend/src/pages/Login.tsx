import React, { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { useForm } from "react-hook-form";
import {
  Box,
  Paper,
  Typography,
  TextField,
  FormControlLabel,
  Checkbox,
  Button,
  Divider,
  InputAdornment,
  IconButton,
} from "@mui/material";
import GoogleIcon from "@mui/icons-material/Google";
import GitHubIcon from "@mui/icons-material/GitHub";
import VisibilityIcon from "@mui/icons-material/Visibility";
import VisibilityOffIcon from "@mui/icons-material/VisibilityOff";
import toast from "react-hot-toast";

import { apiClient } from "../api/client";
import { saveTokens } from "../utils/auth";
import type { LoginInputs } from "../types";

const baseURL = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

export const Login: React.FC = () => {
  const navigate = useNavigate();
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<LoginInputs>({
    defaultValues: {
      email: "",
      password: "",
      rememberMe: false,
    },
  });

  const handleOAuthLogin = (provider: "google" | "github") => {
    window.location.href = `${baseURL}/auth/login/${provider}`;
  };

  const onSubmit = async (data: LoginInputs) => {
    setLoading(true);
    try {
      const res = await apiClient.post("/auth/login", {
        email: data.email,
        password: data.password,
      });

      const { access_token, refresh_token } = res.data;
      saveTokens(access_token, refresh_token, data.rememberMe);

      toast.success("Welcome back! Login successful.");
      navigate("/");
    } catch (err: any) {
      const detail = err?.response?.data?.detail || "Invalid email or password.";
      toast.error(detail);
    } finally {
      setLoading(false);
    }
  };

  return (
    <Box
      sx={{
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        minHeight: "85vh",
        px: 2,
      }}
    >
      <Paper
        elevation={0}
        sx={{
          maxWidth: 420,
          width: "100%",
          p: { xs: 3, sm: 4 },
          border: "1px solid",
          borderColor: "divider",
          borderRadius: 3,
          boxShadow: "0 1px 3px rgba(0,0,0,0.02), 0 4px 12px rgba(0,0,0,0.01)",
        }}
      >
        <Box sx={{ textAlign: "center", mb: 3.5 }}>
          <Typography variant="h5" sx={{ fontWeight: 700, letterSpacing: -0.5, mb: 1 }}>
            Sign in to DevFlow AI
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Enter your credentials or use an OAuth provider
          </Typography>
        </Box>

        {/* OAuth Buttons */}
        <Box sx={{ display: "flex", flexDirection: "column", gap: 1.5, mb: 3.5 }}>
          <Button
            variant="outlined"
            color="inherit"
            startIcon={<GoogleIcon sx={{ color: "#ea4335" }} />}
            onClick={() => handleOAuthLogin("google")}
            sx={{
              borderRadius: 2,
              py: 1,
              textTransform: "none",
              fontWeight: 600,
              borderColor: "divider",
              "&:hover": { borderColor: "text.primary" },
            }}
          >
            Continue with Google
          </Button>
          <Button
            variant="outlined"
            color="inherit"
            startIcon={<GitHubIcon />}
            onClick={() => handleOAuthLogin("github")}
            sx={{
              borderRadius: 2,
              py: 1,
              textTransform: "none",
              fontWeight: 600,
              borderColor: "divider",
              "&:hover": { borderColor: "text.primary" },
            }}
          >
            Continue with GitHub
          </Button>
        </Box>

        <Divider sx={{ mb: 3 }}>
          <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 500 }}>
            OR CONTINUE WITH EMAIL
          </Typography>
        </Divider>

        {/* Local Login Form */}
        <form onSubmit={handleSubmit(onSubmit)}>
          <Box sx={{ display: "flex", flexDirection: "column", gap: 2.5 }}>
            <TextField
              label="Email Address"
              type="email"
              variant="outlined"
              fullWidth
              size="small"
              error={!!errors.email}
              helperText={errors.email?.message}
              {...register("email", {
                required: "Email address is required",
                pattern: {
                  value: /^[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}$/i,
                  message: "Invalid email address format",
                },
              })}
              slotProps={{ input: { style: { borderRadius: 8 } } }}
            />

            <TextField
              label="Password"
              type={showPassword ? "text" : "password"}
              variant="outlined"
              fullWidth
              size="small"
              error={!!errors.password}
              helperText={errors.password?.message}
              {...register("password", {
                required: "Password is required",
                minLength: {
                  value: 6,
                  message: "Password must be at least 6 characters",
                },
              })}
              slotProps={{
                input: {
                  style: { borderRadius: 8 },
                  endAdornment: (
                    <InputAdornment position="end">
                      <IconButton
                        aria-label="toggle password visibility"
                        onClick={() => setShowPassword(!showPassword)}
                        edge="end"
                        size="small"
                      >
                        {showPassword ? <VisibilityOffIcon /> : <VisibilityIcon />}
                      </IconButton>
                    </InputAdornment>
                  ),
                },
              }}
            />

            <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "center", mt: -1 }}>
              <FormControlLabel
                control={
                  <Checkbox
                    size="small"
                    color="primary"
                    {...register("rememberMe")}
                  />
                }
                label={
                  <Typography variant="body2" color="text.secondary">
                    Remember me
                  </Typography>
                }
              />
            </Box>

            <Button
              type="submit"
              variant="contained"
              color="primary"
              fullWidth
              disabled={loading}
              sx={{
                borderRadius: 2,
                py: 1,
                fontWeight: 700,
                textTransform: "none",
                fontSize: "0.95rem",
                boxShadow: "none",
                "&:hover": { boxShadow: "none" },
              }}
            >
              {loading ? "Signing in..." : "Sign In"}
            </Button>
          </Box>
        </form>

        <Box sx={{ textAlign: "center", mt: 3 }}>
          <Typography variant="body2" color="text.secondary">
            Don't have an account?{" "}
            <Typography
              component={Link}
              to="/register"
              variant="body2"
              color="primary"
              sx={{ fontWeight: 600, textDecoration: "none", "&:hover": { textDecoration: "underline" } }}
            >
              Sign Up
            </Typography>
          </Typography>
        </Box>
      </Paper>
    </Box>
  );
};
