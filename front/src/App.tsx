import { LoaderCircle } from 'lucide-react'
import { useEffect, useState } from 'react'
import { AuthScreen } from './AuthScreen'
import { readSession, signOut, type Session } from './auth'
import { Workspace } from './Workspace'
import type { Theme } from './ThemeButton'

export function App() {
  const [session, setSession] = useState<Session | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [attempt, setAttempt] = useState(0)
  const [theme, setTheme] = useState<Theme>(() => {
    try {
      return localStorage.getItem('mathcontext.theme') === 'light' ? 'light' : 'dark'
    } catch {
      return 'dark'
    }
  })

  useEffect(() => {
    document.documentElement.dataset.theme = theme
    try { localStorage.setItem('mathcontext.theme', theme) } catch { /* Theme stays active for this visit. */ }
  }, [theme])

  const themeControl = { theme, onTheme: () => setTheme(theme === 'dark' ? 'light' : 'dark') }

  useEffect(() => {
    let active = true
    readSession()
      .then((result) => { if (active) setSession(result) })
      .catch((issue: Error) => { if (active) setError(issue.message) })
      .finally(() => { if (active) setLoading(false) })
    return () => { active = false }
  }, [attempt])

  if (loading) {
    return <main className="center-status" role="status"><LoaderCircle className="spin" /> Проверяем сессию</main>
  }

  if (error) {
    return (
      <main className="center-status" role="alert">
        <p>{error}</p>
        <button className="primary" onClick={() => { setError(''); setLoading(true); setAttempt(attempt + 1) }}>Повторить</button>
      </main>
    )
  }

  if (!session) return <AuthScreen onLogin={setSession} {...themeControl} />

  return <Workspace key={session.user_id} session={session} {...themeControl} onLogout={async () => {
    await signOut()
    setSession(null)
  }} />
}
