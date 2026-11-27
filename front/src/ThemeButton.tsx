import { Moon, Sun } from 'lucide-react'

export type Theme = 'dark' | 'light'

export interface ThemeControl {
  theme: Theme
  onTheme: () => void
}

export function ThemeButton({ theme, onTheme }: ThemeControl) {
  const dark = theme === 'dark'
  const Icon = dark ? Sun : Moon

  return <button className="theme-button" type="button" onClick={onTheme}>
    <Icon size={15} /> {dark ? 'Светлая тема' : 'Тёмная тема'}
  </button>
}
