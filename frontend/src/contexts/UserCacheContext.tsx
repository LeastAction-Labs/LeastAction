/*
 * Copyright (c) 2026 LeastAction Labs, Inc.
 * This file is part of LeastAction and is licensed under the
 * LeastAction Sustainable Use License (see LICENSE.md) or, for files
 * marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
 * Use of this file outside those terms is not permitted.
 */
import type { ReactNode } from 'react';
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
} from 'react';

import { searchUsers } from '@/services/user.service';

export interface CachedUser {
  laui: string;
  username?: string;
  email?: string;
  isLoading?: boolean;
  [key: string]: any;
}

interface UserCacheContextType {
  userCache: Record<string, CachedUser>;
  fetchMissingUsers: (lauis: string[]) => void;
}

const UserCacheContext = createContext<UserCacheContextType | undefined>(undefined);

export const UserCacheProvider = ({ children }: { children: ReactNode }) => {
  const [userCache, setUserCache] = useState<Record<string, CachedUser>>({});
  // Use a ref to track in-flight requests so we don't fetch the same user twice
  const fetchingQueue = useRef<Set<string>>(new Set());

  const fetchMissingUsers = useCallback(
    async (lauis: string[]) => {
      // 1. Identify which LAUIs are not in cache and not currently fetching
      const missing = lauis.filter((laui) => !userCache[laui] && !fetchingQueue.current.has(laui));

      if (missing.length === 0) return;

      // 2. Mark them as fetching
      missing.forEach((laui) => fetchingQueue.current.add(laui));

      try {
        // 3. Fetch ONLY the missing ones
        const response = (
          await searchUsers({
            user_lauis: missing,
            page: 1,
            per_page: missing.length,
          })
        ).users;

        setUserCache((prev) => {
          const next = { ...prev };

          // Map successful responses
          response.forEach((u: any) => {
            const key = u.laui || u.id;
            if (key) {
              next[key] = {
                laui: key,
                username: u.username || 'Unknown User',
                email: u.email || 'N/A',
                ...u,
              };
            }
          });

          // 4. Mark unreturned users as 'Unknown' to avoid infinite retry loops
          missing.forEach((laui) => {
            if (!next[laui]) {
              next[laui] = { laui, username: 'Unknown User', email: 'N/A' };
            }
          });

          return next;
        });
      } catch (err) {
        console.error('Failed to fetch users for cache:', err);
        // Only clear from the queue on failure so they can be retried
        missing.forEach((laui) => fetchingQueue.current.delete(laui));
      }
    },
    [userCache],
  );

  return (
    <UserCacheContext.Provider
      value={{ userCache, fetchMissingUsers: (lauis) => void fetchMissingUsers(lauis) }}
    >
      {children}
    </UserCacheContext.Provider>
  );
};

// Hook 1: Get the raw cache (useful for filtering large lists of users)
export const useUserCache = () => {
  const context = useContext(UserCacheContext);
  if (!context) throw new Error('useUserCache must be used within UserCacheProvider');
  return context;
};

// Hook 2: Fetch and return users IN THE EXACT ORDER of the provided array
export const useUsers = (lauis: string[]): CachedUser[] => {
  const { userCache, fetchMissingUsers } = useUserCache();

  // Trigger fetch for any missing users when the requested array changes
  useEffect(() => {
    if (lauis && lauis.length > 0) {
      fetchMissingUsers(lauis);
    }
  }, [lauis, fetchMissingUsers]);

  // Return the mapped array. If missing, return an object with isLoading: true
  return useMemo(() => {
    return (lauis || []).map((laui) => userCache[laui] || { laui, isLoading: true });
  }, [lauis, userCache]);
};
