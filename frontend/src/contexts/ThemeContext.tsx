/*
 * Copyright (c) 2026 LeastAction Labs, Inc.
 * This file is part of LeastAction and is licensed under the
 * LeastAction Sustainable Use License (see LICENSE.md) or, for files
 * marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
 * Use of this file outside those terms is not permitted.
 */
import type { ReactNode } from 'react';
import React, { createContext, useContext, useEffect, useState } from 'react';

type Theme = 'black' | 'white';

interface ThemeContextType {
  theme: Theme;
  setTheme: (theme: Theme) => void;
}

const ThemeContext = createContext<ThemeContextType | undefined>(undefined);

export const useTheme = () => {
  const context = useContext(ThemeContext);
  if (!context) {
    throw new Error('useTheme must be used within a ThemeProvider');
  }
  return context;
};

interface ThemeProviderProps {
  children: ReactNode;
}

export const ThemeProvider: React.FC<ThemeProviderProps> = ({ children }) => {
  const [theme, setThemeState] = useState<Theme>(() => {
    // Get theme from localStorage or default to black
    const savedTheme = localStorage.getItem('app-theme') as Theme;
    // Validate that saved theme is either "black" or "white"
    return savedTheme === 'black' || savedTheme === 'white' ? savedTheme : 'black';
  });

  useEffect(() => {
    // Apply theme to html element
    const html = document.documentElement;

    // Remove all theme classes
    html.classList.remove('theme-black', 'theme-white');

    // Add current theme class
    html.classList.add(`theme-${theme}`);

    // Save to localStorage
    localStorage.setItem('app-theme', theme);
  }, [theme]);

  const setTheme = (newTheme: Theme) => {
    setThemeState(newTheme);
  };

  return <ThemeContext.Provider value={{ theme, setTheme }}>{children}</ThemeContext.Provider>;
};
