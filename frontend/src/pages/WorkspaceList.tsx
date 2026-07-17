import React, { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import {
  Grid,
  Box,
  Card,
  CardContent,
  Typography,
  Button,
} from "@mui/material";
import WorkspacesIcon from "@mui/icons-material/Workspaces";
import AddIcon from "@mui/icons-material/Add";
import toast from "react-hot-toast";

import { apiClient } from "../api/client";
import { PageHeader } from "../components/PageHeader";
import { LoadingSpinner } from "../components/LoadingSpinner";
import { EmptyState } from "../components/EmptyState";
import { StatusChip } from "../components/StatusChip";
import type { Workspace } from "../types";

export const WorkspaceList: React.FC = () => {
  const [workspaces, setWorkspaces] = useState<Workspace[]>([]);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
    apiClient
      .get("/workspaces")
      .then((res) => {
        setWorkspaces(res.data.items);
      })
      .catch(() => {
        toast.error("Failed to load workspaces list.");
      })
      .finally(() => {
        setLoading(false);
      });
  }, []);

  if (loading) {
    return <LoadingSpinner message="Retrieving workspaces..." />;
  }

  const createButton = (
    <Button
      component={Link}
      to="/workspaces/new"
      variant="contained"
      color="primary"
      startIcon={<AddIcon />}
      sx={{ borderRadius: 2, textTransform: "none", fontWeight: 600 }}
    >
      Create Workspace
    </Button>
  );

  return (
    <Box>
      <PageHeader
        title="Workspaces"
        subtitle="Manage user permissions and repository connections"
        action={createButton}
      />

      {workspaces.length === 0 ? (
        <EmptyState
          title="No Workspaces Found"
          description="Workspaces let you collaborate with developers, track commit histories, and sync connected repositories."
          actionText="Create Your First Workspace"
          onAction={() => navigate("/workspaces/new")}
          icon={<WorkspacesIcon />}
        />
      ) : (
        <Grid container spacing={3}>
          {workspaces.map((ws) => (
            <Grid key={ws.id} size={{ xs: 12, sm: 6, md: 4 }}>
              <Card
                sx={{
                  borderRadius: 3,
                  border: "1px solid",
                  borderColor: "divider",
                  boxShadow: "0 1px 3px rgba(0,0,0,0.02), 0 4px 12px rgba(0,0,0,0.01)",
                  height: "100%",
                  display: "flex",
                  flexDirection: "column",
                  justifyContent: "space-between",
                  transition: "transform 0.15s ease-in-out, box-shadow 0.15s ease-in-out",
                  "&:hover": {
                    transform: "translateY(-2px)",
                    boxShadow: "0 4px 20px rgba(0,0,0,0.06)",
                  },
                }}
              >
                <CardContent sx={{ p: 2.5, display: "flex", flexDirection: "column", height: "100%" }}>
                  <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", mb: 1.5 }}>
                    <Typography variant="h6" sx={{ fontWeight: 700, letterSpacing: -0.3, wordBreak: "break-all" }}>
                      {ws.name}
                    </Typography>
                    <StatusChip label={ws.is_active ? "Active" : "Archived"} type="status" />
                  </Box>

                  <Typography variant="caption" color="text.secondary" sx={{ display: "block", mb: 1, fontWeight: 500 }}>
                    slug: /{ws.slug}
                  </Typography>

                  <Typography
                    variant="body2"
                    color="text.secondary"
                    sx={{
                      mb: 3,
                      flexGrow: 1,
                      display: "-webkit-box",
                      WebkitLineClamp: 3,
                      WebkitBoxOrient: "vertical",
                      overflow: "hidden",
                      textOverflow: "ellipsis",
                      minHeight: "3.5em",
                    }}
                  >
                    {ws.description || "No description provided."}
                  </Typography>

                  <Box sx={{ display: "flex", justifyContent: "flex-end", pt: 1.5, borderTop: "1px solid", borderColor: "divider" }}>
                    <Button
                      component={Link}
                      to={`/workspaces/${ws.id}`}
                      size="small"
                      variant="text"
                      color="primary"
                      sx={{ fontWeight: 600, textTransform: "none" }}
                    >
                      Configure &rarr;
                    </Button>
                  </Box>
                </CardContent>
              </Card>
            </Grid>
          ))}
        </Grid>
      )}
    </Box>
  );
};
