export interface Session {
  user_id: string
  user_role: 'user' | 'admin'
}

export interface Credentials {
  username: string
  password: string
}

class AuthError extends Error {
  constructor(readonly status: number, message: string) {
    super(message)
  }
}

async function authRequest<T>(action: string, credentials?: Credentials): Promise<T> {
  let response: Response
  try {
    response = await fetch('/api/v1/auth/' + action, {
      method: action === 'me' ? 'GET' : 'POST',
      credentials: 'same-origin',
      headers: credentials ? { 'Content-Type': 'application/json' } : undefined,
      body: credentials ? JSON.stringify(credentials) : undefined,
    })
  } catch {
    throw new Error('Сервис авторизации недоступен. Проверьте подключение и попробуйте ещё раз.')
  }

  if (!response.ok) {
    const payload = await response.json().catch(() => null)
    const message =
      response.status >= 500 ? 'Сервис авторизации недоступен. Попробуйте ещё раз.' :
      response.status === 429 ? 'Слишком много попыток. Попробуйте через минуту.' :
      response.status === 422 ? 'Проверьте длину логина и пароля.' :
      typeof payload?.detail === 'string' ? payload.detail :
      'Не удалось выполнить запрос.'
    throw new AuthError(response.status, message)
  }

  if (response.status === 204) return undefined as T
  return response.json() as Promise<T>
}

function isExpiredSession(error: unknown): boolean {
  return error instanceof AuthError && [400, 401, 403, 404, 422].includes(error.status)
}

export async function readSession(): Promise<Session | null> {
  try {
    return await authRequest<Session>('me')
  } catch (error) {
    if (!isExpiredSession(error)) throw error
  }

  try {
    await authRequest<void>('refresh')
    return await authRequest<Session>('me')
  } catch (error) {
    if (isExpiredSession(error)) return null
    throw error
  }
}

export async function signIn(mode: 'login' | 'register', credentials: Credentials) {
  await authRequest<void>(mode, credentials)
  const session = await readSession()
  if (!session) throw new Error('Не удалось открыть сессию. Откройте приложение через localhost или HTTPS.')
  return session
}

export function signOut() {
  return authRequest<void>('logout')
}
