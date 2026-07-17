import React, { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import {
  Box,
  Tabs,
  Tab,
  Typography,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Avatar,
  Button,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Card,
  CardContent,
  Divider,
  Grid,
} from "@mui/material";
import PersonAddIcon from "@mui/icons-material/PersonAdd";
import DeleteIcon from "@mui/icons-material/Delete";
import SwapHorizIcon from "@mui/icons-material/SwapHoriz";
import SettingsIcon from "@mui/icons-material/Settings";
import GroupIcon from "@mui/icons-material/Group";
import InfoIcon from "@mui/icons-material/Info";
import toast from "react-hot-toast";

import { apiClient } from "../api/client";
import { PageHeader } from "../components/PageHeader";
import { LoadingSpinner } from "../components/LoadingSpinner";
import { StatusChip } from "../components/StatusChip";
import { ConfirmDialog } from "../components/ConfirmDialog";
import type { Workspace } from "../types";

interface Member {
  id: string;
  full_name: string;
  email: string;
  role: string;
}

interface Invitation {
  id: string;
  email: string;
  role: string;
  status: string;
  expires_at: string;
}

export const WorkspaceView: React.FC = () => {
  const { workspaceId } = useParams<{ workspaceId: string }>();
  const navigate = useNavigate();

  const [activeTab, setActiveTab] = useState(0);
  const [workspace, setWorkspace] = useState<Workspace | null>(null);
  const [members, setMembers] = useState<Member[]>([]);
  const [invitations, setInvitations] = useState<Invitation[]>([]);
  const [currentUser, setCurrentUser] = useState<any>(null);
  
  // Loading states
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(false);

  // Form states
  const [editName, setEditName] = useState("");
  const [editSlug, setEditSlug] = useState("");
  const [editLogoUrl, setEditLogoUrl] = useState("");
  const [editDescription, setEditDescription] = useState("");

  // Dialog states
  const [inviteOpen, setInviteOpen] = useState(false);
  const [inviteEmail, setInviteEmail] = useState("");
  const [inviteRole, setInviteRole] = useState("DEVELOPER");

  const [transferOpen, setTransferOpen] = useState(false);
  const [transferTargetId, setTransferTargetId] = useState("");

  const [deleteConfirmOpen, setDeleteConfirmOpen] = useState(false);
  const [removeMemberConfirmOpen, setRemoveMemberConfirmOpen] = useState(false);
  const [memberToRemove, setMemberToRemove] = useState<Member | null>(null);

  // Load workspace details, members, and current user info
  const loadData = async () => {
    try {
      const [wsRes, membersRes, meRes] = await Promise.all([
        apiClient.get(`/workspaces/${workspaceId}`),
        apiClient.get(`/workspaces/${workspaceId}/members`),
        apiClient.get("/auth/me"),
      ]);

      setWorkspace(wsRes.data);
      setEditName(wsRes.data.name);
      setEditSlug(wsRes.data.slug);
      setEditDescription(wsRes.data.description || "");
      setEditLogoUrl(wsRes.data.logo_url || "");

      const mappedMembers = membersRes.data.map((m: any) => ({
        id: m.id,
        full_name: m.full_name,
        email: m.email,
        role: m.role.toUpperCase(),
      }));
      setMembers(mappedMembers);
      setCurrentUser(meRes.data);

      // Gracefully fetch invitations list (w/ fallback logic)
      try {
        const invitesRes = await apiClient.get(`/workspaces/${workspaceId}/invitations`);
        setInvitations(invitesRes.data);
      } catch (err) {
        console.log("Invitations list endpoint unavailable. Using local track state.");
      }
    } catch (err) {
      toast.error("Failed to load workspace details.");
      navigate("/workspaces");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (workspaceId) {
      loadData();
    }
  }, [workspaceId]);

  const currentUserMember = members.find((m) => m.email.toLowerCase() === currentUser?.email?.toLowerCase());
  const currentUserRole = currentUserMember?.role || "DEVELOPER";

  const isOwner = currentUserRole === "OWNER";
  const isManager = currentUserRole === "MANAGER" || isOwner;

  const handleTabChange = (_event: React.SyntheticEvent, newValue: number) => {
    setActiveTab(newValue);
  };

  const handleUpdate = async (e: React.FormEvent) => {
    e.preventDefault();
    setActionLoading(true);
    try {
      const payload = {
        name: editName,
        slug: editSlug,
        description: editDescription.trim() || null,
        logo_url: editLogoUrl.trim() || null,
      };

      const res = await apiClient.patch(`/workspaces/${workspaceId}`, payload);
      setWorkspace(res.data);
      toast.success("Workspace details updated.");
    } catch (err: any) {
      toast.error(err.response?.data?.detail || "Failed to update workspace.");
    } finally {
      setActionLoading(false);
    }
  };

  const handleInviteSubmit = async () => {
    if (!inviteEmail) return;
    setActionLoading(true);
    try {
      const res = await apiClient.post(`/workspaces/${workspaceId}/invitations`, {
        email: inviteEmail.trim(),
        role: inviteRole,
      });

      toast.success(`Invitation sent to ${inviteEmail}!`);
      setInviteOpen(false);
      setInviteEmail("");
      
      const newInvite: Invitation = {
        id: res.data.id,
        email: res.data.email,
        role: res.data.role.toUpperCase(),
        status: res.data.status.toUpperCase(),
        expires_at: res.data.expires_at,
      };
      setInvitations((prev) => [newInvite, ...prev]);
    } catch (err: any) {
      toast.error(err.response?.data?.detail || "Failed to send invitation.");
    } finally {
      setActionLoading(false);
    }
  };

  const handleCancelInvite = async (inviteId: string) => {
    try {
      await apiClient.post(`/workspaces/${workspaceId}/invitations/${inviteId}/cancel`);
      toast.success("Invitation cancelled.");
      setInvitations((prev) => prev.filter((i) => i.id !== inviteId));
    } catch (err: any) {
      toast.error(err.response?.data?.detail || "Failed to cancel invitation.");
    }
  };

  const handleResendInvite = async (inviteId: string) => {
    try {
      const res = await apiClient.post(`/workspaces/${workspaceId}/invitations/${inviteId}/resend`);
      toast.success("Invitation resent successfully!");
      setInvitations((prev) =>
        prev.map((i) => (i.id === inviteId ? { ...i, status: res.data.status.toUpperCase() } : i))
      );
    } catch (err: any) {
      toast.error(err.response?.data?.detail || "Failed to resend invitation.");
    }
  };

  const handleRemoveMember = async () => {
    if (!memberToRemove) return;
    setActionLoading(true);
    try {
      await apiClient.delete(`/workspaces/${workspaceId}/members/${memberToRemove.id}`);
      toast.success(`${memberToRemove.full_name} removed from workspace.`);
      setMembers((prev) => prev.filter((m) => m.id !== memberToRemove.id));
      setRemoveMemberConfirmOpen(false);
      setMemberToRemove(null);
    } catch (err: any) {
      toast.error(err.response?.data?.detail || "Failed to remove member.");
    } finally {
      setActionLoading(false);
    }
  };

  const handleTransferOwnership = async () => {
    if (!transferTargetId) return;
    setActionLoading(true);
    try {
      await apiClient.post(`/workspaces/${workspaceId}/transfer-ownership`, {
        new_owner_id: transferTargetId,
      });

      toast.success("Workspace ownership transferred successfully!");
      setTransferOpen(false);
      setTransferTargetId("");
      loadData();
    } catch (err: any) {
      toast.error(err.response?.data?.detail || "Failed to transfer ownership.");
    } finally {
      setActionLoading(false);
    }
  };

  const handleDeleteWorkspace = async () => {
    setActionLoading(true);
    try {
      await apiClient.delete(`/workspaces/${workspaceId}`);
      toast.success("Workspace permanently deleted.");
      setDeleteConfirmOpen(false);
      navigate("/workspaces");
    } catch (err: any) {
      toast.error("Failed to delete workspace.");
    } finally {
      setActionLoading(false);
    }
  };

  if (loading) {
    return <LoadingSpinner message="Loading workspace details..." />;
  }

  return (
    <Box>
      {workspace && (
        <>
          <PageHeader
            title={workspace.name}
            subtitle={`Slug: /${workspace.slug}`}
            breadcrumbs={[
              { label: "Workspaces", to: "/workspaces" },
              { label: workspace.name },
            ]}
          />

          <Box sx={{ borderBottom: 1, borderColor: "divider", mb: 3 }}>
            <Tabs value={activeTab} onChange={handleTabChange} aria-label="workspace settings tabs">
              <Tab label="Overview" icon={<InfoIcon sx={{ fontSize: 18 }} />} iconPosition="start" sx={{ textTransform: "none", fontWeight: 600 }} />
              <Tab label="Members & Invites" icon={<GroupIcon sx={{ fontSize: 18 }} />} iconPosition="start" sx={{ textTransform: "none", fontWeight: 600 }} />
              {isOwner && (
                <Tab label="Settings" icon={<SettingsIcon sx={{ fontSize: 18 }} />} iconPosition="start" sx={{ textTransform: "none", fontWeight: 600 }} />
              )}
            </Tabs>
          </Box>

          {/* OVERVIEW TAB */}
          {activeTab === 0 && (
            <Grid container spacing={4}>
              <Grid size={{ xs: 12, md: 7 }}>
                <Card sx={{ borderRadius: 3, border: "1px solid", borderColor: "divider", boxShadow: "0 1px 3px rgba(0,0,0,0.02)" }}>
                  <CardContent sx={{ p: 3 }}>
                    <Typography variant="subtitle1" sx={{ fontWeight: 700, mb: 3 }}>
                      Workspace Properties
                    </Typography>
                    
                    <form onSubmit={handleUpdate}>
                      <Box sx={{ display: "flex", flexDirection: "column", gap: 2.5 }}>
                        <TextField
                          label="Workspace Name"
                          value={editName}
                          onChange={(e) => setEditName(e.target.value)}
                          disabled={!isManager}
                          fullWidth
                          size="small"
                          slotProps={{ input: { style: { borderRadius: 8 } } }}
                        />
                        <TextField
                          label="Slug"
                          value={editSlug}
                          onChange={(e) => setEditSlug(e.target.value)}
                          disabled={!isManager}
                          fullWidth
                          size="small"
                          slotProps={{ input: { style: { borderRadius: 8 } } }}
                        />
                        <TextField
                          label="Logo URL"
                          value={editLogoUrl}
                          onChange={(e) => setEditLogoUrl(e.target.value)}
                          disabled={!isManager}
                          fullWidth
                          size="small"
                          slotProps={{ input: { style: { borderRadius: 8 } } }}
                        />
                        <TextField
                          label="Description"
                          value={editDescription}
                          onChange={(e) => setEditDescription(e.target.value)}
                          disabled={!isManager}
                          fullWidth
                          multiline
                          rows={3}
                          size="small"
                          slotProps={{ input: { style: { borderRadius: 8 } } }}
                        />
                        {isManager && (
                          <Button
                            type="submit"
                            variant="contained"
                            disabled={actionLoading}
                            sx={{ alignSelf: "flex-end", borderRadius: 2, textTransform: "none", px: 3, fontWeight: 600 }}
                          >
                            Save Details
                          </Button>
                        )}
                      </Box>
                    </form>
                  </CardContent>
                </Card>
              </Grid>

              <Grid size={{ xs: 12, md: 5 }}>
                <Card sx={{ borderRadius: 3, border: "1px solid", borderColor: "divider", boxShadow: "0 1px 3px rgba(0,0,0,0.02)" }}>
                  <CardContent sx={{ p: 3 }}>
                    <Typography variant="subtitle1" sx={{ fontWeight: 700, mb: 2 }}>
                      System Details
                    </Typography>
                    <Box sx={{ display: "flex", flexDirection: "column", gap: 2 }}>
                      <Box>
                        <Typography variant="caption" color="text.secondary" sx={{ display: "block" }}>
                          WORKSPACE ID
                        </Typography>
                        <Typography variant="body2" sx={{ fontWeight: 600, fontFamily: "monospace", wordBreak: "break-all" }}>
                          {workspace.id}
                        </Typography>
                      </Box>
                      <Box>
                        <Typography variant="caption" color="text.secondary" sx={{ display: "block" }}>
                          PROVISIONED TIMESTAMP
                        </Typography>
                        <Typography variant="body2" sx={{ fontWeight: 600 }}>
                          {new Date(workspace.created_at).toLocaleString()}
                        </Typography>
                      </Box>
                      <Box>
                        <Typography variant="caption" color="text.secondary" sx={{ display: "block" }}>
                          YOUR MEMBERSHIP ROLE
                        </Typography>
                        <Box sx={{ mt: 0.5 }}>
                          <StatusChip label={currentUserRole} type="role" />
                        </Box>
                      </Box>
                    </Box>
                  </CardContent>
                </Card>
              </Grid>
            </Grid>
          )}

          {/* MEMBERS & INVITATIONS TAB */}
          {activeTab === 1 && (
            <Box sx={{ display: "flex", flexDirection: "column", gap: 4 }}>
              {/* Members List */}
              <Card sx={{ borderRadius: 3, border: "1px solid", borderColor: "divider", boxShadow: "0 1px 3px rgba(0,0,0,0.02)" }}>
                <CardContent sx={{ p: 0, "&:last-child": { pb: 0 } }}>
                  <Box sx={{ p: 2.5, display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                    <Typography variant="subtitle1" sx={{ fontWeight: 700 }}>
                      Workspace Members
                    </Typography>
                    <Box sx={{ display: "flex", gap: 1.5 }}>
                      {isOwner && members.length > 1 && (
                        <Button
                          variant="outlined"
                          size="small"
                          color="primary"
                          startIcon={<SwapHorizIcon />}
                          onClick={() => setTransferOpen(true)}
                          sx={{ borderRadius: 2, textTransform: "none", fontWeight: 600 }}
                        >
                          Transfer Ownership
                        </Button>
                      )}
                      {isManager && (
                        <Button
                          variant="contained"
                          size="small"
                          color="primary"
                          startIcon={<PersonAddIcon />}
                          onClick={() => setInviteOpen(true)}
                          sx={{ borderRadius: 2, textTransform: "none", fontWeight: 600 }}
                        >
                          Invite Member
                        </Button>
                      )}
                    </Box>
                  </Box>
                  <Divider />
                  
                  <TableContainer>
                    <Table>
                      <TableHead sx={{ bgcolor: "action.hover" }}>
                        <TableRow>
                          <TableCell sx={{ fontWeight: 600, fontSize: "0.8rem", color: "text.secondary" }}>MEMBER</TableCell>
                          <TableCell sx={{ fontWeight: 600, fontSize: "0.8rem", color: "text.secondary" }}>EMAIL</TableCell>
                          <TableCell sx={{ fontWeight: 600, fontSize: "0.8rem", color: "text.secondary" }}>ROLE</TableCell>
                          {isManager && (
                            <TableCell align="right" sx={{ fontWeight: 600, fontSize: "0.8rem", color: "text.secondary" }}>ACTIONS</TableCell>
                          )}
                        </TableRow>
                      </TableHead>
                      <TableBody>
                        {members.map((member) => {
                          const isSelf = member.email.toLowerCase() === currentUser?.email?.toLowerCase();
                          return (
                            <TableRow key={member.id} hover>
                              <TableCell sx={{ py: 1.5 }}>
                                <Box sx={{ display: "flex", alignItems: "center", gap: 1.5 }}>
                                  <Avatar sx={{ width: 28, height: 28, fontSize: "0.8rem", bgcolor: "primary.light", color: "primary.main", fontWeight: 700 }}>
                                    {member.full_name.charAt(0).toUpperCase()}
                                  </Avatar>
                                  <Typography variant="body2" sx={{ fontWeight: 600 }}>
                                    {member.full_name} {isSelf && "(You)"}
                                  </Typography>
                                </Box>
                              </TableCell>
                              <TableCell sx={{ py: 1.5 }}>
                                <Typography variant="body2" color="text.secondary">
                                  {member.email}
                                </Typography>
                              </TableCell>
                              <TableCell sx={{ py: 1.5 }}>
                                <StatusChip label={member.role} type="role" />
                              </TableCell>
                              {isManager && (
                                <TableCell align="right" sx={{ py: 1.5 }}>
                                  {member.role !== "OWNER" && !isSelf && (
                                    <Button
                                      size="small"
                                      color="error"
                                      startIcon={<DeleteIcon />}
                                      onClick={() => {
                                        setMemberToRemove(member);
                                        setRemoveMemberConfirmOpen(true);
                                      }}
                                      sx={{ textTransform: "none", fontWeight: 600 }}
                                    >
                                      Remove
                                    </Button>
                                  )}
                                </TableCell>
                              )}
                            </TableRow>
                          );
                        })}
                      </TableBody>
                    </Table>
                  </TableContainer>
                </CardContent>
              </Card>

              {/* Pending Invitations List */}
              <Card sx={{ borderRadius: 3, border: "1px solid", borderColor: "divider", boxShadow: "0 1px 3px rgba(0,0,0,0.02)" }}>
                <CardContent sx={{ p: 0, "&:last-child": { pb: 0 } }}>
                  <Box sx={{ p: 2.5 }}>
                    <Typography variant="subtitle1" sx={{ fontWeight: 700 }}>
                      Pending Invites
                    </Typography>
                  </Box>
                  <Divider />
                  
                  {invitations.length === 0 ? (
                    <Box sx={{ p: 4, textAlign: "center" }}>
                      <Typography variant="body2" color="text.secondary">
                        No pending team invitations.
                      </Typography>
                    </Box>
                  ) : (
                    <TableContainer>
                      <Table>
                        <TableHead sx={{ bgcolor: "action.hover" }}>
                          <TableRow>
                            <TableCell sx={{ fontWeight: 600, fontSize: "0.8rem", color: "text.secondary" }}>INVITEE EMAIL</TableCell>
                            <TableCell sx={{ fontWeight: 600, fontSize: "0.8rem", color: "text.secondary" }}>ASSIGNED ROLE</TableCell>
                            <TableCell sx={{ fontWeight: 600, fontSize: "0.8rem", color: "text.secondary" }}>STATUS</TableCell>
                            <TableCell sx={{ fontWeight: 600, fontSize: "0.8rem", color: "text.secondary" }}>EXPIRES AT</TableCell>
                            {isManager && (
                              <TableCell align="right" sx={{ fontWeight: 600, fontSize: "0.8rem", color: "text.secondary" }}>ACTIONS</TableCell>
                            )}
                          </TableRow>
                        </TableHead>
                        <TableBody>
                          {invitations.map((invite) => (
                            <TableRow key={invite.id} hover>
                              <TableCell sx={{ py: 1.5 }}>
                                <Typography variant="body2" sx={{ fontWeight: 600 }}>
                                  {invite.email}
                                </Typography>
                              </TableCell>
                              <TableCell sx={{ py: 1.5 }}>
                                <StatusChip label={invite.role} type="role" />
                              </TableCell>
                              <TableCell sx={{ py: 1.5 }}>
                                <StatusChip label={invite.status} type="status" />
                              </TableCell>
                              <TableCell sx={{ py: 1.5 }}>
                                <Typography variant="body2" color="text.secondary">
                                  {new Date(invite.expires_at).toLocaleString()}
                                </Typography>
                              </TableCell>
                              {isManager && (
                                <TableCell align="right" sx={{ py: 1 }}>
                                  <Box sx={{ display: "flex", gap: 1, justifyContent: "flex-end" }}>
                                    <Button
                                      size="small"
                                      onClick={() => handleResendInvite(invite.id)}
                                      sx={{ textTransform: "none", fontWeight: 600 }}
                                    >
                                      Resend
                                    </Button>
                                    <Button
                                      size="small"
                                      color="error"
                                      onClick={() => handleCancelInvite(invite.id)}
                                      sx={{ textTransform: "none", fontWeight: 600 }}
                                    >
                                      Cancel
                                    </Button>
                                  </Box>
                                </TableCell>
                              )}
                            </TableRow>
                          ))}
                        </TableBody>
                      </Table>
                    </TableContainer>
                  )}
                </CardContent>
              </Card>
            </Box>
          )}

          {/* SETTINGS / DANGER ZONE TAB */}
          {activeTab === 2 && isOwner && (
            <Card sx={{ borderRadius: 3, border: "1px solid", borderColor: "error.light", boxShadow: "0 1px 3px rgba(0,0,0,0.02)", mt: 2 }}>
              <CardContent sx={{ p: 3 }}>
                <Typography variant="subtitle1" sx={{ fontWeight: 700, color: "error.main", mb: 1 }}>
                  Danger Zone
                </Typography>
                <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
                  Permanently delete this workspace, including all its connected repositories, member linkages, webhook records, and commit histories. This action is irreversible.
                </Typography>
                <Button
                  variant="contained"
                  color="error"
                  onClick={() => setDeleteConfirmOpen(true)}
                  sx={{ borderRadius: 2, textTransform: "none", fontWeight: 600 }}
                >
                  Delete Workspace
                </Button>
              </CardContent>
            </Card>
          )}

          {/* Invite Member Dialog */}
          <Dialog open={inviteOpen} onClose={() => setInviteOpen(false)} maxWidth="xs" fullWidth>
            <DialogTitle sx={{ fontWeight: 600 }}>Invite a Team Member</DialogTitle>
            <DialogContent sx={{ display: "flex", flexDirection: "column", gap: 2.5, pt: 1 }}>
              <TextField
                label="Email Address"
                type="email"
                value={inviteEmail}
                onChange={(e) => setInviteEmail(e.target.value)}
                fullWidth
                size="small"
                slotProps={{ input: { style: { borderRadius: 8 } } }}
              />
              <FormControl size="small" fullWidth>
                <InputLabel>Role</InputLabel>
                <Select
                  value={inviteRole}
                  onChange={(e) => setInviteRole(e.target.value)}
                  label="Role"
                  sx={{ borderRadius: 2 }}
                >
                  <MenuItem value="DEVELOPER">Developer</MenuItem>
                  <MenuItem value="MANAGER">Manager</MenuItem>
                </Select>
              </FormControl>
            </DialogContent>
            <DialogActions sx={{ px: 3, pb: 2 }}>
              <Button onClick={() => setInviteOpen(false)} disabled={actionLoading} color="inherit">
                Cancel
              </Button>
              <Button onClick={handleInviteSubmit} disabled={actionLoading || !inviteEmail} variant="contained">
                {actionLoading ? "Sending..." : "Send Invitation"}
              </Button>
            </DialogActions>
          </Dialog>

          {/* Transfer Ownership Dialog */}
          <Dialog open={transferOpen} onClose={() => setTransferOpen(false)} maxWidth="xs" fullWidth>
            <DialogTitle sx={{ fontWeight: 600 }}>Transfer Workspace Ownership</DialogTitle>
            <DialogContent sx={{ display: "flex", flexDirection: "column", gap: 2.5, pt: 1 }}>
              <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                Select an existing member to transfer workspace ownership to. You will lose owner rights and be demoted to a MANAGER.
              </Typography>
              <FormControl size="small" fullWidth>
                <InputLabel>New Owner</InputLabel>
                <Select
                  value={transferTargetId}
                  onChange={(e) => setTransferTargetId(e.target.value)}
                  label="New Owner"
                  sx={{ borderRadius: 2 }}
                >
                  {members
                    .filter((m) => m.role !== "OWNER")
                    .map((m) => (
                      <MenuItem key={m.id} value={m.id}>
                        {m.full_name} ({m.email})
                      </MenuItem>
                    ))}
                </Select>
              </FormControl>
            </DialogContent>
            <DialogActions sx={{ px: 3, pb: 2 }}>
              <Button onClick={() => setTransferOpen(false)} disabled={actionLoading} color="inherit">
                Cancel
              </Button>
              <Button
                onClick={handleTransferOwnership}
                disabled={actionLoading || !transferTargetId}
                variant="contained"
                color="warning"
              >
                {actionLoading ? "Transferring..." : "Confirm Transfer"}
              </Button>
            </DialogActions>
          </Dialog>

          {/* Remove Member Confirmation Dialog */}
          <ConfirmDialog
            open={removeMemberConfirmOpen}
            title="Remove Workspace Member"
            message={`Are you sure you want to remove ${memberToRemove?.full_name} (${memberToRemove?.email}) from this workspace? They will lose access to all repositories linked here.`}
            confirmText="Remove Member"
            severity="error"
            loading={actionLoading}
            onConfirm={handleRemoveMember}
            onCancel={() => {
              setRemoveMemberConfirmOpen(false);
              setMemberToRemove(null);
            }}
          />

          {/* Delete Workspace Confirmation Dialog */}
          <ConfirmDialog
            open={deleteConfirmOpen}
            title="Delete Workspace"
            message="Are you sure you want to permanently delete this workspace? This deletes all repositories, commits, and member configurations. This action cannot be undone."
            confirmText="Delete Workspace"
            severity="error"
            loading={actionLoading}
            onConfirm={handleDeleteWorkspace}
            onCancel={() => setDeleteConfirmOpen(false)}
          />
        </>
      )}
    </Box>
  );
};
