import React, { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import {
  Box,
  Card,
  CardContent,
  FormControl,
  Select,
  MenuItem,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Button,
  Typography,
  Divider,
} from "@mui/material";
import GitHubIcon from "@mui/icons-material/GitHub";
import SyncIcon from "@mui/icons-material/Sync";
import DeleteIcon from "@mui/icons-material/Delete";
import AddIcon from "@mui/icons-material/Add";
import toast from "react-hot-toast";

import { apiClient } from "../api/client";
import { PageHeader } from "../components/PageHeader";
import { LoadingSpinner } from "../components/LoadingSpinner";
import { EmptyState } from "../components/EmptyState";
import { StatusChip } from "../components/StatusChip";
import { ConfirmDialog } from "../components/ConfirmDialog";
import type { Repository } from "../types";

interface WorkspaceSelectItem {
  id: string;
  name: string;
}

export const RepositoryList: React.FC = () => {
  const navigate = useNavigate();
  
  const [workspaces, setWorkspaces] = useState<WorkspaceSelectItem[]>([]);
  const [selectedWorkspace, setSelectedWorkspace] = useState<string>("");
  const [repositories, setRepositories] = useState<Repository[]>([]);
  
  const [loadingWorkspaces, setLoadingWorkspaces] = useState(true);
  const [loadingRepos, setLoadingRepos] = useState(false);
  const [syncLoadingId, setSyncLoadingId] = useState<string | null>(null);
  
  const [deleteConfirmOpen, setDeleteConfirmOpen] = useState(false);
  const [repoToDelete, setRepoToDelete] = useState<Repository | null>(null);
  const [deleteLoading, setDeleteLoading] = useState(false);

  useEffect(() => {
    apiClient
      .get("/dashboard/workspaces")
      .then((res) => {
        setWorkspaces(res.data);
        if (res.data.length > 0) {
          setSelectedWorkspace(res.data[0].id);
        }
      })
      .catch(() => {
        toast.error("Failed to load workspace contexts.");
      })
      .finally(() => {
        setLoadingWorkspaces(false);
      });
  }, []);

  useEffect(() => {
    if (!selectedWorkspace) return;
    setLoadingRepos(true);
    apiClient
      .get(`/workspaces/${selectedWorkspace}/repositories`)
      .then((res) => {
        setRepositories(res.data);
      })
      .catch(() => {
        toast.error("Failed to retrieve connected repositories.");
      })
      .finally(() => {
        setLoadingRepos(false);
      });
  }, [selectedWorkspace]);

  const handleSyncRepository = async (repoId: string) => {
    setSyncLoadingId(repoId);
    try {
      const res = await apiClient.post(`/repositories/${repoId}/sync`);
      toast.success("Manual repository metadata sync triggered!");
      
      setRepositories((prev) =>
        prev.map((r) =>
          r.id === repoId
            ? { ...r, last_synced_at: res.data.last_synced_at, default_branch: res.data.default_branch || r.default_branch }
            : r
        )
      );
    } catch (err: any) {
      toast.error(err.response?.data?.detail || "Sync failed. Verify GitHub token/connection.");
    } finally {
      setSyncLoadingId(null);
    }
  };

  const handleDeleteRepository = async () => {
    if (!repoToDelete) return;
    setDeleteLoading(true);
    try {
      await apiClient.delete(`/repositories/${repoToDelete.id}`);
      toast.success("Repository connection disconnected successfully.");
      setRepositories((prev) => prev.filter((r) => r.id !== repoToDelete.id));
      setDeleteConfirmOpen(false);
      setRepoToDelete(null);
    } catch (err: any) {
      toast.error("Failed to disconnect repository connection.");
    } finally {
      setDeleteLoading(false);
    }
  };

  if (loadingWorkspaces) {
    return <LoadingSpinner message="Resolving workspace contexts..." />;
  }

  const workspaceSelector = workspaces.length > 0 && (
    <FormControl size="small" sx={{ minWidth: 200 }}>
      <Select
        value={selectedWorkspace}
        onChange={(e) => setSelectedWorkspace(e.target.value)}
        sx={{ borderRadius: 2, bgcolor: "background.paper" }}
      >
        {workspaces.map((ws) => (
          <MenuItem key={ws.id} value={ws.id}>
            {ws.name}
          </MenuItem>
        ))}
      </Select>
    </FormControl>
  );

  return (
    <Box>
      <PageHeader
        title="Connected Repositories"
        subtitle="Manage repository synchronization hooks and status"
        action={workspaceSelector}
      />

      {workspaces.length === 0 ? (
        <EmptyState
          title="No Workspaces Available"
          description="Create a workspace first in order to connect repository git sources."
          actionText="Create Workspace"
          onAction={() => navigate("/workspaces/new")}
          icon={<GitHubIcon />}
        />
      ) : loadingRepos ? (
        <LoadingSpinner message="Fetching connected repositories..." />
      ) : repositories.length === 0 ? (
        <EmptyState
          title="No Connected Repositories"
          description="Link Git repository URLs directly to synchronize metadata, analyze branches, and ingest push webhooks."
          actionText="Connect Repository"
          onAction={() => navigate(`/workspaces/${selectedWorkspace}/connect-repos`)}
          icon={<GitHubIcon />}
        />
      ) : (
        <Card
          sx={{
            borderRadius: 3,
            border: "1px solid",
            borderColor: "divider",
            boxShadow: "0 1px 3px rgba(0,0,0,0.02)",
          }}
        >
          <CardContent sx={{ p: 0, "&:last-child": { pb: 0 } }}>
            <Box sx={{ p: 2.5, display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <Typography variant="subtitle1" sx={{ fontWeight: 700 }}>
                Linked Codebases
              </Typography>
              <Button
                component={Link}
                to={`/workspaces/${selectedWorkspace}/connect-repos`}
                variant="contained"
                size="small"
                startIcon={<AddIcon />}
                sx={{ borderRadius: 2, textTransform: "none", fontWeight: 600 }}
              >
                Connect URL
              </Button>
            </Box>
            <Divider />

            <TableContainer>
              <Table>
                <TableHead sx={{ bgcolor: "action.hover" }}>
                  <TableRow>
                    <TableCell sx={{ fontWeight: 600, fontSize: "0.8rem", color: "text.secondary" }}>REPOSITORY</TableCell>
                    <TableCell sx={{ fontWeight: 600, fontSize: "0.8rem", color: "text.secondary" }}>PROVIDER</TableCell>
                    <TableCell sx={{ fontWeight: 600, fontSize: "0.8rem", color: "text.secondary" }}>VISIBILITY</TableCell>
                    <TableCell sx={{ fontWeight: 600, fontSize: "0.8rem", color: "text.secondary" }}>BRANCH</TableCell>
                    <TableCell sx={{ fontWeight: 600, fontSize: "0.8rem", color: "text.secondary" }}>WEBHOOK</TableCell>
                    <TableCell sx={{ fontWeight: 600, fontSize: "0.8rem", color: "text.secondary" }}>LAST SYNC</TableCell>
                    <TableCell align="right" sx={{ fontWeight: 600, fontSize: "0.8rem", color: "text.secondary" }}>ACTIONS</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {repositories.map((repo) => (
                    <TableRow key={repo.id} hover>
                      <TableCell sx={{ py: 1.5 }}>
                        <Typography
                          component="a"
                          href={repo.repo_url}
                          target="_blank"
                          rel="noreferrer"
                          variant="body2"
                          sx={{ fontWeight: 600, color: "primary.main", textDecoration: "none", "&:hover": { textDecoration: "underline" } }}
                        >
                          {repo.full_name || repo.name}
                        </Typography>
                      </TableCell>
                      <TableCell sx={{ py: 1.5 }}>
                        <StatusChip label={repo.provider} type="provider" />
                      </TableCell>
                      <TableCell sx={{ py: 1.5 }}>
                        <StatusChip label={repo.visibility || "PRIVATE"} type="visibility" />
                      </TableCell>
                      <TableCell sx={{ py: 1.5 }}>
                        <Typography variant="body2" sx={{ fontFamily: "monospace" }}>
                          {repo.default_branch}
                        </Typography>
                      </TableCell>
                      <TableCell sx={{ py: 1.5 }}>
                        <StatusChip
                          label={repo.webhook_enabled ? "Enabled" : "Disabled"}
                          type="webhook"
                        />
                      </TableCell>
                      <TableCell sx={{ py: 1.5 }}>
                        <Typography variant="body2" color="text.secondary">
                          {repo.last_synced_at
                            ? new Date(repo.last_synced_at).toLocaleString()
                            : "Never"}
                        </Typography>
                      </TableCell>
                      <TableCell align="right" sx={{ py: 1 }}>
                        <Box sx={{ display: "flex", gap: 1, justifyContent: "flex-end" }}>
                          <Button
                            size="small"
                            variant="outlined"
                            color="inherit"
                            disabled={syncLoadingId === repo.id}
                            startIcon={<SyncIcon className={syncLoadingId === repo.id ? "spin" : ""} sx={{ fontSize: 16 }} />}
                            onClick={() => handleSyncRepository(repo.id)}
                            sx={{
                              borderRadius: 1.5,
                              textTransform: "none",
                              fontWeight: 600,
                              fontSize: "0.8rem",
                              borderColor: "divider",
                            }}
                          >
                            {syncLoadingId === repo.id ? "Syncing..." : "Sync"}
                          </Button>
                          <Button
                            size="small"
                            variant="outlined"
                            color="error"
                            startIcon={<DeleteIcon sx={{ fontSize: 16 }} />}
                            onClick={() => {
                              setRepoToDelete(repo);
                              setDeleteConfirmOpen(true);
                            }}
                            sx={{
                              borderRadius: 1.5,
                              textTransform: "none",
                              fontWeight: 600,
                              fontSize: "0.8rem",
                            }}
                          >
                            Disconnect
                          </Button>
                        </Box>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
          </CardContent>
        </Card>
      )}

      <ConfirmDialog
        open={deleteConfirmOpen}
        title="Disconnect Repository"
        message={`Are you sure you want to disconnect ${repoToDelete?.full_name || repoToDelete?.name}? This will remove the webhook integration and commit data linked to it.`}
        confirmText="Disconnect"
        severity="error"
        loading={deleteLoading}
        onConfirm={handleDeleteRepository}
        onCancel={() => {
          setDeleteConfirmOpen(false);
          setRepoToDelete(null);
        }}
      />
    </Box>
  );
};

const styles = `
  @keyframes spin {
    0% { transform: rotate(0deg); }
    100% { transform: rotate(360deg); }
  }
  .spin {
    animation: spin 1.2s linear infinite;
  }
`;

if (typeof document !== "undefined") {
  const styleEl = document.createElement("style");
  styleEl.innerHTML = styles;
  document.head.appendChild(styleEl);
}
