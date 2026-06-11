/*
 * Copyright (c) 2026 LeastAction Labs, Inc.
 * This file is part of LeastAction and is licensed under the
 * LeastAction Sustainable Use License (see LICENSE.md) or, for files
 * marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
 * Use of this file outside those terms is not permitted.
 */
import type { ReactNode } from 'react';
import React, { createContext, useContext, useState } from 'react';

import type { CatalogItem } from '@/components/browse';

export interface OperatorData {
  codeblock: object;
  bashblock: object;
  prompt: string;
  install_docs: object;
  guide_docs: object;
}

export interface LinkModalDataType {
  isOpen: boolean;
  childItem: CatalogItem;
  availableItems?: CatalogItem[];
  itemTypeFilter?: string;
  supportedParentTypes?: string[];
}

interface LinkModalContextType {
  linkModalData: LinkModalDataType | null;
  setLinkModalData: (data: LinkModalDataType | null) => void;
}

const LinkModalContext = createContext<LinkModalContextType | undefined>(undefined);

export const LinkModalProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [linkModalData, setLinkModalData] = useState<LinkModalDataType | null>(null);
  return (
    <LinkModalContext.Provider
      value={{
        linkModalData,
        setLinkModalData,
      }}
    >
      {children}
    </LinkModalContext.Provider>
  );
};

export const useLinkModalContext = (): LinkModalContextType => {
  const context = useContext(LinkModalContext);
  if (!context) {
    throw new Error('useLinkModalContext must be used within a LinkModalProvider');
  }
  return context;
};
