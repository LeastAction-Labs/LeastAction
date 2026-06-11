/*
 * Copyright (c) 2026 LeastAction Labs, Inc.
 * This file is part of LeastAction and is licensed under the
 * LeastAction Sustainable Use License (see LICENSE.md) or, for files
 * marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
 * Use of this file outside those terms is not permitted.
 */
import { createFileRoute } from '@tanstack/react-router'
import { useEffect } from 'react'
import axios from 'axios'
import { MARKETPLACE_URL, CORE_FRONTEND_URL } from '@/config/urls'

export const Route = createFileRoute('/public/marketplace-callback')({
  component: RouteComponent,
})

function RouteComponent() {
  console.log("marketplace callback")
  const callback = async () => {
    // Prevent duplicate requests

    if (localStorage.getItem('marketplace_auth_processing')) {
      console.log('Marketplace auth already processing, skipping duplicate request')
      return
    }

    if (localStorage.getItem('marketplace_auth_started')) {
      localStorage.setItem('marketplace_auth_processing', 'true')

      const queryString = window.location.search
      const params = new URLSearchParams(queryString)
      const stateFromQuery = params.get('state')
      const codeFromQuery = params.get('code')
      const stateFromLocalStorage = localStorage.getItem('marketplace_auth_state')
      if (stateFromLocalStorage?.includes(stateFromQuery||"") && codeFromQuery) {
        try {
          // Exchange code for access token
          await axios.post(
            `${MARKETPLACE_URL}/api/v1/marketplace/auth/oauth/token`,
            {
              grant_type: 'authorization_code',
              code: codeFromQuery,
              client_id: 'core-client',
            },
            {
              withCredentials: true, // Marketplace is on different domain
            }
          )
          localStorage.removeItem('marketplace_auth_started')
          localStorage.removeItem('marketplace_auth_state')
          localStorage.removeItem('marketplace_auth_processing')

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

        if (window.opener) {
         window.close()
        } else {
          window.location.assign(`${CORE_FRONTEND_URL}/marketplace`)
        }
      }
    }
  }

  useEffect(() => {
    void callback()
  }, [])

  return (
    <div>
      Authenticating with Marketplace...
    </div>
  )
}
