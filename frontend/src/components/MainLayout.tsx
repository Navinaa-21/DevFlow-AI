import React, { useEffect, useState } from "react";
import { useLocation, useNavigate, Link } from "react-router-dom";
import {
  Box,
  AppBar,
  Toolbar,
  Typography,
  IconButton,
  Drawer,
  List,
  ListItem,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  Divider,
  Avatar,
  Menu,
  MenuItem,
} from "@mui/material";
import MenuIcon from "@mui/icons-material/Menu";
import DashboardIcon from "@mui/icons-material/Dashboard";
import WorkspacesIcon from "@mui/icons-material/Workspaces";
import GitHubIcon from "@mui/icons-material/GitHub";
import MailOutlineIcon from "@mui/icons-material/Mail";
import KeyboardArrowDownIcon from "@mui/icons-material/KeyboardArrowDown";
import AccountCircleIcon from "@mui/icons-material/AccountCircle";
import LogoutIcon from "@mui/icons-material/Logout";
import toast from "react-hot-toast";

import { apiClient } from "../api/client";
import { clearTokens } from "../utils/auth";

const drawerWidth = 240;

interface UserInfo {
  id: string;
  full_name: string;
  email: string;
  avatar_url: string | null;
}

export const MainLayout: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [mobileOpen, setMobileOpen] = useState(false);
  const [anchorEl, setAnchorEl] = useState<HTMLElement | null>(null);
  const [user, setUser] = useState<UserInfo | null>(null);
  
  const location = useLocation();
  const navigate = useNavigate();

  // Load user profile details on mount
  useEffect(() => {
    apiClient
      .get("/auth/me")
      .then((res) => {
        setUser(res.data);
      })
      .catch(() => {
        toast.error("Session expired. Re-authenticating.");
        clearTokens();
        navigate("/login");
      });
  }, [navigate]);

  const handleDrawerToggle = () => {
    setMobileOpen(!mobileOpen);
  };

  const handleProfileMenuOpen = (event: React.MouseEvent<HTMLElement>) => {
    setAnchorEl(event.currentTarget);
  };

  const handleProfileMenuClose = () => {
    setAnchorEl(null);
  };

  const handleLogout = () => {
    handleProfileMenuClose();
    clearTokens();
    toast.success("Successfully signed out.");
    navigate("/login");
  };

  const menuItems = [
    { text: "Dashboard", icon: <DashboardIcon />, path: "/" },
    { text: "Workspaces", icon: <WorkspacesIcon />, path: "/workspaces" },
    { text: "Repositories", icon: <GitHubIcon />, path: "/repositories" },
    { text: "Invitations", icon: <MailOutlineIcon />, path: "/invitations" },
  ];

  const drawerContent = (
    <Box sx={{ display: "flex", flexDirection: "column", height: "100%", bgcolor: "background.paper" }}>
      {/* Sidebar Header */}
      <Box sx={{ p: 2, display: "flex", alignItems: "center", gap: 1.5 }}>
        <Box
          sx={{
            width: 28,
            height: 28,
            borderRadius: "6px",
            bgcolor: "primary.main",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            color: "white",
            fontWeight: "bold",
          }}
        >
          D
        </Box>
        <Typography variant="subtitle1" sx={{ fontWeight: 700, letterSpacing: -0.5 }}>
          DevFlow AI
        </Typography>
      </Box>
      <Divider />
      <List sx={{ px: 1, py: 1.5, flexGrow: 1 }}>
        {menuItems.map((item) => {
          const isSelected =
            item.path === "/"
              ? location.pathname === "/"
              : location.pathname.startsWith(item.path);

          return (
            <ListItem key={item.text} disablePadding sx={{ mb: 0.5 }}>
              <ListItemButton
                component={Link}
                to={item.path}
                selected={isSelected}
                sx={{
                  borderRadius: 2,
                  py: 1,
                  px: 2,
                  "&.Mui-selected": {
                    bgcolor: "primary.light",
                    color: "primary.main",
                    "&:hover": {
                      bgcolor: "primary.light",
                    },
                    "& .MuiListItemIcon-root": {
                      color: "primary.main",
                    },
                  },
                }}
              >
                <ListItemIcon sx={{ minWidth: 36, color: isSelected ? "primary.main" : "text.secondary" }}>
                  {item.icon}
                </ListItemIcon>
                <ListItemText
                  primary={
                    <Typography sx={{ fontSize: "0.875rem", fontWeight: isSelected ? 600 : 500 }}>
                      {item.text}
                    </Typography>
                  }
                />
              </ListItemButton>
            </ListItem>
          );
        })}
      </List>
      <Divider />
      {user && (
        <Box sx={{ p: 2, display: "flex", alignItems: "center", gap: 1.5 }}>
          <Avatar sx={{ bgcolor: "primary.main", width: 32, height: 32, fontSize: "0.9rem" }}>
            {user.full_name.charAt(0).toUpperCase()}
          </Avatar>
          <Box sx={{ overflow: "hidden", flexGrow: 1 }}>
            <Typography variant="body2" noWrap sx={{ fontWeight: 600 }}>
              {user.full_name}
            </Typography>
            <Typography variant="caption" color="text.secondary" noWrap sx={{ display: "block" }}>
              {user.email}
            </Typography>
          </Box>
        </Box>
      )}
    </Box>
  );

  return (
    <Box sx={{ display: "flex", minHeight: "100vh", bgcolor: "background.default" }}>
      {/* AppBar Header */}
      <AppBar
        position="fixed"
        elevation={0}
        sx={{
          width: { md: `calc(100% - ${drawerWidth}px)` },
          ml: { md: `${drawerWidth}px` },
          borderBottom: "1px solid",
          borderColor: "divider",
          bgcolor: "background.paper",
          color: "text.primary",
        }}
      >
        <Toolbar sx={{ justifyContent: "space-between", px: { xs: 2, md: 3 } }}>
          <IconButton
            color="inherit"
            aria-label="open drawer"
            edge="start"
            onClick={handleDrawerToggle}
            sx={{ mr: 2, display: { md: "none" } }}
          >
            <MenuIcon />
          </IconButton>
          
          <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
            <Typography variant="body2" color="text.secondary" sx={{ fontWeight: 600 }}>
              POC Platform
            </Typography>
          </Box>

          <Box sx={{ display: "flex", alignItems: "center" }}>
            {user && (
              <Box
                onClick={handleProfileMenuOpen}
                sx={{
                  display: "flex",
                  alignItems: "center",
                  gap: 0.5,
                  cursor: "pointer",
                  py: 0.5,
                  px: 1,
                  borderRadius: 1.5,
                  "&:hover": { bgcolor: "action.hover" },
                }}
              >
                <Avatar sx={{ bgcolor: "primary.light", color: "primary.main", width: 28, height: 28, fontSize: "0.8rem", fontWeight: 700 }}>
                  {user.full_name.charAt(0).toUpperCase()}
                </Avatar>
                <KeyboardArrowDownIcon sx={{ fontSize: 16, color: "text.secondary" }} />
              </Box>
            )}
            <Menu
              anchorEl={anchorEl}
              open={Boolean(anchorEl)}
              onClose={handleProfileMenuClose}
              transformOrigin={{ horizontal: "right", vertical: "top" }}
              anchorOrigin={{ horizontal: "right", vertical: "bottom" }}
              slotProps={{
                paper: {
                  elevation: 0,
                  sx: {
                    overflow: "visible",
                    filter: "drop-shadow(0px 2px 8px rgba(0,0,0,0.08))",
                    mt: 1.5,
                    border: "1px solid",
                    borderColor: "divider",
                    borderRadius: 2,
                    minWidth: 160,
                    "& .MuiMenuItem-root": {
                      fontSize: "0.875rem",
                      borderRadius: 1,
                      mx: 0.75,
                      my: 0.25,
                    },
                  },
                },
              }}
            >
              <MenuItem onClick={() => { handleProfileMenuClose(); navigate("/"); }}>
                <ListItemIcon sx={{ minWidth: 28 }}><AccountCircleIcon fontSize="small" /></ListItemIcon>
                Profile Details
              </MenuItem>
              <Divider />
              <MenuItem onClick={handleLogout} sx={{ color: "error.main" }}>
                <ListItemIcon sx={{ minWidth: 28, color: "error.main" }}><LogoutIcon fontSize="small" /></ListItemIcon>
                Sign Out
              </MenuItem>
            </Menu>
          </Box>
        </Toolbar>
      </AppBar>

      {/* Navigation SideBar Drawer */}
      <Box
        component="nav"
        sx={{ width: { md: drawerWidth }, flexShrink: { md: 0 } }}
        aria-label="navigation panels"
      >
        <Drawer
          variant="temporary"
          open={mobileOpen}
          onClose={handleDrawerToggle}
          ModalProps={{ keepMounted: true }}
          sx={{
            display: { xs: "block", md: "none" },
            "& .MuiDrawer-paper": {
              boxSizing: "border-box",
              width: drawerWidth,
              borderRight: "1px solid",
              borderColor: "divider",
            },
          }}
        >
          {drawerContent}
        </Drawer>
        <Drawer
          variant="permanent"
          sx={{
            display: { xs: "none", md: "block" },
            "& .MuiDrawer-paper": {
              boxSizing: "border-box",
              width: drawerWidth,
              borderRight: "1px solid",
              borderColor: "divider",
            },
          }}
          open
        >
          {drawerContent}
        </Drawer>
      </Box>

      {/* Main Content Area */}
      <Box
        component="main"
        sx={{
          flexGrow: 1,
          p: { xs: 2.5, md: 4 },
          width: { md: `calc(100% - ${drawerWidth}px)` },
          mt: "64px",
          minHeight: "calc(100vh - 64px)",
        }}
      >
        {children}
      </Box>
    </Box>
  );
};
