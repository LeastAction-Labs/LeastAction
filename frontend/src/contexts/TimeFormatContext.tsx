/*
 * Copyright (c) 2026 LeastAction Labs, Inc.
 * This file is part of LeastAction and is licensed under the
 * LeastAction Sustainable Use License (see LICENSE.md) or, for files
 * marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
 * Use of this file outside those terms is not permitted.
 */
import type { ReactNode } from 'react';
import React, { createContext, useContext, useState } from 'react';

import type { TimeZoneMode } from '@/utils/timeFormat';

interface TimeFormatContextType {
  timeZone: TimeZoneMode;
  toggleTimeZone: () => void;
}

const TimeFormatContext = createContext<TimeFormatContextType | undefined>(undefined);

export const useTimeFormat = () => {
  const context = useContext(TimeFormatContext);
  if (!context) {
    throw new Error('useTimeFormat must be used within a TimeFormatProvider');
  }
  return context;
};

export const TimeFormatProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [timeZone, setTimeZone] = useState<TimeZoneMode>(() => {
    const saved = localStorage.getItem('app-timezone') as TimeZoneMode;
    return saved === 'local' ? 'local' : 'utc';
  });

  const toggleTimeZone = () => {
    const next = timeZone === 'utc' ? 'local' : 'utc';
    localStorage.setItem('app-timezone', next);
    setTimeZone(next);
  };

  return (
    <TimeFormatContext.Provider value={{ timeZone, toggleTimeZone }}>
      {children}
    </TimeFormatContext.Provider>
  );
};
