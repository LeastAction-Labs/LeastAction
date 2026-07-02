/*
 * Copyright (c) 2026 LeastAction Labs, Inc.
 * This file is part of LeastAction and is licensed under the
 * LeastAction Sustainable Use License (see LICENSE.md) or, for files
 * marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
 * Use of this file outside those terms is not permitted.
 */
import { createFileRoute} from '@tanstack/react-router'
import { useEffect, useState } from 'react'
import { TextField, Box, Button, CircularProgress, Container, Paper, Typography } from '@mui/material'
import axios  from 'axios'
import { CORE_BACKEND_URL, CORE_FRONTEND_URL } from '@/config/urls'

export const Route = createFileRoute('/public/callback') ({
  component: RouteComponent,
})

function RouteComponent() {

  const [code, setCode] = useState('')
  const [provider, setProvider] = useState('leastaction')
  const [loading,setLoading] = useState(false)

  useEffect(()=>{
    const queryString = window.location.search
    const params = new URLSearchParams(queryString)
    const codeFromQuery = params.get('code')
    const providerFromQuery = params.get('provider')
    if(providerFromQuery) setProvider(providerFromQuery)
    if(codeFromQuery && codeFromQuery !== code ){
      setCode(codeFromQuery)
      return
    }
    if(codeFromQuery === code) void handleSubmitCode()
  },[code])

  const handleSubmitCode = async () => {
    setLoading(true)
    if(localStorage.getItem('auth_request_started')) {
      const queryString = window.location.search
      const params = new URLSearchParams(queryString)
      const state_from_query = params.get('state')
      const state_from_localstorage = localStorage.getItem('la_state')
      if( state_from_localstorage === state_from_query ) {
      try{
        const response = await axios.post( `${CORE_BACKEND_URL}/api/v1/token` ,
          {
            grant_type : 'authorization_code' ,
            credentials : {code,provider}
          },
          {withCredentials : true }
        )
        const data = response.data
        localStorage.removeItem('auth_request_started')
        if (data?.must_change_password) {
          localStorage.setItem('must_change_password', 'true')
          window.location.assign(`${CORE_FRONTEND_URL}/change-password`)
        } else {
          window.location.assign(`${CORE_FRONTEND_URL}/` )
        }
      }
      catch {
        console.log('invalid totp')
        localStorage.removeItem('auth_request_started')
        window.location.assign(`${CORE_FRONTEND_URL}/public/login`)
      }
      } else {
        console.log('state mismatch')
        localStorage.removeItem('auth_request_started')
        window.location.assign(`${CORE_FRONTEND_URL}/public/login`)
      }
    } else {
      localStorage.removeItem('auth_request_started')
      window.location.assign(`${CORE_FRONTEND_URL}/public/login`)
    }
  }

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
            Enter verfication code
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
              onChange={(e)=>setCode(e.target.value)}
            />
            <Button
              type="submit"
              fullWidth
              variant="contained"
              onClick={() => void handleSubmitCode()}
              disabled={loading}
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
