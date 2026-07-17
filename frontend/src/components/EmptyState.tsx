import React from "react";
import { Box, Typography, Button } from "@mui/material";

interface EmptyStateProps {
  title: string;
  description: string;
  actionText?: string;
  onAction?: () => void;
  icon?: React.ReactNode;
}

export const EmptyState: React.FC<EmptyStateProps> = ({
  title,
  description,
  actionText,
  onAction,
  icon,
}) => {
  return (
    <Box
      sx={{
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        py: 6,
        px: 3,
        textAlign: "center",
        border: "1px dashed",
        borderColor: "divider",
        borderRadius: 3,
        bgcolor: "background.paper",
        boxShadow: "0 1px 3px rgba(0,0,0,0.02)",
      }}
    >
      {icon && <Box sx={{ fontSize: 48, color: "text.secondary", mb: 2 }}>{icon}</Box>}
      <Typography variant="subtitle1" sx={{ fontWeight: 600, mb: 1 }}>
        {title}
      </Typography>
      <Typography variant="body2" color="text.secondary" sx={{ maxWidth: 400, mb: 3 }}>
        {description}
      </Typography>
      {actionText && onAction && (
        <Button variant="contained" color="primary" onClick={onAction} sx={{ borderRadius: 2 }}>
          {actionText}
        </Button>
      )}
    </Box>
  );
};
