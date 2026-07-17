import React, { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { useForm } from "react-hook-form";
import {
  Box,
  Paper,
  Typography,
  TextField,
  Button,
  InputAdornment,
  IconButton,
} from "@mui/material";
import VisibilityIcon from "@mui/icons-material/Visibility";
import VisibilityOffIcon from "@mui/icons-material/VisibilityOff";
import toast from "react-hot-toast";

import { apiClient } from "../api/client";
import { saveTokens } from "../utils/auth";
import type { RegisterInputs } from "../types";

export const Register: React.FC = () => {
  const navigate = useNavigate();
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);

  const {
    register,
    handleSubmit,
    watch,
    formState: { errors },
  } = useForm<RegisterInputs>({
    defaultValues: {
      full_name: "",
      email: "",
      password: "",
      confirmPassword: "",
    },
  });

  const passwordVal = watch("password");

  const onSubmit = async (data: RegisterInputs) => {
    setLoading(true);
    try {
      const res = await apiClient.post("/auth/register", {
        full_name: data.full_name,
        email: data.email,
        password: data.password,
      });

      const { access_token, refresh_token } = res.data;
      saveTokens(access_token, refresh_token, false);

      toast.success("Welcome! Registration completed successfully.");
      navigate("/");
    } catch (err: any) {
      const detail = err?.response?.data?.detail || "Registration failed. Email might be in use.";
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
            Create an Account
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Get started with DevFlow AI today
          </Typography>
        </Box>

        <form onSubmit={handleSubmit(onSubmit)}>
          <Box sx={{ display: "flex", flexDirection: "column", gap: 2.5 }}>
            <TextField
              label="Full Name"
              type="text"
              variant="outlined"
              fullWidth
              size="small"
              error={!!errors.full_name}
              helperText={errors.full_name?.message}
              {...register("full_name", {
                required: "Full name is required",
                minLength: {
                  value: 2,
                  message: "Full name must be at least 2 characters",
                },
              })}
              slotProps={{ input: { style: { borderRadius: 8 } } }}
            />

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

            <TextField
              label="Confirm Password"
              type={showPassword ? "text" : "password"}
              variant="outlined"
              fullWidth
              size="small"
              error={!!errors.confirmPassword}
              helperText={errors.confirmPassword?.message}
              {...register("confirmPassword", {
                required: "Please confirm your password",
                validate: (val) => val === passwordVal || "Passwords do not match",
              })}
              slotProps={{ input: { style: { borderRadius: 8 } } }}
            />

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
                mt: 1,
              }}
            >
              {loading ? "Creating account..." : "Sign Up"}
            </Button>
          </Box>
        </form>

        <Box sx={{ textAlign: "center", mt: 3 }}>
          <Typography variant="body2" color="text.secondary">
            Already have an account?{" "}
            <Typography
              component={Link}
              to="/login"
              variant="body2"
              color="primary"
              sx={{ fontWeight: 600, textDecoration: "none", "&:hover": { textDecoration: "underline" } }}
            >
              Sign In
            </Typography>
          </Typography>
        </Box>
      </Paper>
    </Box>
  );
};
