/*
 * Copyright (c) 2026 LeastAction Labs, Inc.
 * This file is part of LeastAction and is licensed under the
 * LeastAction Sustainable Use License (see LICENSE.md) or, for files
 * marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
 * Use of this file outside those terms is not permitted.
 */
import { createFileRoute } from '@tanstack/react-router'
import { useEffect, useState, useCallback } from 'react'
import { TextField, Box, Button, CircularProgress, Container, Paper, Typography } from '@mui/material'
import axios from 'axios'
import { MARKETPLACE_URL, CORE_FRONTEND_URL } from '@/config/urls'

export const Route = createFileRoute('/public/marketplace-callback')({
  component: RouteComponent,
})

function RouteComponent() {
  console.log("marketplace callback")
  const [code, setCode] = useState('')
  const [loading, setLoading] = useState(false)

  const handleSubmitCode = useCallback(async (codeToSubmit: string) => {
    // Prevent duplicate requests
    if (localStorage.getItem('marketplace_auth_processing')) {
      console.log('Marketplace auth already processing, skipping duplicate request')
      return
    }

    if (localStorage.getItem('marketplace_auth_started')) {
      localStorage.setItem('marketplace_auth_processing', 'true')
      setLoading(true)

      const queryString = window.location.search
      const params = new URLSearchParams(queryString)
      const stateFromQuery = params.get('state')
      const stateFromLocalStorage = localStorage.getItem('marketplace_auth_state')

      // Validate states and verify code is present
      if (stateFromLocalStorage?.includes(stateFromQuery || "") && codeToSubmit) {
        try {
          // Exchange code for access token
          await axios.post(
            `${MARKETPLACE_URL}/api/v1/marketplace/auth/oauth/token`,
            {
              grant_type: 'authorization_code',
              code: codeToSubmit,
              client_id: 'core-client',
            },
            {
              withCredentials: true, // Marketplace is on different domain
            }
          )

          localStorage.removeItem('marketplace_auth_started')
          localStorage.removeItem('marketplace_auth_state')
          localStorage.removeItem('marketplace_auth_processing')
          setLoading(false)

          // Close the popup window if opened from parent
          if (window.opener) {
            window.close()
          } else {
            // If not a popup, redirect to home
            window.location.assign(`${CORE_FRONTEND_URL}/`)
          }
        } catch (error: any) {
          console.error('Marketplace auth error:', error)
          localStorage.removeItem('marketplace_auth_started')
          localStorage.removeItem('marketplace_auth_state')
          localStorage.removeItem('marketplace_auth_processing')
          setLoading(false)

          if (window.opener) {
            window.opener.postMessage(
              { type: 'MARKETPLACE_AUTH_ERROR', error: error.message },
              window.location.origin
            )
            window.close()
          } else {
            alert('Failed to connect to marketplace. Please try again.')
            window.location.assign(`${CORE_FRONTEND_URL}/`)
          }
        }
      } else {
        console.error('State mismatch or missing code')
        localStorage.removeItem('marketplace_auth_started')
        localStorage.removeItem('marketplace_auth_state')
        localStorage.removeItem('marketplace_auth_processing')
        setLoading(false)

        if (window.opener) {
          window.close()
        } else {
          window.location.assign(`${CORE_FRONTEND_URL}/marketplace`)
        }
      }
    }
  }, [])

  // Auto-trigger callback if code is found in URL params
  useEffect(() => {
    const queryString = window.location.search
    const params = new URLSearchParams(queryString)
    const codeFromQuery = params.get('code')

    if (codeFromQuery && codeFromQuery !== code) {
      setCode(codeFromQuery)
      return
    }

    if (codeFromQuery && codeFromQuery === code) {
      void handleSubmitCode(code)
    }
  }, [code, handleSubmitCode])

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
            Enter verification code
          </Typography>

          <Box sx={{ width: "100%" }}>
            <TextField
              margin="normal"
              required
              fullWidth
              id="code"
              label="Code"
              name="Code"
              autoFocus
              value={code}
              onChange={(e) => setCode(e.target.value)}
              disabled={loading}
            />
            <Button
              type="submit"
              fullWidth
              variant="contained"
              onClick={() => void handleSubmitCode(code)}
              disabled={loading || !code.trim()}
              sx={{ mt: 3, mb: 2, py: 1.5, fontSize: "1.1rem" }}
            >
              {loading ? (
                <CircularProgress size={24} color="inherit" />
              ) : (
                "Sign In"
              )}
            </Button>
          </Box>
        </Paper>
      </Box>
    </Container>
  )
}
