import { Eye, EyeOff, LoaderCircle } from 'lucide-react'
import { useState, type FormEvent } from 'react'
import { signIn, type Session } from './auth'
import { ThemeButton, type ThemeControl } from './ThemeButton'
import introVideo from './assets/intro.mp4'

export function Brand() {
  return (
    <span className="brand">MathContext.</span>
  )
}

export function AuthScreen({ onLogin, theme, onTheme }: { onLogin: (session: Session) => void } & ThemeControl) {
  const [mode, setMode] = useState<'login' | 'register'>('login')
  const [visible, setVisible] = useState(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const registering = mode === 'register'

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (busy) return
    const fields = new FormData(event.currentTarget)
    const username = String(fields.get('username')).trim()
    const password = String(fields.get('password'))
    if (username.length < 4) {
      setError('Введите логин от 4 до 20 символов.')
      return
    }
    if (registering && password !== fields.get('confirmation')) {
      setError('Пароли не совпадают.')
      return
    }
    setError('')
    setBusy(true)
    try {
      onLogin(await signIn(mode, { username, password }))
    } catch (issue) {
      setError(issue instanceof Error ? issue.message : 'Не удалось войти.')
    } finally {
      setBusy(false)
    }
  }

  return (
    <main className="auth-layout">
      <header className="auth-header">
        <Brand />
        <ThemeButton theme={theme} onTheme={onTheme} />
      </header>
      <div className="auth-columns">
        <section className="auth-content" aria-labelledby="auth-title">
        <div className="auth-form-wrap">
          <h1 id="auth-title">{registering ? 'Создать аккаунт' : 'Вход в аккаунт'}</h1>
          <p className="muted auth-description">
            {registering ? 'Создайте профиль, чтобы открыть чат и учебники.' : 'Войдите, чтобы продолжить работу с лекциями.'}
          </p>
          <form className="auth-form glass" onSubmit={submit}>
            <label className="field">
              <span>Логин</span>
              <input name="username" autoComplete="username" placeholder="Ваш логин" minLength={4} maxLength={20} required />
            </label>
            <div className="field">
              <label htmlFor="account-password">Пароль</label>
              <div className="password-field">
                <input id="account-password" name="password" type={visible ? 'text' : 'password'} autoComplete={registering ? 'new-password' : 'current-password'} placeholder="Ваш пароль" minLength={5} maxLength={30} required />
                <button type="button" className="icon-button" aria-label={visible ? 'Скрыть пароль' : 'Показать пароль'} onClick={() => setVisible(!visible)}>
                  {visible ? <EyeOff size={18} /> : <Eye size={18} />}
                </button>
              </div>
            </div>
            {registering && (
              <label className="field">
                <span>Повторите пароль</span>
                <input name="confirmation" type="password" autoComplete="new-password" placeholder="Повторите пароль" minLength={5} maxLength={30} required />
              </label>
            )}
            {error && <p className="form-error" role="alert">{error}</p>}
            <button className="primary auth-submit" disabled={busy}>
              {busy && <LoaderCircle className="spin" size={17} />}
              {registering ? 'Создать аккаунт' : 'Войти'}
            </button>
          </form>
          <p className="auth-toggle muted">
            {registering ? 'Уже есть аккаунт?' : 'Ещё нет аккаунта?'}
            <button type="button" className="text-button" disabled={busy} onClick={() => {
              setError('')
              setMode(registering ? 'login' : 'register')
            }}>{registering ? 'Войти' : 'Создать аккаунт'}</button>
          </p>
        </div>
        </section>
        <section className="auth-preview" aria-labelledby="preview-title">
          <div className="auth-video glass">
            <video src={introVideo} controls autoPlay muted playsInline aria-label="Как работает MathContext" />
          </div>
          <h2 id="preview-title">Как работает MathContext</h2>
          <p>Короткое видео о поиске по учебникам.</p>
        </section>
      </div>
    </main>
  )
}
