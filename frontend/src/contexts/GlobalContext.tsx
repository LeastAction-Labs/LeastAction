/*
 * Copyright (c) 2026 LeastAction Labs, Inc.
 * This file is part of LeastAction and is licensed under the
 * LeastAction Sustainable Use License (see LICENSE.md) or, for files
 * marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
 * Use of this file outside those terms is not permitted.
 */
import type { ReactNode } from 'react';
import { createContext, useCallback, useContext, useState } from 'react';

import type { FolderSidebarStateData } from '@/components/browse/FolderSidebar/FolderSidebar';

export enum CatalogType {
  'MARKETPLACE' = 'marketplace',
  'BROWSE' = 'browse',
}

export interface OpenTab {
  laui: string;
  name: string;
  item_type: string;
  source: 'browse' | 'marketplace';
}

const OPEN_TABS_KEY = 'la_open_tabs';
const CURRENT_PROJECT_KEY = 'la_current_project_laui';
const MAX_TABS = 15;

function loadCurrentProjectFromStorage(): string | null {
  return localStorage.getItem(CURRENT_PROJECT_KEY) ?? null;
}

function loadTabsFromStorage(): OpenTab[] {
  try {
    const raw = localStorage.getItem(OPEN_TABS_KEY);
    return raw ? JSON.parse(raw) : [];
  } catch {
    return [];
  }
}

function saveTabsToStorage(tabs: OpenTab[]) {
  localStorage.setItem(OPEN_TABS_KEY, JSON.stringify(tabs));
}

interface GlobalContextType {
  accountLaui: string | null;
  trashLaui: string | null;
  projectLauis: string[];
  currentProjectLaui: string | null;
  catalogType: CatalogType;
  folderSidebarState: FolderSidebarStateData;
  openTabs: OpenTab[];
  setAccountLaui: (laui: string | null) => void;
  setTrashLaui: (laui: string | null) => void;
  setProjectLauis: (lauis: string[]) => void;
  setCurrentProjectLaui: (laui: string | null) => void;
  setCatalogType: (catalogType: CatalogType) => void;
  setFolderSidebarState: (state: FolderSidebarStateData) => void;
  addTab: (tab: OpenTab) => void;
  removeTab: (laui: string) => void;
  clearTabs: () => void;
}

export const GlobalContext = createContext<GlobalContextType | undefined>(undefined);

export const GlobalProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [accountLaui, setAccountLaui] = useState<string | null>(null);
  const [trashLaui, setTrashLaui] = useState<string | null>(null);
  const [projectLauis, setProjectLauis] = useState<string[]>([]);
  const [currentProjectLaui, setCurrentProjectLaui_] = useState<string | null>(
    loadCurrentProjectFromStorage,
  );

  const setCurrentProjectLaui = useCallback((laui: string | null) => {
    if (laui) localStorage.setItem(CURRENT_PROJECT_KEY, laui);
    else localStorage.removeItem(CURRENT_PROJECT_KEY);
    setCurrentProjectLaui_(laui);
  }, []);
  const [catalogType, setCatalogType] = useState<CatalogType>(CatalogType.BROWSE);
  const [folderSidebarState, setFolderSidebarState] = useState<FolderSidebarStateData>({
    isCollapsed: false,
    width: 280,
    isResizing: false,
  });
  const [openTabs, setOpenTabs] = useState<OpenTab[]>(loadTabsFromStorage);

  const addTab = useCallback((tab: OpenTab) => {
    setOpenTabs((prev) => {
      // If already open, update in place (name/type may have changed)
      if (prev.some((t) => t.laui === tab.laui)) {
        const next = prev.map((t) => (t.laui === tab.laui ? tab : t));
        saveTabsToStorage(next);
        return next;
      }
      // Append at end, drop oldest (leftmost) if over cap
      const next = prev.length >= MAX_TABS ? [...prev.slice(1), tab] : [...prev, tab];
      saveTabsToStorage(next);
      return next;
    });
  }, []);

  const removeTab = useCallback((laui: string) => {
    setOpenTabs((prev) => {
      const next = prev.filter((t) => t.laui !== laui);
      saveTabsToStorage(next);
      return next;
    });
  }, []);

  const clearTabs = useCallback(() => {
    saveTabsToStorage([]);
    setOpenTabs([]);
  }, []);

  return (
    <GlobalContext.Provider
      value={{
        accountLaui,
        trashLaui,
        projectLauis,
        currentProjectLaui,
        catalogType,
        folderSidebarState,
        openTabs,
        setAccountLaui,
        setTrashLaui,
        setProjectLauis,
        setCurrentProjectLaui,
        setCatalogType,
        setFolderSidebarState,
        addTab,
        removeTab,
        clearTabs,
      }}
    >
      {children}
    </GlobalContext.Provider>
  );
};

export const useGlobal = (): GlobalContextType => {
  const global = useContext(GlobalContext);
  if (!global) {
    throw new Error('useGlobal must be used within global provider');
  }
  return global;
};
