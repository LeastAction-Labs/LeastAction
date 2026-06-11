/*
 * Copyright (c) 2026 LeastAction Labs, Inc.
 * This file is part of LeastAction and is licensed under the
 * LeastAction Sustainable Use License (see LICENSE.md) or, for files
 * marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
 * Use of this file outside those terms is not permitted.
 */
import React, { createContext, useContext, useEffect, useState } from 'react';

import type { MarketplaceUser } from '@/services/marketplace.service';
import { getMarketplaceUser, marketplaceCheckLoggedIn } from '@/services/marketplace.service';

export interface MarketplaceState {
  userAuthenticated: boolean;
  user: MarketplaceUser | null;
  publishAccess: boolean;
  triggerReload: () => void;
}

const MarketplaceContext = createContext<MarketplaceState | undefined>(undefined);

export function MarketplaceProvider({ children }: { children: React.ReactNode }) {
  const [userAuthenticated, setUserAuthenticated] = useState<boolean>(false);
  const [user, setUser] = useState<MarketplaceUser | null>(null);
  const [publishAccess, setPublishAccess] = useState<boolean>(false);
  const [count, setCount] = useState<number>(0);

  const triggerReload = () => {
    setCount((prev) => prev + 1);
  };

  useEffect(() => {
    const check = async () => {
      try {
        await marketplaceCheckLoggedIn();
        setUserAuthenticated(true);
        try {
          const marketplaceUser = await getMarketplaceUser();
          setUser(marketplaceUser);
          setPublishAccess(['publisher', 'admin'].includes(marketplaceUser.role));
          setUserAuthenticated(true);
        } catch (e) {
          console.log(e);
        }
      } catch {
        console.log('user not logged in to marketplace');
      }
    };
    void check();
  }, [count]);

  return (
    <MarketplaceContext.Provider
      value={{
        userAuthenticated,
        user,
        publishAccess,
        triggerReload,
      }}
    >
      {children}
    </MarketplaceContext.Provider>
  );
}

export function useMarketplace() {
  const context = useContext(MarketplaceContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
