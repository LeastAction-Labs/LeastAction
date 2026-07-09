/*
 * Copyright (c) 2026 LeastAction Labs, Inc.
 * This file is part of LeastAction and is licensed under the
 * LeastAction Sustainable Use License (see LICENSE.md) or, for files
 * marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
 * Use of this file outside those terms is not permitted.
 */
import type { ReactNode } from 'react';
import { createContext, useContext, useState } from 'react';

interface ChatDockContextValue {
  reservedRight: number;
  setReservedRight: (width: number) => void;
}

const ChatDockContext = createContext<ChatDockContextValue>({
  reservedRight: 0,
  setReservedRight: () => {},
});

export function ChatDockProvider({ children }: { children: ReactNode }) {
  const [reservedRight, setReservedRight] = useState(0);
  return (
    <ChatDockContext.Provider value={{ reservedRight, setReservedRight }}>
      {children}
    </ChatDockContext.Provider>
  );
}

export const useChatDock = () => useContext(ChatDockContext);
