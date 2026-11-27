import { readSession } from './auth'

export const MAX_QUESTION_LENGTH = 100

export interface ChatAnswer {
  chat_id: string
  model: string
  response: string
}

export interface QuestionQuote {
  text: string
  lecture: string
  page: number
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null
}

export function questionText(message: string, quote: QuestionQuote | null = null): string {
  const text = message.trim()
  const question = quote ? [text, `Цитата из «${quote.lecture}», с. ${quote.page}: ${quote.text}`].filter(Boolean).join('\n\n') : text
  if (!question) throw new Error('Введите вопрос.')
  if (Array.from(question).length > MAX_QUESTION_LENGTH) {
    throw new Error(`Вопрос вместе с цитатой должен содержать не больше ${MAX_QUESTION_LENGTH} символов.`)
  }
  return question
}

export async function sendQuestion(message: string, userId: string, chatId?: string): Promise<ChatAnswer> {
  const question = questionText(message)
  const session = await readSession()
  if (!session || session.user_id !== userId) {
    throw new Error('Сессия завершилась или аккаунт изменился. Войдите заново.')
  }

  const query = chatId ? `?chat_id=${encodeURIComponent(chatId)}` : ''
  let response: Response
  try {
    response = await fetch(`/api/v1/chat/promt${query}`, {
      method: 'POST',
      credentials: 'same-origin',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message: question }),
    })
  } catch {
    throw new Error('Не удалось получить ответ от сервера. Проверьте подключение. Перед повторной отправкой проверьте историю: сервер мог сохранить сообщение.')
  }

  const payload: unknown = await response.json().catch(() => null)
  if (!response.ok) {
    const detail = isRecord(payload) && typeof payload.detail === 'string' ? payload.detail : ''
    const message = response.status === 429 ? 'Достигнут лимит вопросов. Попробуйте позже.' :
      response.status === 422 ? `Проверьте вопрос: допустимо от 1 до ${MAX_QUESTION_LENGTH} символов.` :
      response.status >= 500 ? 'Ошибка сервера при обработке вопроса. Попробуйте позже.' :
      detail || 'Не удалось отправить вопрос.'
    throw new Error(message)
  }
  if (!isRecord(payload) || typeof payload.chat_id !== 'string' || typeof payload.model !== 'string' ||
      typeof payload.response !== 'string' || !payload.chat_id || !payload.response.trim() ||
      (chatId !== undefined && payload.chat_id !== chatId)) {
    throw new Error('Сервер вернул некорректный ответ. Проверьте историю перед повторной отправкой.')
  }
  return { chat_id: payload.chat_id, model: payload.model, response: payload.response }
}
