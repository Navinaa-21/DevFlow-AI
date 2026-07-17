import React, { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import {
  Box,
  Paper,
  Typography,
  TextField,
  Button,
  Card,
  CardContent,
  Divider,
} from "@mui/material";
import MailOutlineIcon from "@mui/icons-material/Mail";
import CheckCircleIcon from "@mui/icons-material/CheckCircle";
import CancelIcon from "@mui/icons-material/Cancel";
import toast from "react-hot-toast";

import { apiClient } from "../api/client";
import { PageHeader } from "../components/PageHeader";
import { LoadingSpinner } from "../components/LoadingSpinner";
import { isAuthenticated } from "../utils/auth";

interface InvitationDetails {
  id: string;
  email: string;
  status: string;
  workspace_name: string;
  inviter_name: string;
  role: string;
}

export const WorkspaceInvitation: React.FC = () => {
  const { token } = useParams<{ token?: string }>();
  const navigate = useNavigate();
  const isAuthed = isAuthenticated();

  const [inputToken, setInputToken] = useState("");
  const [invitation, setInvitation] = useState<InvitationDetails | null>(null);
  const [loading, setLoading] = useState(false);
  const [actionLoading, setActionLoading] = useState(false);

  useEffect(() => {
    if (token) {
      setLoading(true);
      apiClient
        .get(`/invitations/${token}`)
        .then((res) => {
          setInvitation(res.data);
        })
        .catch(() => {
          toast.error("Invitation not found or has expired.");
          navigate("/invitations");
        })
        .finally(() => {
          setLoading(false);
        });
    } else {
      setInvitation(null);
    }
  }, [token, navigate]);

  const handleInspectToken = () => {
    if (!inputToken.trim()) return;
    navigate(`/invitations/${inputToken.trim()}`);
  };

  const handleAuthRedirect = () => {
    navigate(`/register`);
  };

  const handleAccept = async () => {
    if (!token) return;
    setActionLoading(true);
    try {
      await apiClient.post(`/invitations/${token}/accept`);
      toast.success("Invitation accepted! You have joined the workspace.");
      navigate("/");
    } catch (err: any) {
      toast.error(err.response?.data?.detail || "Failed to accept invitation.");
    } finally {
      setActionLoading(false);
    }
  };

  const handleDecline = async () => {
    if (!token) return;
    setActionLoading(true);
    try {
      await apiClient.post(`/invitations/${token}/decline`);
      toast.success("Invitation declined.");
      navigate("/");
    } catch (err: any) {
      toast.error(err.response?.data?.detail || "Failed to decline invitation.");
    } finally {
      setActionLoading(false);
    }
  };

  if (loading) {
    return <LoadingSpinner message="Verifying invitation status..." />;
  }

  return (
    <Box>
      <PageHeader
        title="Workspace Invitations"
        subtitle="Accept or decline invitations to collaborate in team workspaces"
      />

      <Box sx={{ display: "flex", justifyContent: "center", mt: 2 }}>
        {!token ? (
          <Paper
            elevation={0}
            sx={{
              maxWidth: 500,
              width: "100%",
              p: 4,
              border: "1px solid",
              borderColor: "divider",
              borderRadius: 3,
              textAlign: "center",
              boxShadow: "0 1px 3px rgba(0,0,0,0.02)",
            }}
          >
            <MailOutlineIcon sx={{ fontSize: 48, color: "text.secondary", mb: 2 }} />
            <Typography variant="h6" sx={{ fontWeight: 700, letterSpacing: -0.5, mb: 1 }}>
              Enter Invitation Token
            </Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 3.5 }}>
              If you received a workspace invitation token, enter it below to inspect details and join the workspace.
            </Typography>

            <Box sx={{ display: "flex", flexDirection: "column", gap: 2 }}>
              <TextField
                label="Invitation Token"
                variant="outlined"
                value={inputToken}
                onChange={(e) => setInputToken(e.target.value)}
                fullWidth
                size="small"
                placeholder="Paste token hash here"
                slotProps={{ input: { style: { borderRadius: 8 } } }}
              />
              <Button
                variant="contained"
                onClick={handleInspectToken}
                disabled={!inputToken.trim()}
                sx={{ borderRadius: 2, py: 1, textTransform: "none", fontWeight: 700 }}
              >
                Inspect Invitation
              </Button>
            </Box>
          </Paper>
        ) : (
          invitation && (
            <Card
              sx={{
                maxWidth: 450,
                width: "100%",
                borderRadius: 3,
                border: "1px solid",
                borderColor: "divider",
                boxShadow: "0 1px 3px rgba(0,0,0,0.02), 0 4px 12px rgba(0,0,0,0.01)",
              }}
            >
              <CardContent sx={{ p: 4, textAlign: "center" }}>
                <MailOutlineIcon color="primary" sx={{ fontSize: 52, mb: 2 }} />
                <Typography variant="h6" sx={{ fontWeight: 700, letterSpacing: -0.5, mb: 1 }}>
                  Join {invitation.workspace_name}
                </Typography>
                <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
                  {invitation.inviter_name} has invited you to collaborate in this workspace as a {invitation.role}.
                </Typography>
                <Divider sx={{ mb: 3 }} />

                <Box sx={{ display: "flex", flexDirection: "column", gap: 2, mb: 4.5, textAlign: "left" }}>
                  <Box>
                    <Typography variant="caption" color="text.secondary" sx={{ display: "block" }}>
                      INVITEE EMAIL
                    </Typography>
                    <Typography variant="body2" sx={{ fontWeight: 600 }}>
                      {invitation.email}
                    </Typography>
                  </Box>
                  <Box>
                    <Typography variant="caption" color="text.secondary" sx={{ display: "block" }}>
                      STATUS
                    </Typography>
                    <Typography variant="body2" sx={{ fontWeight: 600, color: "warning.main" }}>
                      {invitation.status.toUpperCase()}
                    </Typography>
                  </Box>
                </Box>

                {invitation.status.toLowerCase() === "pending" ? (
                  !isAuthed ? (
                    <Box sx={{ display: "flex", flexDirection: "column", gap: 2 }}>
                      <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
                        You need an account to accept this invitation.
                      </Typography>
                      <Button
                        variant="contained"
                        color="primary"
                        fullWidth
                        onClick={handleAuthRedirect}
                        sx={{ borderRadius: 2, textTransform: "none", py: 1, fontWeight: 700 }}
                      >
                        Create Account
                      </Button>
                    </Box>
                  ) : (
                    <Box sx={{ display: "flex", gap: 2 }}>
                      <Button
                        variant="outlined"
                        color="error"
                        fullWidth
                        startIcon={<CancelIcon />}
                      disabled={actionLoading}
                      onClick={handleDecline}
                      sx={{ borderRadius: 2, textTransform: "none", py: 1, fontWeight: 600 }}
                    >
                      Decline
                    </Button>
                    <Button
                      variant="contained"
                      color="success"
                      fullWidth
                      startIcon={<CheckCircleIcon />}
                      disabled={actionLoading}
                      onClick={handleAccept}
                      sx={{ borderRadius: 2, textTransform: "none", py: 1, fontWeight: 700 }}
                    >
                      Accept & Join
                    </Button>
                    </Box>
                  )
                ) : (
                  <Box>
                    <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                      This invitation is no longer pending (current status: {invitation.status}).
                    </Typography>
                    <Button
                      variant="outlined"
                      onClick={() => navigate("/invitations")}
                      sx={{ borderRadius: 2, textTransform: "none" }}
                    >
                      Back
                    </Button>
                  </Box>
                )}
              </CardContent>
            </Card>
          )
        )}
      </Box>
    </Box>
  );
};
