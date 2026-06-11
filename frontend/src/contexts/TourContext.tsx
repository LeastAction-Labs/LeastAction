/*
 * Copyright (c) 2026 LeastAction Labs, Inc.
 * This file is part of LeastAction and is licensed under the
 * LeastAction Sustainable Use License (see LICENSE.md) or, for files
 * marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
 * Use of this file outside those terms is not permitted.
 */
import React, { createContext, useContext, useEffect, useState } from 'react';

import type { TourConfig } from '@/config/tours';
import { TOURS } from '@/config/tours';

import { useAuth } from './AuthContext';

interface TourContextType {
  activeTour: TourConfig | null;
  currentStepIndex: number;
  isNavigating: boolean;
  showLanding: boolean;
  startTour: (tourId: string) => void;
  endTour: () => void;
  setCurrentStepIndex: (i: number) => void;
  setIsNavigating: (v: boolean) => void;
  openLanding: () => void;
  closeLanding: () => void;
}

const TourContext = createContext<TourContextType | null>(null);

export function TourProvider({ children }: { children: React.ReactNode }) {
  const [activeTour, setActiveTour] = useState<TourConfig | null>(null);
  const [currentStepIndex, setCurrentStepIndex] = useState(0);
  const [isNavigating, setIsNavigating] = useState(false);
  const [showLanding, setShowLanding] = useState(false);
  const { authState } = useAuth();

  useEffect(() => {
    if (!authState.isAuthenticated) return;
    setShowLanding(true);
  }, [authState.isAuthenticated]);

  const openLanding = () => setShowLanding(true);
  const closeLanding = () => setShowLanding(false);

  const startTour = (tourId: string) => {
    const tour = TOURS[tourId];
    if (!tour) return;
    setActiveTour(tour);
    setCurrentStepIndex(0);
    setIsNavigating(false);
    setShowLanding(false);
  };

  const endTour = () => {
    setActiveTour(null);
    setCurrentStepIndex(0);
    setIsNavigating(false);
  };

  return (
    <TourContext.Provider
      value={{
        activeTour,
        currentStepIndex,
        isNavigating,
        showLanding,
        startTour,
        endTour,
        setCurrentStepIndex,
        setIsNavigating,
        openLanding,
        closeLanding,
      }}
    >
      {children}
    </TourContext.Provider>
  );
}

export function useTour(): TourContextType {
  const ctx = useContext(TourContext);
  if (!ctx) throw new Error('useTour must be used within TourProvider');
  return ctx;
}
