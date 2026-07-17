import React, { useState, useEffect } from "react";
import {
  Grid,
  Box,
  Card,
  CardContent,
  Typography,
  FormControl,
  Select,
  MenuItem,
  List,
  ListItem,
  ListItemText,
  Avatar,
  Divider,
} from "@mui/material";
import WorkspacesIcon from "@mui/icons-material/Workspaces";
import GitHubIcon from "@mui/icons-material/GitHub";
import HistoryIcon from "@mui/icons-material/History";
import SyncIcon from "@mui/icons-material/Sync";
import AccessTimeIcon from "@mui/icons-material/AccessTime";

import { apiClient } from "../api/client";
import { PageHeader } from "../components/PageHeader";
import { StatCard } from "../components/StatCard";
import { LoadingSpinner } from "../components/LoadingSpinner";
import { StatusChip } from "../components/StatusChip";
import toast from "react-hot-toast";

interface SummaryData {
  total_repositories: number;
  active_repositories: number;
  archived_repositories: number;
  total_commits: number;
  commits_last_24h: number;
  commits_last_7d: number;
  last_sync_time: string | null;
}

interface ActivityItem {
  id: string;
  repository_id: string;
  repository_name: string;
  commit_sha: string;
  short_sha: string;
  commit_message: string;
  committed_at: string;
  author_name: string;
  author_email: string;
  branch: string;
}

interface WorkspaceListItem {
  id: string;
  name: string;
  slug: string;
}

export const Dashboard: React.FC = () => {
  const [selectedWorkspace, setSelectedWorkspace] = useState<string>("all");
  const [workspaces, setWorkspaces] = useState<WorkspaceListItem[]>([]);
  const [summary, setSummary] = useState<SummaryData | null>(null);
  const [activities, setActivities] = useState<ActivityItem[]>([]);
  const [loading, setLoading] = useState<boolean>(true);

  // Fetch list of workspaces for selector dropdown
  useEffect(() => {
    apiClient
      .get("/dashboard/workspaces")
      .then((res) => {
        setWorkspaces(res.data);
      })
      .catch(() => {
        toast.error("Failed to load workspace filters.");
      });
  }, []);

  // Fetch summary stats and activities
  useEffect(() => {
    setLoading(true);
    const workspaceParam = selectedWorkspace === "all" ? "" : selectedWorkspace;
    const query = workspaceParam ? `?workspace_id=${workspaceParam}` : "";

    const fetchSummary = apiClient.get(`/dashboard/summary${query}`);
    const fetchActivity = apiClient.get(`/dashboard/recent-activity${query}&limit=8`);

    Promise.all([fetchSummary, fetchActivity])
      .then(([summaryRes, activityRes]) => {
        setSummary(summaryRes.data);
        setActivities(activityRes.data);
      })
      .catch(() => {
        toast.error("Failed to update dashboard data.");
      })
      .finally(() => {
        setLoading(false);
      });
  }, [selectedWorkspace]);

  if (loading && !summary) {
    return <LoadingSpinner message="Assembling your dashboard..." />;
  }

  const workspaceSelector = (
    <FormControl size="small" sx={{ minWidth: 200 }}>
      <Select
        value={selectedWorkspace}
        onChange={(e) => setSelectedWorkspace(e.target.value)}
        sx={{ borderRadius: 2, bgcolor: "background.paper" }}
      >
        <MenuItem value="all">All Workspaces</MenuItem>
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
        title="Dashboard"
        subtitle="Aggregate metrics and activity overview"
        action={workspaceSelector}
      />

      {summary && (
        <Grid container spacing={3} sx={{ mb: 4 }}>
          <Grid size={{ xs: 12, sm: 6, md: 3 }}>
            <StatCard
              title="Workspaces"
              value={selectedWorkspace === "all" ? workspaces.length : 1}
              icon={<WorkspacesIcon />}
              subtitle="Registered workspaces"
              color="primary.main"
            />
          </Grid>
          <Grid size={{ xs: 12, sm: 6, md: 3 }}>
            <StatCard
              title="Repositories"
              value={summary.total_repositories}
              icon={<GitHubIcon />}
              subtitle={`${summary.active_repositories} Active / ${summary.archived_repositories} Archived`}
              color="text.primary"
            />
          </Grid>
          <Grid size={{ xs: 12, sm: 6, md: 3 }}>
            <StatCard
              title="Total Commits"
              value={summary.total_commits}
              icon={<HistoryIcon />}
              subtitle={`${summary.commits_last_7d} commits this week`}
              color="info.main"
            />
          </Grid>
          <Grid size={{ xs: 12, sm: 6, md: 3 }}>
            <StatCard
              title="Commits (24h)"
              value={summary.commits_last_24h}
              icon={<AccessTimeIcon />}
              subtitle="Commits ingested in last 24h"
              color="success.main"
            />
          </Grid>
        </Grid>
      )}

      <Grid container spacing={4}>
        <Grid size={{ xs: 12, md: 8 }}>
          <Card
            sx={{
              borderRadius: 3,
              border: "1px solid",
              borderColor: "divider",
              boxShadow: "0 1px 3px rgba(0,0,0,0.02)",
            }}
          >
            <CardContent sx={{ p: 0, "&:last-child": { pb: 0 } }}>
              <Box sx={{ p: 2.5, display: "flex", alignItems: "center", gap: 1 }}>
                <HistoryIcon color="primary" />
                <Typography variant="subtitle1" sx={{ fontWeight: 700 }}>
                  Recent Commits Ingested
                </Typography>
              </Box>
              <Divider />
              {activities.length === 0 ? (
                <Box sx={{ p: 4, textAlign: "center" }}>
                  <Typography variant="body2" color="text.secondary">
                    No commit ingestion events logged.
                  </Typography>
                </Box>
              ) : (
                <List disablePadding>
                  {activities.map((item, idx) => (
                    <React.Fragment key={item.id}>
                      <ListItem
                        sx={{
                          py: 2,
                          px: 2.5,
                          alignItems: "flex-start",
                        }}
                      >
                        <Avatar
                          sx={{
                            width: 32,
                            height: 32,
                            fontSize: "0.85rem",
                            mr: 2,
                            bgcolor: "primary.light",
                            color: "primary.main",
                            fontWeight: "bold",
                          }}
                        >
                          {item.author_name.charAt(0).toUpperCase()}
                        </Avatar>
                        <ListItemText
                          primary={
                            <Box sx={{ display: "flex", flexWrap: "wrap", gap: 1, alignItems: "center", mb: 0.5 }}>
                              <Typography variant="body2" sx={{ fontWeight: 600, color: "text.primary" }}>
                                {item.author_name}
                              </Typography>
                              <Typography variant="caption" color="text.secondary">
                                pushed to
                              </Typography>
                              <Typography variant="body2" sx={{ fontWeight: 600, color: "text.primary" }}>
                                {item.repository_name}/{item.branch}
                              </Typography>
                              <StatusChip label={item.short_sha} type="provider" />
                            </Box>
                          }
                          secondary={
                            <Box>
                              <Typography variant="body2" sx={{ mb: 1, fontWeight: 500, color: "text.primary" }}>
                                {item.commit_message}
                              </Typography>
                              <Typography variant="caption" color="text.secondary">
                                {new Date(item.committed_at).toLocaleString()}
                              </Typography>
                            </Box>
                          }
                        />
                      </ListItem>
                      {idx < activities.length - 1 && <Divider />}
                    </React.Fragment>
                  ))}
                </List>
              )}
            </CardContent>
          </Card>
        </Grid>

        <Grid size={{ xs: 12, md: 4 }}>
          <Card
            sx={{
              borderRadius: 3,
              border: "1px solid",
              borderColor: "divider",
              boxShadow: "0 1px 3px rgba(0,0,0,0.02)",
            }}
          >
            <CardContent sx={{ p: 2.5 }}>
              <Box sx={{ display: "flex", alignItems: "center", gap: 1, mb: 2 }}>
                <SyncIcon color="primary" />
                <Typography variant="subtitle1" sx={{ fontWeight: 700 }}>
                  Synchronization Status
                </Typography>
              </Box>
              <Divider sx={{ mb: 2 }} />
              <Box sx={{ display: "flex", flexDirection: "column", gap: 2 }}>
                <Box>
                  <Typography variant="caption" color="text.secondary" sx={{ display: "block", mb: 0.5 }}>
                    LAST BROADCAST SYNC TIME
                  </Typography>
                  <Typography variant="body2" sx={{ fontWeight: 600 }}>
                    {summary?.last_sync_time
                      ? new Date(summary.last_sync_time).toLocaleString()
                      : "Never Synced"}
                  </Typography>
                </Box>
                <Box>
                  <Typography variant="caption" color="text.secondary" sx={{ display: "block", mb: 0.5 }}>
                    WEBHOOK CONFIGURATION STATUS
                  </Typography>
                  <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
                    <StatusChip label="ACTIVE" type="status" />
                    <Typography variant="caption" color="text.secondary">
                      Ingesting push webhooks
                    </Typography>
                  </Box>
                </Box>
              </Box>
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Box>
  );
};
