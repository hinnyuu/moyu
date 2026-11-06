export type ThemePref = "system" | "light" | "dark";
export type ResolvedTheme = "light" | "dark";

export const THEME_KEY = "moyu-theme";

export function loadPref(): ThemePref {
  try {
    const value = localStorage.getItem(THEME_KEY);
    if (value === "light" || value === "dark" || value === "system") return value;
  } catch {
    /* storage unavailable */
  }
  return "system";
}

export function systemPrefersDark(): boolean {
  return window.matchMedia("(prefers-color-scheme: dark)").matches;
}

export function resolveTheme(pref: ThemePref): ResolvedTheme {
  if (pref === "system") return systemPrefersDark() ? "dark" : "light";
  return pref;
}

export function applyTheme(pref: ThemePref): ResolvedTheme {
  const resolved = resolveTheme(pref);
  document.documentElement.dataset.theme = resolved;
  document.documentElement.dataset.themePref = pref;
  try {
    localStorage.setItem(THEME_KEY, pref);
  } catch {
    /* storage unavailable */
  }
  return resolved;
}

export function nextPref(pref: ThemePref): ThemePref {
  if (pref === "system") return "light";
  if (pref === "light") return "dark";
  return "system";
}

export function themeLabel(pref: ThemePref): string {
  if (pref === "system") return "跟随系统";
  if (pref === "light") return "亮色";
  return "暗色";
}