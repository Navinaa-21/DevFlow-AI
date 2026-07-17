import React, { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { useForm } from "react-hook-form";
import {
  Box,
  Paper,
  TextField,
  Button,
  FormHelperText,
} from "@mui/material";
import toast from "react-hot-toast";

import { apiClient } from "../api/client";
import { PageHeader } from "../components/PageHeader";

interface WorkspaceCreateInputs {
  name: string;
  slug: string;
  logo_url: string;
  description: string;
}

export const WorkspaceCreate: React.FC = () => {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const [ownerId, setOwnerId] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    setValue,
    watch,
    formState: { errors },
  } = useForm<WorkspaceCreateInputs>({
    defaultValues: {
      name: "",
      slug: "",
      logo_url: "",
      description: "",
    },
  });

  const nameVal = watch("name");

  // Generate URL friendly slug automatically when workspace name changes
  useEffect(() => {
    if (nameVal) {
      const generated = nameVal
        .toLowerCase()
        .trim()
        .replace(/[^\w\s-]/g, "") // remove non-alphanumeric/spaces/hyphens
        .replace(/[\s_]+/g, "-")  // spaces to hyphens
        .replace(/^-+|-+$/g, ""); // trim leading/trailing hyphens
      setValue("slug", generated, { shouldValidate: true });
    }
  }, [nameVal, setValue]);

  // Fetch the current owner user ID to map creator relationship
  useEffect(() => {
    apiClient
      .get("/auth/me")
      .then((res) => {
        setOwnerId(res.data.id);
      })
      .catch(() => {
        toast.error("Failed to verify authenticated user status.");
      });
  }, []);

  const onSubmit = async (data: WorkspaceCreateInputs) => {
    if (!ownerId) {
      toast.error("User identity is not verified yet. Please try again.");
      return;
    }
    setLoading(true);
    try {
      const payload = {
        name: data.name,
        slug: data.slug,
        logo_url: data.logo_url.trim() || null,
        description: data.description.trim() || null,
        owner_id: ownerId,
        is_active: true,
      };

      await apiClient.post("/workspaces", payload);
      toast.success("Workspace created successfully!");
      navigate("/workspaces");
    } catch (err: any) {
      const detail = err.response?.data?.detail || "Failed to create workspace.";
      toast.error(typeof detail === "object" ? JSON.stringify(detail) : detail);
    } finally {
      setLoading(false);
    }
  };

  return (
    <Box>
      <PageHeader
        title="Create Workspace"
        subtitle="Provision a collaborative workspace"
        breadcrumbs={[
          { label: "Workspaces", to: "/workspaces" },
          { label: "New Workspace" },
        ]}
      />

      <Box sx={{ display: "flex", justifyContent: "center" }}>
        <Paper
          elevation={0}
          sx={{
            maxWidth: 500,
            width: "100%",
            p: 4,
            border: "1px solid",
            borderColor: "divider",
            borderRadius: 3,
            boxShadow: "0 1px 3px rgba(0,0,0,0.02)",
          }}
        >
          <form onSubmit={handleSubmit(onSubmit)}>
            <Box sx={{ display: "flex", flexDirection: "column", gap: 3 }}>
              <TextField
                label="Workspace Name"
                variant="outlined"
                fullWidth
                size="small"
                error={!!errors.name}
                helperText={errors.name?.message}
                {...register("name", {
                  required: "Workspace name is required",
                  maxLength: {
                    value: 255,
                    message: "Name cannot exceed 255 characters",
                  },
                })}
                slotProps={{ input: { style: { borderRadius: 8 } } }}
              />

              <Box>
                <TextField
                  label="URL Slug"
                  variant="outlined"
                  fullWidth
                  size="small"
                  error={!!errors.slug}
                  helperText={errors.slug?.message}
                  {...register("slug", {
                    required: "Workspace URL slug is required",
                    pattern: {
                      value: /^[a-z0-9-]+$/,
                      message: "Slug can only contain lowercase alphanumeric characters and hyphens",
                    },
                    maxLength: {
                      value: 255,
                      message: "Slug cannot exceed 255 characters",
                    },
                  })}
                  slotProps={{ input: { style: { borderRadius: 8 } } }}
                />
                <FormHelperText sx={{ ml: 1, mt: 0.5 }}>
                  This acts as the unique workspace URL address identifier (e.g. devflow.ai/workspaces/slug)
                </FormHelperText>
              </Box>

              <TextField
                label="Logo URL (optional)"
                variant="outlined"
                fullWidth
                size="small"
                error={!!errors.logo_url}
                helperText={errors.logo_url?.message}
                {...register("logo_url", {
                  validate: (val) => {
                    if (!val) return true;
                    try {
                      new URL(val);
                      return true;
                    } catch {
                      return "Invalid URL format";
                    }
                  },
                })}
                slotProps={{ input: { style: { borderRadius: 8 } } }}
              />

              <TextField
                label="Description (optional)"
                variant="outlined"
                fullWidth
                multiline
                rows={3}
                size="small"
                error={!!errors.description}
                helperText={errors.description?.message}
                {...register("description", {
                  maxLength: {
                    value: 1000,
                    message: "Description cannot exceed 1000 characters",
                  },
                })}
                slotProps={{ input: { style: { borderRadius: 8 } } }}
              />

              <Box sx={{ display: "flex", gap: 2, mt: 1 }}>
                <Button
                  onClick={() => navigate("/workspaces")}
                  variant="outlined"
                  color="inherit"
                  fullWidth
                  sx={{ borderRadius: 2, textTransform: "none", py: 1 }}
                >
                  Cancel
                </Button>
                <Button
                  type="submit"
                  variant="contained"
                  color="primary"
                  fullWidth
                  disabled={loading || !ownerId}
                  sx={{ borderRadius: 2, textTransform: "none", py: 1, fontWeight: 700 }}
                >
                  {loading ? "Creating..." : "Create Workspace"}
                </Button>
              </Box>
            </Box>
          </form>
        </Paper>
      </Box>
    </Box>
  );
};
