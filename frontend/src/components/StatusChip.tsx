import React from "react";
import { Chip } from "@mui/material";

interface StatusChipProps {
  label: string;
  type: "status" | "role" | "visibility" | "webhook" | "provider";
}

type ChipColor = "default" | "primary" | "secondary" | "error" | "info" | "success" | "warning";
type ChipVariant = "filled" | "outlined";

export const StatusChip: React.FC<StatusChipProps> = ({ label, type }) => {
  const norm = label.toLowerCase().trim();

  let color: ChipColor = "default";
  let variant: ChipVariant = "outlined";

  if (type === "status") {
    if (norm === "active" || norm === "accepted" || norm === "processed" || norm === "completed" || norm === "success") {
      color = "success";
      variant = "filled";
    } else if (norm === "pending" || norm === "received" || norm === "processing") {
      color = "warning";
      variant = "filled";
    } else if (norm === "archived" || norm === "cancelled" || norm === "declined" || norm === "expired" || norm === "failed") {
      color = "error";
      variant = "filled";
    }
  } else if (type === "role") {
    if (norm === "owner") {
      color = "primary";
      variant = "filled";
    } else if (norm === "manager" || norm === "admin") {
      color = "secondary";
      variant = "filled";
    } else {
      color = "default";
      variant = "outlined";
    }
  } else if (type === "visibility") {
    if (norm === "public") {
      color = "success";
      variant = "outlined";
    } else {
      color = "default";
      variant = "outlined";
    }
  } else if (type === "webhook") {
    if (norm === "true" || norm === "enabled" || norm === "active") {
      color = "success";
      variant = "outlined";
    } else {
      color = "error";
      variant = "outlined";
    }
  } else if (type === "provider") {
    color = "info";
    variant = "filled";
  }

  return (
    <Chip
      label={label.toUpperCase()}
      size="small"
      color={color}
      variant={variant}
      sx={{
        fontWeight: 600,
        fontSize: "0.72rem",
        borderRadius: "6px",
        height: "22px",
      }}
    />
  );
};
