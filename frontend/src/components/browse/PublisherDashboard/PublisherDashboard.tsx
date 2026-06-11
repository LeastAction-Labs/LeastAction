/*
 * Copyright (c) 2026 LeastAction Labs, Inc.
 * This file is part of LeastAction and is licensed under the
 * LeastAction Sustainable Use License (see LICENSE.md) or, for files
 * marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
 * Use of this file outside those terms is not permitted.
 */
/*
import { useState, useEffect } from "react";
import {
  Box,
  Typography,
  CircularProgress,
  List,
  ListItem,
  ListItemButton,
  ListItemText,
  Divider,
  Alert,
  Chip,
} from "@mui/material";
import { useNavigate } from "@tanstack/react-router";
import { httpJson } from "@/services/api";
import { CORE_BACKEND_URL } from "@/config/urls";
import { CatalogMode, useCatalog } from "@/contexts/CatalogContext";

// Item types eligible for publishing
const PUBLISHABLE_TYPES = ["payload", "action", "operator", "skill"] as const;
type PublishableType = (typeof PUBLISHABLE_TYPES)[number];

interface PublisherItem {
  laui: string;
  name: string;
  item_type: string;
  is_published: boolean;
}

type GroupedItems = Record<PublishableType, PublisherItem[]>;

const TYPE_LABELS: Record<PublishableType, string> = {
  payload: "Payloads",
  action: "Actions",
  operator: "Operators",
  skill: "Skills",
};

export default function PublisherDashboard() {
  const navigate = useNavigate();
  const { setMode } = useCatalog();
  const [grouped, setGrouped] = useState<GroupedItems>({ payload: [], action: [], operator: [], skill: [] });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const load = async () => {
    try {
      setLoading(true);
      setError("");
      const items = await httpJson<PublisherItem[]>(`${CORE_BACKEND_URL}/api/v1/user/publisher-items`);
      const g: GroupedItems = { payload: [], action: [], operator: [], skill: [] };
      for (const item of items) {
        const baseType = PUBLISHABLE_TYPES.find(
          (p) => item.item_type === p || item.item_type.startsWith(p + ".")
        );
        if (baseType) g[baseType].push(item);
      }
      setGrouped(g);
    } catch (err: unknown) {
      const msg = (err as { message?: string })?.message || String(err);
      setError(`Failed to load your items: ${msg}`);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, []);

  const handleItemClick = (item: PublisherItem) => {
    setMode(CatalogMode.DEFAULT);
    navigate({ to: "/path", search: { laui: item.laui, itemtype: item.item_type } });
  };

  const hasAnyItems = PUBLISHABLE_TYPES.some((t) => grouped[t].length > 0);

  return (
    <Box sx={{ p: 3, overflow: "auto", height: "100%" }}>
      <Typography variant="h5" sx={{ color: "var(--text-primary)", fontWeight: 600, mb: 1 }}>
        Publisher Dashboard
      </Typography>
      <Typography variant="body2" sx={{ color: "var(--text-secondary)", mb: 3 }}>
        Items you own that are eligible for publishing to the Marketplace.
      </Typography>

      {loading && (
        <Box sx={{ display: "flex", justifyContent: "center", pt: 4 }}>
          <CircularProgress size={32} />
        </Box>
      )}

      {!loading && error && (
        <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>
      )}

      {!loading && !error && !hasAnyItems && (
        <Typography sx={{ color: "var(--text-secondary)" }}>
          No publishable items found. Create items of type payload, action, operator, or skill to publish them here.
        </Typography>
      )}

      {!loading && !error && PUBLISHABLE_TYPES.map((type) => {
        const items = grouped[type];
        if (items.length === 0) return null;
        return (
          <Box key={type} sx={{ mb: 3 }}>
            <Typography
              variant="subtitle1"
              sx={{ color: "var(--text-primary)", fontWeight: 600, mb: 1, textTransform: "capitalize" }}
            >
              {TYPE_LABELS[type]}
            </Typography>
            <Box
              sx={{
                border: "1px solid var(--border)",
                borderRadius: 1,
                bgcolor: "var(--bg-secondary)",
                overflow: "hidden",
              }}
            >
              <List disablePadding>
                {items.map((item, idx) => (
                  <Box key={item.laui}>
                    {idx > 0 && <Divider sx={{ borderColor: "var(--border)" }} />}
                    <ListItem disablePadding>
                      <ListItemButton
                        onClick={() => handleItemClick(item)}
                        sx={{
                          py: 1,
                          px: 2,
                          "&:hover": { bgcolor: "var(--bg-tertiary)" },
                        }}
                      >
                        <ListItemText
                          primary={
                            <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
                              <Typography sx={{ color: "var(--text-primary)", fontSize: "0.875rem", fontWeight: 500 }}>
                                {item.name}
                              </Typography>
                              {item.is_published && (
                                <Chip
                                  label="Published"
                                  size="small"
                                  sx={{
                                    height: 18,
                                    fontSize: "0.65rem",
                                    bgcolor: "#1b5e20",
                                    color: "#a5d6a7",
                                    fontWeight: 600,
                                  }}
                                />
                              )}
                            </Box>
                          }
                          secondary={
                            <Typography sx={{ color: "var(--text-secondary)", fontSize: "0.75rem" }}>
                              {item.item_type}
                            </Typography>
                          }
                        />
                      </ListItemButton>
                    </ListItem>
                  </Box>
                ))}
              </List>
            </Box>
          </Box>
        );
      })}
    </Box>
  );
}
*/
