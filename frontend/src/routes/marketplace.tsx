/*
 * Copyright (c) 2026 LeastAction Labs, Inc.
 * This file is part of LeastAction and is licensed under the
 * LeastAction Sustainable Use License (see LICENSE.md) or, for files
 * marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
 * Use of this file outside those terms is not permitted.
 */
import { useEffect, useState } from 'react';

import { createFileRoute, useNavigate, useSearch } from '@tanstack/react-router';

import MarketplaceLayout from '@/components/marketplace/MarketplaceLayout';
import { CatalogProvider } from '@/contexts/CatalogContext';

interface MarketplaceSearchParams {
  q?: string;
  laui?: string;
}

export const Route = createFileRoute('/marketplace')({
  component: RouteComponent,
  validateSearch: (search: Record<string, unknown>): MarketplaceSearchParams => {
    return {
      q: typeof search.q === 'string' ? search.q : undefined,
      laui: typeof search.laui === 'string' ? search.laui : undefined,
    };
  },
});

function RouteComponent() {
  const [isAuthenticating, setIsAuthenticating] = useState(false);
  const search = useSearch({ from: '/marketplace' });
  const navigate = useNavigate();

  /*
  useEffect(()=>{
    const auth = async () => { 
    try {
      // Check if user has marketplace token stored
      await checkMarketplaceToken();
      return 
    } catch (error) {
      console.error("Error checking marketplace token:", error);
      // If check fails, proceed with OAuth flow
    }

    if(!isAuthenticating){
    // Not authenticated, start OAuth flow
    setIsAuthenticating(true);
    const state = Math.random().toString(36).substring(2, 15) + Math.random().toString(36).substring(2, 15);
    const x = JSON.parse(localStorage.getItem('marketplace_auth_state')||"[]")
    x.push(state)
    localStorage.setItem('marketplace_auth_state', JSON.stringify(x));
    localStorage.setItem('marketplace_auth_started', 'true');

    const clientId = 'core-client';
    const redirectUri = encodeURIComponent(`${CORE_FRONTEND_URL}/public/marketplace-callback`);
    const marketplaceAuthUrl = `${MARKETPLACE_URL}/api/v1/marketplace/auth/oauth/authorize?client_id=${clientId}&redirect_uri=${redirectUri}&state=${state}`;
    window.open(marketplaceAuthUrl, '_blank');
    }
    }
    auth()
  }
  ,[])
  */

  useEffect(() => {
    const handleMessage = (event: MessageEvent) => {
      // Verify origin for security
      if (event.origin !== window.location.origin) {
        return;
      }
      if (event.data.type === 'MARKETPLACE_AUTH_SUCCESS') {
        setIsAuthenticating(false);
      } else if (event.data.type === 'MARKETPLACE_AUTH_ERROR') {
        console.error('Marketplace authentication failed:', event.data.error);
        setIsAuthenticating(false);
      }
    };

    window.addEventListener('message', handleMessage);
    return () => {
      window.removeEventListener('message', handleMessage);
    };
  }, []);

  return (
    <>
      {isAuthenticating ? (
        <div>Authenticating</div>
      ) : (
        <CatalogProvider>
          <MarketplaceLayout
            initialQuery={search.q}
            initialLaui={search.laui}
            onSearchChange={(q) =>
              void navigate({
                to: '/marketplace',
                search: (prev) => ({ ...prev, q: q || undefined }),
                replace: true,
              })
            }
            onItemSelect={(laui) =>
              void navigate({ to: '/marketplace', search: (prev) => ({ ...prev, laui }) })
            }
            onBack={() =>
              void navigate({
                to: '/marketplace',
                search: (prev) => ({ ...prev, laui: undefined }),
              })
            }
          />
        </CatalogProvider>
      )}
    </>
  );
}
