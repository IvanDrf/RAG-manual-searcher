import { ArrowUp, BookOpen, Copy, ImagePlus, X } from 'lucide-react'
import { useEffect, useLayoutEffect, useMemo, useRef, useState, type FormEvent } from 'react'
import { MessagePhoto } from './ChatPhotos'
import type { ChatPhoto } from './photoStore'
import { MAX_QUESTION_LENGTH } from './chatApi'
import { graphemes, type ReplyPresentation } from './replyPresentation'
import { ThinkingAnimation } from './ThinkingAnimation'

export interface Quote {
  text: string
  lecture: string
  page: number
}

interface Message {
  id: string
  role: 'user' | 'assistant'
  text: string
  quote?: Quote
  photo?: ChatPhoto
}

export interface Chat {
  id: string
  title: string
  serverId?: string
  messages: Message[]
}

function ReplyCursor() {
  return <span className="reply-cursor" aria-hidden="true"><i /><i /><i /></span>
}

function WrittenText({ letters, count }: { letters: string[]; count: number }) {
  const tail = Math.max(0, count - 6)
  return <>
    {letters.slice(0, tail).join('')}
    {letters.slice(tail, count).map((letter, index) => <span className="reply-ink" key={tail + index}>{letter}</span>)}
    <ReplyCursor />
  </>
}

function QuoteCard({ quote, onRemove }: { quote: Quote; onRemove?: () => void }) {
  return (
    <blockquote className="quote-card">
      <div><BookOpen size={16} /><strong>{quote.lecture} · с. {quote.page}</strong>
        {onRemove && <button className="icon-button" type="button" aria-label="Убрать цитату" onClick={onRemove}><X size={17} /></button>}
      </div>
      <p>{quote.text}</p>
    </blockquote>
  )
}

interface ChatPanelProps {
  userId: string
  chat?: Chat
  presentation?: ReplyPresentation
  draft: string
  quote: Quote | null
  pendingSince?: number
  saving: boolean
  sendError: string
  onDraft: (value: string) => void
  onClearQuote: () => void
  onSend: (value: string) => void
  onLibrary: () => void
}

function usePlaybackTime(presentation?: ReplyPresentation) {
  const [time, setTime] = useState(() => performance.now())

  useEffect(() => {
    if (!presentation) return
    const { thinkUntil, endAt } = presentation
    let frame = 0
    let timer = 0

    function tick(now: number) {
      setTime(now)
      if (now < thinkUntil) {
        timer = window.setTimeout(() => { frame = requestAnimationFrame(tick) }, thinkUntil - now)
      } else if (now < endAt) {
        frame = requestAnimationFrame(tick)
      }
    }
    frame = requestAnimationFrame(tick)
    return () => {
      window.clearTimeout(timer)
      cancelAnimationFrame(frame)
    }
  }, [presentation])

  return time
}

export function ChatPanel({
  userId, chat, presentation, draft, quote, saving, sendError, pendingSince,
  onDraft, onClearQuote, onSend, onLibrary,
}: ChatPanelProps) {
  const timeline = useRef<HTMLDivElement>(null)
  const followLatest = useRef(true)
  const textarea = useRef<HTMLTextAreaElement>(null)
  const messages = chat?.messages
  const empty = !messages?.length
  const [copied, setCopied] = useState<{ id: string; ok: boolean }>()
  const time = usePlaybackTime(presentation)
  const activeText = messages?.find((item) => item.id === presentation?.messageId)?.text ?? ''
  const writing = useMemo(() => graphemes(activeText), [activeText])
  const thinking = presentation && time < presentation.thinkUntil
  const typing = presentation && !thinking && time < presentation.endAt
  const count = typing
    ? Math.floor(writing.length * (time - presentation.thinkUntil) / (presentation.endAt - presentation.thinkUntil))
    : writing.length

  useLayoutEffect(() => {
    followLatest.current = true
  }, [messages])

  useLayoutEffect(() => {
    if (followLatest.current && timeline.current) timeline.current.scrollTop = timeline.current.scrollHeight
  }, [messages, thinking, typing, count, pendingSince])

  useEffect(() => { if (quote) textarea.current?.focus() }, [quote])

  const canSend = !presentation && !saving && (!!draft.trim() || !!quote)

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (canSend) onSend(draft)
  }

  return (
    <section className="chat-stage" aria-label="Чат по математике">
      <div className="chat-smoke" aria-hidden="true"><span /><span /><span /><span /></div>
      <div className={'chat-panel' + (empty ? ' chat-panel-empty' : '')}>
          {empty && (
            <div className="chat-empty">
              <span className="chat-symbol" aria-hidden="true">m.</span>
              <h1>В чём хотите разобраться?</h1>
              <p>Задайте вопрос по математическим учебникам.</p>
            </div>
          )}
          {!empty && <div className="chat-timeline" ref={timeline} onScroll={({ currentTarget }) => {
            followLatest.current = currentTarget.scrollHeight - currentTarget.scrollTop - currentTarget.clientHeight < 75
          }}>
            <div className="messages" role="log" aria-label="Сообщения чата">
              {messages.map((message) => {
                const active = presentation?.messageId === message.id
                if (active && thinking) {
                  return <ThinkingAnimation key={message.id} startedAt={presentation.startedAt} />
                }
                const partial = active && typing
                return (
                  <article className={'message message-' + message.role} key={message.id} data-reply-phase={partial ? 'typing' : undefined}>
                  {message.role === 'assistant' && <header><span className="reply-mark">m.</span> MathContext</header>}
                  {message.quote && <QuoteCard quote={message.quote} />}
                  {message.photo && <MessagePhoto photo={message.photo} userId={userId} />}
                  {(partial || message.text) && <p aria-hidden={partial || undefined}>{partial ? <WrittenText letters={writing} count={count} /> : message.text}</p>}
                  {message.role === 'assistant' && !partial && <button className="copy-reply text-button" onClick={async () => {
                    try {
                      await navigator.clipboard.writeText(message.text)
                      setCopied({ id: message.id, ok: true })
                    } catch {
                      setCopied({ id: message.id, ok: false })
                    }
                  }}><Copy size={15} /> {copied?.id === message.id ? (copied.ok ? 'Скопировано' : 'Не удалось скопировать') : 'Копировать'}</button>}
                  </article>
                )
              })}
              {pendingSince !== undefined && <ThinkingAnimation startedAt={pendingSince} />}
            </div>
          </div>}
        <div className="composer-area">
          <form className="composer" onSubmit={submit}>
            {quote && <QuoteCard quote={quote} onRemove={saving ? undefined : onClearQuote} />}
            <div className="composer-line">
              <textarea ref={textarea} rows={3} value={draft} maxLength={MAX_QUESTION_LENGTH} readOnly={saving} onChange={(event) => onDraft(event.target.value)} placeholder={quote ? 'Добавьте вопрос к цитате…' : 'Напишите вопрос…'} aria-label="Вопрос для чата"
                onKeyDown={(event) => {
                  if (event.key === 'Enter' && !event.shiftKey && !event.nativeEvent.isComposing) {
                    event.preventDefault()
                    if (canSend) onSend(draft)
                  }
                }} />
            </div>
            {sendError && <p className="form-error composer-error" role="alert">{sendError}</p>}
            <div className="composer-actions">
              <div className="composer-tools">
                <button className="text-button library-shortcut" type="button" onClick={onLibrary}><BookOpen size={16} /> Все учебники</button>
                <button className="icon-button attachment-button" type="button" aria-label="Анализ фото пока недоступен" title="Анализ фото пока недоступен. Отправьте текст вопроса." disabled>
                  <ImagePlus size={19} />
                </button>
              </div>
              <button className="send-button icon-button" type="submit" disabled={!canSend} aria-label="Отправить вопрос"><ArrowUp size={20} /></button>
            </div>
          </form>
          <p className="composer-hint">Enter — отправить · Shift + Enter — новая строка</p>
          <p className="composer-hint">{saving ? 'Ожидаем ответ сервера…' : `До ${MAX_QUESTION_LENGTH} символов вместе с цитатой`}</p>
        </div>
      </div>
    </section>
  )
}
