export const SHAPE_INTERVAL_MS = 900
export const THINKING_MS = 6 * SHAPE_INTERVAL_MS

const segmenter = new Intl.Segmenter('ru', { granularity: 'grapheme' })

export interface ReplyPresentation {
  messageId: string
  startedAt: number
  thinkUntil: number
  endAt: number
}

export function graphemes(text: string): string[] {
  return Array.from(segmenter.segment(text), ({ segment }) => segment)
}

export function createReplyPresentation(messageId: string, text: string): ReplyPresentation {
  const startedAt = performance.now()
  const thinkUntil = startedAt + THINKING_MS
  const typingMs = Math.max(850, Math.min(graphemes(text).length * 15, 4400))
  return { messageId, startedAt, thinkUntil, endAt: thinkUntil + typingMs }
}
