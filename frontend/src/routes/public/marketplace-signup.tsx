/*
 * Copyright (c) 2026 LeastAction Labs, Inc.
 * This file is part of LeastAction and is licensed under the
 * LeastAction Sustainable Use License (see LICENSE.md) or, for files
 * marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
 * Use of this file outside those terms is not permitted.
 */
import { marketplaceSignup } from '@/services/marketplace.service';
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

export const Route = createFileRoute('/public/marketplace-signup')({
  component: RouteComponent,
})

function RouteComponent() {
  const [username, setUsername] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  const handleSignup = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");

    if (password !== confirmPassword) {
      setError("Passwords do not match");
      return;
    }

    if (password.length < 8) {
      setError("Password must be at least 8 characters long");
      return;
    }

    setLoading(true);

    try {
      await marketplaceSignup({ username, email, password });
      // Redirect to login after successful signup
      void navigate({ to: "/public/marketplace-login" });
    } catch {
      const errorMessage = "An error occurred during signup";
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
            Marketplace Sign Up
          </Typography>

          {error && (
            <Alert severity="error" sx={{ mb: 2 }}>
              {error}
            </Alert>
          )}

          <Box component="form" onSubmit={() => void handleSignup()}>
            <TextField
              fullWidth
              label="Username"
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              required
              margin="normal"
              sx={{
                "& .MuiOutlinedInput-root": {
                  color: "var(--text-primary)",
                  "& fieldset": { borderColor: "var(--border)" },
                  "&:hover fieldset": { borderColor: "var(--border-hover)" },
                  "&.Mui-focused fieldset": { borderColor: "var(--accent-primary)" },
                },
                "& .MuiInputLabel-root": { color: "var(--text-secondary)" },
                "& .MuiInputLabel-root.Mui-focused": { color: "var(--accent-primary)" },
              }}
            />
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
              helperText="Password must be at least 8 characters"
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
                "& .MuiFormHelperText-root": {
                  color: "var(--text-secondary)",
                },
              }}
            />
            <TextField
              fullWidth
              label="Confirm Password"
              type="password"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
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
              {loading ? "Creating account..." : "Sign Up"}
            </Button>
            <Box sx={{ textAlign: "center", mt: 2 }}>
              <Link
                component="button"
                type="button"
                onClick={() => void navigate({ to: "/public/marketplace-login" })}
                sx={{
                  color: "var(--accent-primary)",
                  textDecoration: "none",
                  "&:hover": {
                    textDecoration: "underline",
                  },
                }}
              >
                Already have an account? Login
              </Link>
            </Box>
          </Box>
        </Paper>
      </Container>
    </Box>
  );
}
