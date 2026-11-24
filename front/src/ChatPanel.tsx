import { ArrowUp, BookOpen, Copy, ImagePlus, X } from 'lucide-react'
import { useEffect, useLayoutEffect, useMemo, useRef, useState, type ClipboardEvent, type FormEvent } from 'react'
import { DraftPhoto, MessagePhoto } from './ChatPhotos'
import { PHOTO_TYPES, photoValidationError, type ChatPhoto } from './photoStore'
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
  messages: Message[]
}

const derivativeIntro = 'Производная показывает, как быстро меняется значение функции в точке. Геометрически это наклон касательной к графику.'
const derivativeFormula = 'Определение: f′(x) = limₕ→₀ [f(x + h) − f(x)] / h.'
const derivativeExample = 'Для f(x) = x² производная равна f′(x) = 2x. В точке x = 3 наклон равен 6.'
const derivativeSections = [derivativeIntro, derivativeFormula, derivativeExample].map(graphemes)

const examples = [
  {
    question: 'Что такое производная?',
    reply: [derivativeIntro, derivativeFormula, derivativeExample].join(' '),
  },
  {
    question: 'Что такое линейная независимость?',
    reply: 'Векторы линейно независимы, если их линейная комбинация равна нулю только при нулевых коэффициентах. Геометрически это значит, что ни один из них нельзя выразить через остальные.',
  },
  {
    question: 'Как работает формула Байеса?',
    reply: 'Формула Байеса обновляет вероятность гипотезы с учётом наблюдения: P(A | B) = P(B | A) · P(A) / P(B), если P(B) > 0.',
  },
  {
    question: 'Что означает определённый интеграл?',
    reply: 'Определённый интеграл описывает накопление величины на отрезке. Для непрерывной неотрицательной функции он равен площади под графиком между границами интегрирования.',
  },
]

export function demoReply(question: string, quote: Quote | null): string {
  if (quote) {
    return 'Фрагмент из «' + quote.lecture + '» (с. ' + quote.page + ') приложен к сообщению. В демо можно проверить передачу цитаты. Анализ фрагмента появится после подключения LLM.'
  }
  const normalized = question.toLowerCase().replace(/[?!.,]+$/u, '').trim()
  const sample = examples.find((example) => example.question.toLowerCase().slice(0, -1) === normalized)
  return sample?.reply ?? 'Сообщение сохранено в чате. В демо можно попробовать вопрос «Что такое производная?» или приложить цитату из лекции.'
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

function DerivativeExample({ count }: { count?: number }) {
  const [intro, formula, example] = derivativeSections
  const typing = count !== undefined
  const shown = count ?? Infinity
  const formulaCount = shown - intro.length - 1
  const exampleCount = formulaCount - formula.length - 1

  return <div className="lesson-example" aria-hidden={typing || undefined}>
    <h2 className="lesson-heading">Производная — скорость изменения</h2>
    <p>{typing && formulaCount < 0 ? <WrittenText letters={intro} count={shown} /> : derivativeIntro}</p>
    {formulaCount >= 0 && (
      formulaCount >= formula.length
        ? <div className="lesson-equation glass" role="math" aria-label="Производная равна пределу при h, стремящемся к нулю, отношения f от x плюс h минус f от x к h">
            <span>f′(x) =</span>
            <span className="equation-limit">lim<small>h → 0</small></span>
            <span className="equation-fraction"><span>f(x + h) − f(x)</span><span>h</span></span>
            {typing && exampleCount < 0 && <ReplyCursor />}
          </div>
        : <p className="lesson-equation glass"><span><WrittenText letters={formula} count={formulaCount} /></span></p>
    )}
    {exampleCount >= 0 && (
      typing
        ? <p><WrittenText letters={example} count={exampleCount} /></p>
        : <p>Для <var>f(x) = x²</var> производная равна <var>f′(x) = 2x</var>. В точке <var>x = 3</var> наклон касательной равен 6.</p>
    )}
  </div>
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
  photo: File | null
  saving: boolean
  sendError: string
  onDraft: (value: string) => void
  onPhoto: (file: File | null) => void
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
  userId, chat, presentation, draft, quote, photo, saving, sendError,
  onDraft, onPhoto, onClearQuote, onSend, onLibrary,
}: ChatPanelProps) {
  const timeline = useRef<HTMLDivElement>(null)
  const followLatest = useRef(true)
  const textarea = useRef<HTMLTextAreaElement>(null)
  const fileInput = useRef<HTMLInputElement>(null)
  const messages = chat?.messages
  const empty = !messages?.length
  const [copied, setCopied] = useState<{ id: string; ok: boolean }>()
  const [photoError, setPhotoError] = useState('')
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
  }, [messages, thinking, typing, count])

  useEffect(() => { if (quote) textarea.current?.focus() }, [quote])
  useEffect(() => { setPhotoError('') }, [chat?.id])

  const canSend = !presentation && !saving && (!!draft.trim() || !!photo)

  function selectPhoto(file: File) {
    const error = photoValidationError(file)
    setPhotoError(error)
    if (!error) onPhoto(file)
  }

  function pastePhoto(event: ClipboardEvent<HTMLTextAreaElement>) {
    if (saving) return

    const { clipboardData } = event
    const file = Array.from(clipboardData.files).find((item) => item.type.startsWith('image/'))
    if (!file) return

    if (!clipboardData.getData('text/plain')) event.preventDefault()
    selectPhoto(file)
  }

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
                  {message.role === 'assistant' && message.text === examples[0].reply
                    ? <DerivativeExample count={partial ? count : undefined} />
                    : (partial || message.text) && <p aria-hidden={partial || undefined}>{partial ? <WrittenText letters={writing} count={count} /> : message.text}</p>}
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
            </div>
          </div>}
        <div className="composer-area">
          <form className="composer" onSubmit={submit}>
            {quote && <QuoteCard quote={quote} onRemove={saving ? undefined : onClearQuote} />}
            {photo && (
              <DraftPhoto
                file={photo}
                disabled={saving}
                onRemove={() => { setPhotoError(''); onPhoto(null) }}
                onInvalid={() => {
                  setPhotoError('Не удалось открыть фото. Попробуйте другой файл.')
                  onPhoto(null)
                }}
              />
            )}
            <div className="composer-line">
              <textarea ref={textarea} rows={3} value={draft} maxLength={4000} readOnly={saving} onChange={(event) => onDraft(event.target.value)} placeholder={quote ? 'Добавьте вопрос к цитате…' : 'Напишите вопрос…'} aria-label="Вопрос для чата"
                onPaste={pastePhoto}
                onKeyDown={(event) => {
                  if (event.key === 'Enter' && !event.shiftKey && !event.nativeEvent.isComposing) {
                    event.preventDefault()
                    if (canSend) onSend(draft)
                  }
                }} />
            </div>
            {(photoError || sendError) && <p className="form-error composer-error" role="alert">{photoError || sendError}</p>}
            {saving && <p className="composer-hint" role="status">Обрабатываю фото…</p>}
            <div className="composer-actions">
              <div className="composer-tools">
                <button className="text-button library-shortcut" type="button" onClick={onLibrary}><BookOpen size={16} /> Все учебники</button>
                <button className="icon-button attachment-button" type="button" aria-label="Прикрепить фото" title="Прикрепить фото" disabled={saving} onClick={() => fileInput.current?.click()}>
                  <ImagePlus size={19} />
                </button>
                <input ref={fileInput} type="file" accept={PHOTO_TYPES.join(',')} hidden onChange={(event) => {
                  const file = event.currentTarget.files?.[0]
                  event.currentTarget.value = ''
                  if (file) selectPhoto(file)
                }} />
              </div>
              <button className="send-button icon-button" type="submit" disabled={!canSend} aria-label="Отправить вопрос"><ArrowUp size={20} /></button>
            </div>
          </form>
          <p className="composer-hint">Enter — отправить · Shift + Enter — новая строка</p>
          <p className="composer-hint">Текстовые ответы в деморежиме</p>
        </div>
      </div>
    </section>
  )
}
