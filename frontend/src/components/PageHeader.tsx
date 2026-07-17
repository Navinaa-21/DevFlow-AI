import React from "react";
import { Box, Typography, Breadcrumbs, Link as MuiLink } from "@mui/material";
import { Link } from "react-router-dom";
import NavigateNextIcon from "@mui/icons-material/NavigateNext";

interface BreadcrumbItem {
  label: string;
  to?: string;
}

interface PageHeaderProps {
  title: string;
  subtitle?: string;
  breadcrumbs?: BreadcrumbItem[];
  action?: React.ReactNode;
}

export const PageHeader: React.FC<PageHeaderProps> = ({
  title,
  subtitle,
  breadcrumbs,
  action,
}) => {
  return (
    <Box
      sx={{
        display: "flex",
        flexDirection: { xs: "column", sm: "row" },
        justifyContent: "space-between",
        alignItems: { xs: "flex-start", sm: "center" },
        gap: 2,
        mb: 3,
        pb: 2.5,
        borderBottom: "1px solid",
        borderColor: "divider",
      }}
    >
      <Box>
        {breadcrumbs && breadcrumbs.length > 0 && (
          <Breadcrumbs
            separator={<NavigateNextIcon fontSize="small" sx={{ color: "text.disabled" }} />}
            sx={{ mb: 1, fontSize: "0.8rem" }}
          >
            {breadcrumbs.map((item, idx) => {
              const isLast = idx === breadcrumbs.length - 1;
              return isLast || !item.to ? (
                <Typography key={idx} variant="caption" color="text.secondary" sx={{ fontWeight: 500 }}>
                  {item.label}
                </Typography>
              ) : (
                <MuiLink
                  key={idx}
                  component={Link}
                  to={item.to}
                  color="inherit"
                  sx={{ textDecoration: "none", hover: { textDecoration: "underline" } }}
                >
                  {item.label}
                </MuiLink>
              );
            })}
          </Breadcrumbs>
        )}
        <Typography variant="h5" color="text.primary" sx={{ fontWeight: 700, letterSpacing: -0.5 }}>
          {title}
        </Typography>
        {subtitle && (
          <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
            {subtitle}
          </Typography>
        )}
      </Box>
      {action && <Box sx={{ flexShrink: 0 }}>{action}</Box>}
    </Box>
  );
};
