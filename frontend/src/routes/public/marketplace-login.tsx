/*
 * Copyright (c) 2026 LeastAction Labs, Inc.
 * This file is part of LeastAction and is licensed under the
 * LeastAction Sustainable Use License (see LICENSE.md) or, for files
 * marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
 * Use of this file outside those terms is not permitted.
 */
import { marketplaceLogin } from '@/services/marketplace.service';
import { MARKETPLACE_URL } from '@/config/urls';
import { createFileRoute, useNavigate } from '@tanstack/react-router'
import React, { useState } from "react";
import {
  Box,
  Container,
  Typography,
  TextField,
  Button,
  Paper,
  Link,
  Alert,
} from "@mui/material";

export const Route = createFileRoute('/public/marketplace-login')({
  component: RouteComponent,
})

function RouteComponent() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();
  const searchParams = new URLSearchParams(window.location.search);
  const search = {
    oauth_flow: searchParams.get('oauth_flow') || undefined,
    redirect_uri: searchParams.get('redirect_uri') ? decodeURIComponent(searchParams.get('redirect_uri')!) : undefined,
    state: searchParams.get('state') || undefined,
    client_id: searchParams.get('client_id') || undefined,
  };

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);

    try {
      await marketplaceLogin({email,password})

      // If this is an OAuth flow, redirect to code generation endpoint
      if (search.oauth_flow === "true" && search.redirect_uri && search.state && search.client_id) {
        // After login, the session cookie is set, so we can redirect to the OAuth redirect endpoint
        // The backend will read the session cookie and generate the code
        const redirectUrl = `${MARKETPLACE_URL}/api/v1/marketplace/auth/oauth/redirect-with-code`;
        // Note: user_id will be extracted from session cookie on backend
        window.location.href = redirectUrl;
        return;
      }

      // Normal login flow - redirect to home
      await navigate({ to: "/" });
    } catch {
      const errorMessage = "An error occurred during login";
      setError(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  return (
    <Box
      sx={{
        minHeight: "100vh",
        display: "flex",
        flexDirection: "column",
        bgcolor: "var(--bg-primary)",
        color: "var(--text-primary)",
      }}
    >
      <Container maxWidth="sm" sx={{ mt: 8, mb: 4 }}>
        <Paper
          elevation={3}
          sx={{
            p: 4,
            bgcolor: "var(--bg-secondary)",
            border: "1px solid var(--border)",
          }}
        >
          <Typography variant="h4" component="h1" gutterBottom sx={{ mb: 3 }}>
            Marketplace Login
          </Typography>

          {error && (
            <Alert severity="error" sx={{ mb: 2 }}>
              {error}
            </Alert>
          )}

          <Box component="form" onSubmit={(e) => void handleLogin(e)}>
            <TextField
              fullWidth
              label="Email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              margin="normal"
              sx={{
                "& .MuiOutlinedInput-root": {
                  color: "var(--text-primary)",
                  "& fieldset": {
                    borderColor: "var(--border)",
                  },
                  "&:hover fieldset": {
                    borderColor: "var(--border-hover)",
                  },
                  "&.Mui-focused fieldset": {
                    borderColor: "var(--accent-primary)",
                  },
                },
                "& .MuiInputLabel-root": {
                  color: "var(--text-secondary)",
                },
                "& .MuiInputLabel-root.Mui-focused": {
                  color: "var(--accent-primary)",
                },
              }}
            />
            <TextField
              fullWidth
              label="Password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              margin="normal"
              sx={{
                "& .MuiOutlinedInput-root": {
                  color: "var(--text-primary)",
                  "& fieldset": {
                    borderColor: "var(--border)",
                  },
                  "&:hover fieldset": {
                    borderColor: "var(--border-hover)",
                  },
                  "&.Mui-focused fieldset": {
                    borderColor: "var(--accent-primary)",
                  },
                },
                "& .MuiInputLabel-root": {
                  color: "var(--text-secondary)",
                },
                "& .MuiInputLabel-root.Mui-focused": {
                  color: "var(--accent-primary)",
                },
              }}
            />
            <Button
              type="submit"
              fullWidth
              variant="contained"
              disabled={loading}
              sx={{
                mt: 3,
                mb: 2,
                bgcolor: "var(--accent-primary)",
                "&:hover": {
                  bgcolor: "var(--accent-hover)",
                },
              }}
            >
              {loading ? "Logging in..." : "Login"}
            </Button>
            <Box sx={{ textAlign: "center", mt: 2 }}>
              <Link
                component="button"
                type="button"
                onClick={() => void navigate({ to: "/public/marketplace-signup" })}
                sx={{
                  color: "var(--accent-primary)",
                  textDecoration: "none",
                  "&:hover": {
                    textDecoration: "underline",
                  },
                }}
              >
                Don't have an account? Sign up
              </Link>
            </Box>
          </Box>
        </Paper>
      </Container>
    </Box>
  );
};