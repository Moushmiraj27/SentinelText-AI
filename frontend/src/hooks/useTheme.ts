import { useCallback, useEffect, useState } from 'react';

export type ThemeMode = 'light' | 'dark';
const STORAGE_KEY = 'sentinel-theme';

export function useTheme() {
  const [theme, setTheme] = useState<ThemeMode>(() => localStorage.getItem(STORAGE_KEY) === 'dark' ? 'dark' : 'light');

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    localStorage.setItem(STORAGE_KEY, theme);
  }, [theme]);

  const toggleTheme = useCallback(() => {
    setTheme(current => current === 'light' ? 'dark' : 'light');
  }, []);

  return { theme, setTheme, toggleTheme };
}
