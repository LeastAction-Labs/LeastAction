/*
 * Copyright (c) 2026 LeastAction Labs, Inc.
 * This file is part of LeastAction and is licensed under the
 * LeastAction Sustainable Use License (see LICENSE.md) or, for files
 * marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
 * Use of this file outside those terms is not permitted.
 */
import { useState } from 'react';

import { createFileRoute } from '@tanstack/react-router';

import { Lock, Visibility, VisibilityOff } from '@mui/icons-material';
import {
  Box,
  Button,
  Container,
  IconButton,
  InputAdornment,
  Paper,
  TextField,
  Typography,
} from '@mui/material';

import { CORE_FRONTEND_URL } from '@/config/urls';
import { useNotification } from '@/contexts/NotificationContext';
import { changePassword } from '@/services/user.service';

export const Route = createFileRoute('/change-password')({
  component: ChangePasswordPage,
});

function ChangePasswordPage() {
  const { showSuccess } = useNotification();
  const [formData, setFormData] = useState({
    current: '',
    next: '',
    confirm: '',
  });
  const [showPass, setShowPass] = useState({
    current: false,
    next: false,
    confirm: false,
  });
  const [errors, setErrors] = useState({ current: '', next: '', confirm: '' });
  const [loading, setLoading] = useState(false);

  const toggleShow = (field: keyof typeof showPass) => () =>
    setShowPass((prev) => ({ ...prev, [field]: !prev[field] }));

  const handleChange = (field: string) => (e: React.ChangeEvent<HTMLInputElement>) => {
    setFormData((prev) => ({ ...prev, [field]: e.target.value }));
    if (errors[field as keyof typeof errors]) {
      setErrors((prev) => ({ ...prev, [field]: '' }));
    }
  };

  const validate = () => {
    const newErrors = { current: '', next: '', confirm: '' };
    if (!formData.current) newErrors.current = 'Temporary password is required';
    if (!formData.next) {
      newErrors.next = 'New password is required';
    } else if (formData.next.length < 8) {
      newErrors.next = 'New password must be at least 8 characters';
    }
    if (!formData.confirm) {
      newErrors.confirm = 'Please confirm your new password';
    } else if (formData.next !== formData.confirm) {
      newErrors.confirm = 'Passwords do not match';
    }
    setErrors(newErrors);
    return !newErrors.current && !newErrors.next && !newErrors.confirm;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!validate()) return;
    setLoading(true);
    try {
      await changePassword(formData.current, formData.next);
      localStorage.removeItem('must_change_password');
      showSuccess('Password changed successfully');
      window.location.assign(`${CORE_FRONTEND_URL}/`);
    } catch {
      /* ignore */
    } finally {
      setLoading(false);
    }
  };

  const fields: Array<{
    key: keyof typeof formData;
    label: string;
  }> = [
    { key: 'current', label: 'Temporary Password' },
    { key: 'next', label: 'New Password' },
    { key: 'confirm', label: 'Confirm New Password' },
  ];

  return (
    <Container component="main" maxWidth="sm">
      <Box
        sx={{
          minHeight: '100vh',
          display: 'flex',
          flexDirection: 'column',
          justifyContent: 'center',
          alignItems: 'center',
        }}
      >
        <Paper elevation={3} sx={{ padding: 4, width: '100%', maxWidth: 420 }}>
          <Typography component="h1" variant="h5" sx={{ mb: 1, fontWeight: 'bold' }}>
            Set New Password
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
            Your account requires a password change before you can continue.
          </Typography>

          <Box component="form" onSubmit={(e) => void handleSubmit(e)}>
            {fields.map(({ key, label }) => (
              <TextField
                key={key}
                margin="normal"
                required
                fullWidth
                label={label}
                type={showPass[key] ? 'text' : 'password'}
                value={formData[key]}
                onChange={handleChange(key)}
                error={!!errors[key]}
                helperText={errors[key]}
                InputProps={{
                  startAdornment: (
                    <InputAdornment position="start">
                      <Lock />
                    </InputAdornment>
                  ),
                  endAdornment: (
                    <InputAdornment position="end">
                      <IconButton onClick={toggleShow(key)} edge="end">
                        {showPass[key] ? <VisibilityOff /> : <Visibility />}
                      </IconButton>
                    </InputAdornment>
                  ),
                }}
              />
            ))}

            <Button
              type="submit"
              fullWidth
              variant="contained"
              disabled={loading}
              sx={{ mt: 3, mb: 2, py: 1.5, fontSize: '1rem' }}
            >
              {loading ? 'Updating...' : 'Set New Password'}
            </Button>
          </Box>
        </Paper>
      </Box>
    </Container>
  );
}
