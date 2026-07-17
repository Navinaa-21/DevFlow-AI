import React, { useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useForm } from "react-hook-form";
import {
  Box,
  Paper,
  TextField,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Button,
  FormHelperText,
} from "@mui/material";
import toast from "react-hot-toast";

import { apiClient } from "../api/client";
import { PageHeader } from "../components/PageHeader";

interface RepoConnectInputs {
  clone_url: string;
  provider: "GITHUB";
  default_branch: string;
  visibility: "public" | "private";
}

export const RepositoryConnect: React.FC = () => {
  const { workspaceId } = useParams<{ workspaceId: string }>();
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<RepoConnectInputs>({
    defaultValues: {
      clone_url: "",
      provider: "GITHUB",
      default_branch: "main",
      visibility: "private",
    },
  });

  const onSubmit = async (data: RepoConnectInputs) => {
    setLoading(true);
    try {
      let repoName = "Repository";
      let providerRepoId = `repo-${Date.now()}`;

      try {
        const urlObj = new URL(data.clone_url);
        const pathParts = urlObj.pathname.replace(/^\/|\/$/g, "").split("/");
        if (pathParts.length >= 2) {
          repoName = pathParts[pathParts.length - 1].replace(/\.git$/, "");
          providerRepoId = pathParts.join("/").replace(/\.git$/, "");
        }
      } catch (err) {
        toast.error("Invalid URL format. Please provide a valid absolute URL.");
        setLoading(false);
        return;
      }

      const payload = {
        name: repoName,
        provider: data.provider,
        provider_repository_id: providerRepoId,
        clone_url: data.clone_url.trim(),
        default_branch: data.default_branch,
        visibility: data.visibility,
      };

      await apiClient.post(`/workspaces/${workspaceId}/repositories`, payload);
      toast.success("Repository connected successfully!");
      navigate(`/workspaces/${workspaceId}`);
    } catch (err: any) {
      const detail = err.response?.data?.detail || "Failed to connect repository. Verify the URL is correct.";
      toast.error(typeof detail === "object" ? JSON.stringify(detail) : detail);
    } finally {
      setLoading(false);
    }
  };

  return (
    <Box>
      <PageHeader
        title="Connect Repository"
        subtitle="Link a git codebase to this workspace"
        breadcrumbs={[
          { label: "Workspaces", to: "/workspaces" },
          { label: "Workspace Details", to: `/workspaces/${workspaceId}` },
          { label: "Connect" },
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
                label="Repository Git URL"
                variant="outlined"
                fullWidth
                size="small"
                placeholder="https://github.com/owner/repository.git"
                error={!!errors.clone_url}
                helperText={errors.clone_url?.message}
                {...register("clone_url", {
                  required: "Repository URL is required",
                  pattern: {
                    value: /^https?:\/\/.+/,
                    message: "Must be a valid HTTP/HTTPS URL",
                  },
                })}
                slotProps={{ input: { style: { borderRadius: 8 } } }}
              />

              <FormControl size="small" fullWidth>
                <InputLabel>Git Provider</InputLabel>
                <Select
                  value="GITHUB"
                  label="Git Provider"
                  disabled
                  sx={{ borderRadius: 2 }}
                >
                  <MenuItem value="GITHUB">GitHub</MenuItem>
                </Select>
                <FormHelperText>Currently GITHUB is the only supported provider</FormHelperText>
              </FormControl>

              <TextField
                label="Default Branch"
                variant="outlined"
                fullWidth
                size="small"
                error={!!errors.default_branch}
                helperText={errors.default_branch?.message}
                {...register("default_branch", { required: "Default branch is required" })}
                slotProps={{ input: { style: { borderRadius: 8 } } }}
              />

              <FormControl size="small" fullWidth>
                <InputLabel>Visibility</InputLabel>
                <Select
                  label="Visibility"
                  defaultValue="private"
                  {...register("visibility", { required: "Visibility selection is required" })}
                  sx={{ borderRadius: 2 }}
                >
                  <MenuItem value="private">Private</MenuItem>
                  <MenuItem value="public">Public</MenuItem>
                </Select>
              </FormControl>

              <Box sx={{ display: "flex", gap: 2, mt: 1 }}>
                <Button
                  onClick={() => navigate(`/workspaces/${workspaceId}`)}
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
                  disabled={loading}
                  sx={{ borderRadius: 2, textTransform: "none", py: 1, fontWeight: 700 }}
                >
                  {loading ? "Connecting..." : "Connect Repository"}
                </Button>
              </Box>
            </Box>
          </form>
        </Paper>
      </Box>
    </Box>
  );
};
