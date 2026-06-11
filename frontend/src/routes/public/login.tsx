/*
 * Copyright (c) 2026 LeastAction Labs, Inc.
 * This file is part of LeastAction and is licensed under the
 * LeastAction Sustainable Use License (see LICENSE.md) or, for files
 * marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
 * Use of this file outside those terms is not permitted.
 */
import { createFileRoute} from "@tanstack/react-router";
import { useState } from "react";
import {
  Box,
  TextField,
  Button,
  Typography,
  Paper,
  Container,
  InputAdornment,
  IconButton,
  Alert,
  FormControlLabel,
  Checkbox,
} from "@mui/material";
import { Visibility, VisibilityOff, Person, Lock } from "@mui/icons-material";
import { CORE_BACKEND_URL } from "@/config/urls";
import axios from "axios";

export const Route = createFileRoute("/public/login")({
  component: LoginComponent,
  validateSearch: (search: Record<string, unknown>) => {
    return {
      redirect:
        typeof search.redirect === "string" ? search.redirect : undefined,
    };
  },
});

function LoginComponent() {
  const [formData, setFormData] = useState({
    username: "",
    password: "",
  });
  const [showPassword, setShowPassword] = useState(false);
  const [businessMode, setBusinessMode] = useState(
    () => localStorage.getItem('la_view_mode') === 'business'
  );
  const [_logoutLoading,setLogoutLoading] = useState(false);
  const [loginError, setLoginError] = useState("");
  const [errors, setErrors] = useState({
    username: "",
    password: "",
  });

  const handleInputChange =
    (field: string) => (event: React.ChangeEvent<HTMLInputElement>) => {
      setFormData((prev) => ({
        ...prev,
        [field]: event.target.value,
      }));
      // Clear errors when user starts typing
      if (loginError) setLoginError("");
      if (errors[field as keyof typeof errors]) {
        setErrors((prev) => ({
          ...prev,
          [field]: "",
        }));
      }
    };

  const handleTogglePasswordVisibility = () => {
    setShowPassword((prev) => !prev);
  };

  const validateForm = () => {
    const newErrors = {
      username: "",
      password: "",
    };

    if (!formData.username.trim()) {
      newErrors.username = "Username is required";
    }

    if (!formData.password) {
      newErrors.password = "Password is required";
    } else if (formData.password.length < 6) {
      newErrors.password = "Password must be at least 6 characters";
    }

    setErrors(newErrors);
    return !newErrors.username && !newErrors.password;
  };

  const logout = async () => {
    setLogoutLoading(true)
    await axios.post(`${CORE_BACKEND_URL}/api/v1/logout`,{},{withCredentials:true})
    localStorage.removeItem("la_state");
    localStorage.removeItem("auth_request_started");
    setLogoutLoading(false)
    window.location.reload()
  };

  const handleSubmit = (event?: React.FormEvent) => {
    event?.preventDefault();
    if (!validateForm()) return;

    localStorage.setItem('la_view_mode', businessMode ? 'business' : 'developer');

    setLoginError("");

    const username = formData.username;
    const password = formData.password;
    const loginUrl = `${CORE_BACKEND_URL}/api/v1/login?username=${username}`;

    const form = document.createElement('form');
    form.method = 'POST';
    form.action = loginUrl;
    
    const userField = document.createElement('input');
    userField.type = 'hidden';
    userField.name = 'username';
    userField.value = username;
    form.appendChild(userField);
  
    const passField = document.createElement('input');
    passField.type = 'hidden';
    passField.name = 'password';
    passField.value = password;
    form.appendChild(passField);
  
    document.body.appendChild(form);
    form.submit();
    
  };

  return (
  
    <Container component="main" maxWidth="sm">
      <Box
        sx={{
          minHeight: "100vh",
          display: "flex",
          flexDirection: "column",
          justifyContent: "center",
          alignItems: "center",
        }}
      >
        <Paper
          elevation={3}
          sx={{
            padding: 4,
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            width: "100%",
            maxWidth: 400,
          }}
        >
          <Typography
            component="h1"
            variant="h4"
            sx={{ mb: 3, fontWeight: "bold" }}
          >
            Sign In
          </Typography>

          <Box sx={{ width: "100%" }}>
            {loginError && (
              <Alert severity="error" sx={{ mb: 2 }}>
                {loginError}
              </Alert>
            )}

            <TextField
              margin="normal"
              required
              fullWidth
              id="username"
              label="Username"
              name="username"
              autoComplete="username"
              autoFocus
              value={formData.username}
              onChange={handleInputChange("username")}
              error={!!errors.username}
              helperText={errors.username}
              InputProps={{
                startAdornment: (
                  <InputAdornment position="start">
                    <Person />
                  </InputAdornment>
                ),
              }}
            />

            <TextField
              margin="normal"
              required
              fullWidth
              name="password"
              label="Password"
              type={showPassword ? "text" : "password"}
              id="password"
              autoComplete="current-password"
              value={formData.password}
              onChange={handleInputChange("password")}
              error={!!errors.password}
              helperText={errors.password}
              InputProps={{
                startAdornment: (
                  <InputAdornment position="start">
                    <Lock />
                  </InputAdornment>
                ),
                endAdornment: (
                  <InputAdornment position="end">
                    <IconButton
                      aria-label="toggle password visibility"
                      onClick={handleTogglePasswordVisibility}
                      edge="end"
                    >
                      {showPassword ? <VisibilityOff /> : <Visibility />}
                    </IconButton>
                  </InputAdornment>
                ),
              }}
            />

            <FormControlLabel
              control={
                <Checkbox
                  checked={businessMode}
                  onChange={(e) => setBusinessMode(e.target.checked)}
                  size="small"
                />
              }
              label={
                <Box>
                  <Typography variant="body2" sx={{ fontWeight: 500 }}>Explorer View</Typography>
                  <Typography variant="caption" sx={{ color: 'text.secondary' }}>
                    Clean report explorer for non-technical users
                  </Typography>
                </Box>
              }
              sx={{ mt: 1.5, mb: 0.5, alignItems: 'flex-start', '& .MuiCheckbox-root': { pt: 0.25 } }}
            />

            <Button
              type="submit"
              fullWidth
              variant="contained"
              onClick={() => void handleSubmit()}
              sx={{ mt: 3, mb: 2, py: 1.5, fontSize: "1.1rem" }}
            >
              Sign In
            </Button>

            <Button
              type="submit"
              fullWidth
              variant="contained"
              onClick={() => void logout()}
              sx={{ mt: 3, mb: 2, py: 1.5, fontSize: "1.1rem" }}
            >
              Clear Site Data
            </Button>

            {/* Sign Up link hidden
            <Box sx={{ textAlign: "center", mt: 2 }}>
              <Typography variant="body2">
                Don't have an account?{" "}
                <Button
                  href="/public/register"
                  variant="text"
                  sx={{ textTransform: "none", fontWeight: "bold" }}
                >
                  Sign Up
                </Button>
              </Typography>
            </Box>
            */}
          </Box>
        </Paper>
      </Box>
    </Container>
  );
}