import {
  BookOpen, ChartNoAxesColumnIncreasing, ChevronDown, LogOut,
  PanelLeft, PanelLeftClose, Plus, UserRound,
} from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import { AdminDashboard } from './AdminDashboard'
import { Brand } from './AuthScreen'
import { ChatPanel, type Chat, type Quote } from './ChatPanel'
import { Library } from './library/Library'
import type { Session } from './auth'
import { questionText, sendQuestion } from './chatApi'
import { createReplyPresentation, type ReplyPresentation } from './replyPresentation'
import { ThemeButton, type ThemeControl } from './ThemeButton'

type View = 'chat' | 'library' | 'admin'

function readChats(userId: string): Chat[] {
  try {
    const stored: unknown = JSON.parse(localStorage.getItem('mathdesk.backend-chats.' + userId) ?? '[]')
    if (!Array.isArray(stored)) return []
    return stored.filter((entry): entry is Chat =>
      typeof entry?.id === 'string' && typeof entry?.title === 'string' &&
      typeof entry?.serverId === 'string' && Array.isArray(entry?.messages),
    )
  } catch {
    return []
  }
}

interface WorkspaceProps extends ThemeControl {
  session: Session
  onLogout: () => Promise<void>
}

export function Workspace({ session, onLogout, theme, onTheme }: WorkspaceProps) {
  const [view, setView] = useState<View>('chat')
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [wideSidebar, setWideSidebar] = useState(true)
  const [profileOpen, setProfileOpen] = useState(false)
  const [logoutError, setLogoutError] = useState('')
  const [loggingOut, setLoggingOut] = useState(false)
  const [chats, setChats] = useState(() => readChats(session.user_id))
  const [activeId, setActiveId] = useState<string | null>(null)
  const [draft, setDraft] = useState('')
  const [quote, setQuote] = useState<Quote | null>(null)
  const [saving, setSaving] = useState(false)
  const [pending, setPending] = useState<{ chatId: string; startedAt: number } | null>(null)
  const [sendError, setSendError] = useState('')
  const draftRevision = useRef(0)
  const sending = useRef(false)
  const [presentations, setPresentations] = useState<Record<string, ReplyPresentation>>({})
  const replyTimers = useRef(new Map<string, number>())
  const profile = useRef<HTMLDivElement>(null)
  const isAdmin = session.user_role === 'admin'
  const currentChat = chats.find((chat) => chat.id === activeId)
  const presentation = activeId ? presentations[activeId] : undefined

  useEffect(() => {
    const timers = replyTimers.current
    return () => {
      for (const timer of timers.values()) window.clearTimeout(timer)
      timers.clear()
    }
  }, [])

  useEffect(() => {
    try {
      localStorage.setItem('mathdesk.backend-chats.' + session.user_id, JSON.stringify(chats))
    } catch {
      // The chat still works if the browser disables local storage.
    }
  }, [chats, session.user_id])

  useEffect(() => {
    if (!profileOpen && !sidebarOpen) return
    function dismiss(event: KeyboardEvent) {
      if (event.key === 'Escape') {
        setProfileOpen(false)
        setSidebarOpen(false)
      }
    }
    function closeProfile(event: PointerEvent) {
      if (event.target instanceof Node && !profile.current?.contains(event.target)) {
        setProfileOpen(false)
      }
    }
    window.addEventListener('keydown', dismiss)
    window.addEventListener('pointerdown', closeProfile)
    return () => {
      window.removeEventListener('keydown', dismiss)
      window.removeEventListener('pointerdown', closeProfile)
    }
  }, [profileOpen, sidebarOpen])

  function navigate(next: View) {
    if (next === 'admin' && !isAdmin) return
    setView(next)
    setSidebarOpen(false)
    setProfileOpen(false)
  }

  function selectChat(id: string | null) {
    if (id !== activeId || id === null) {
      draftRevision.current += 1
      setActiveId(id)
      setDraft('')
      setQuote(null)
      setSendError('')
    }
    navigate('chat')
  }

  async function sendMessage(text: string) {
    if (sending.current || (activeId && replyTimers.current.has(activeId))) return
    setSendError('')
    let message: string
    try {
      message = questionText(text, quote)
    } catch (error) {
      setSendError(error instanceof Error ? error.message : 'Проверьте вопрос.')
      return
    }

    const id = currentChat?.id ?? crypto.randomUUID()
    const revision = draftRevision.current
    const capturedQuote = quote
    const userMessage = { id: crypto.randomUUID(), role: 'user' as const, text: text.trim(), quote: capturedQuote ?? undefined }
    const optimistic: Chat = {
      id,
      serverId: currentChat?.serverId,
      title: currentChat?.title ?? message.slice(0, 42),
      messages: [...(currentChat?.messages ?? []), userMessage],
    }
    sending.current = true
    setSaving(true)
    setPending({ chatId: id, startedAt: performance.now() })
    setChats((previous) => [optimistic, ...previous.filter((chat) => chat.id !== id)])
    setActiveId(id)
    setDraft('')
    setQuote(null)

    try {
      const answer = await sendQuestion(message, session.user_id, currentChat?.serverId)
      const reply = { id: crypto.randomUUID(), role: 'assistant' as const, text: answer.response }
      setChats((previous) => previous.map((chat) => chat.id === id
        ? { ...chat, serverId: answer.chat_id, messages: [...chat.messages, reply] }
        : chat))

      if (!window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
        const playback = createReplyPresentation(reply.id, reply.text)
        setPresentations((previous) => ({ ...previous, [id]: playback }))
        const timer = window.setTimeout(() => {
          replyTimers.current.delete(id)
          setPresentations((previous) => {
            const next = { ...previous }
            delete next[id]
            return next
          })
        }, Math.max(0, playback.endAt - performance.now()))
        replyTimers.current.set(id, timer)
      }
    } catch (error) {
      setChats((previous) => previous.map((chat) => chat.id === id
        ? { ...chat, messages: chat.messages.filter((item) => item.id !== userMessage.id) }
        : chat).filter((chat) => chat.messages.length > 0 || chat.serverId))
      if (revision === draftRevision.current) {
        setActiveId(currentChat?.id ?? null)
        setDraft(text)
        setQuote(capturedQuote)
        setSendError(error instanceof Error ? error.message : 'Не удалось отправить вопрос.')
      }
    } finally {
      sending.current = false
      setSaving(false)
      setPending(null)
    }
  }

  async function logout() {
    if (sending.current) return
    setLogoutError('')
    setLoggingOut(true)
    try {
      await onLogout()
    } catch (error) {
      setLogoutError(error instanceof Error ? error.message : 'Не удалось выйти.')
      setLoggingOut(false)
    }
  }

  const title = view === 'library' ? 'Библиотека' : view === 'admin' ? 'Панель администратора' : currentChat?.title ?? 'Новый чат'

  function toggleSidebar() {
    if (window.matchMedia('(max-width: 760px)').matches) {
      setSidebarOpen((open) => !open)
    } else {
      setWideSidebar((open) => !open)
    }
  }

  return (
    <div className={'workspace' + (wideSidebar ? '' : ' sidebar-collapsed')}>
      {sidebarOpen && <button className="sidebar-overlay" type="button" aria-label="Закрыть панель" onClick={() => setSidebarOpen(false)} />}
      <aside className={'sidebar glass' + (sidebarOpen ? ' sidebar-open' : '')} aria-label="Навигация">
        <div className="sidebar-heading">
          <button className="brand-button" onClick={() => navigate('chat')} aria-label="MathContext — к чату"><Brand /></button>
          <button className="icon-button sidebar-close" aria-label="Свернуть панель" onClick={toggleSidebar}><PanelLeftClose size={17} /></button>
        </div>
        <button className="new-chat" aria-current={view === 'chat' && activeId === null ? 'page' : undefined} onClick={() => selectChat(null)}><Plus size={19} /> Новый чат</button>
        <nav className="sidebar-nav" aria-label="Разделы">
          <button className={view === 'library' ? 'nav-active' : undefined} aria-current={view === 'library' ? 'page' : undefined} onClick={() => navigate('library')}><BookOpen size={17} /> Каталог книг</button>
        </nav>
        <div className="sidebar-history">
          <h2>История чатов</h2>
          {chats.length === 0 && <p className="sidebar-empty">Здесь появятся ваши чаты.</p>}
          {chats.map((chat) => (
            <button key={chat.id} className={view === 'chat' && activeId === chat.id ? 'history-active' : undefined} aria-current={view === 'chat' && activeId === chat.id ? 'true' : undefined} onClick={() => selectChat(chat.id)} title={chat.title}>
              <span>{chat.title}</span>
            </button>
          ))}
        </div>
        <div className="profile-wrap" ref={profile}>
          {profileOpen && (
            <div className="profile-popover glass">
              <strong>Профиль</strong>
              <p className="muted">{isAdmin ? 'Администратор' : 'Пользователь'}</p>
              {isAdmin && <button className="profile-link" onClick={() => navigate('admin')}><ChartNoAxesColumnIncreasing size={17} /> Панель администратора</button>}
              <button className="profile-link" onClick={logout} disabled={loggingOut || saving}><LogOut size={17} /> {loggingOut ? 'Выходим…' : 'Выйти'}</button>
              {logoutError && <p className="form-error" role="alert">{logoutError}</p>}
            </div>
          )}
          <button className="profile-button" aria-expanded={profileOpen} onClick={() => setProfileOpen(!profileOpen)}>
            <span className="profile-avatar"><UserRound size={19} /></span>
            <span className="profile-name"><strong>Мой профиль</strong><small>{isAdmin ? 'Администратор' : 'Пользователь'}</small></span>
            <ChevronDown size={16} />
          </button>
        </div>
        {isAdmin && <button className="admin-link" aria-current={view === 'admin' ? 'page' : undefined} onClick={() => navigate('admin')}><ChartNoAxesColumnIncreasing size={17} /> Администрирование</button>}
      </aside>

      <main className={'main-workspace' + (view === 'chat' ? ' main-workspace-chat' : '')}>
        <header className="workspace-header">
          <button className="icon-button open-sidebar" aria-label="Открыть боковую панель" onClick={toggleSidebar}><PanelLeft size={18} /></button>
          {view === 'chat'
            ? <span className="header-title">{title}</span>
            : <button className="text-button header-title return-chat" onClick={() => navigate('chat')}>Вернуться в чат</button>}
          <ThemeButton theme={theme} onTheme={onTheme} />
        </header>
        {view === 'chat' && (
          <ChatPanel
            userId={session.user_id}
            chat={currentChat}
            presentation={presentation}
            draft={draft}
            quote={quote}
            saving={saving}
            pendingSince={pending?.chatId === activeId ? pending.startedAt : undefined}
            sendError={sendError}
            onDraft={setDraft}
            onClearQuote={() => setQuote(null)}
            onSend={sendMessage}
            onLibrary={() => navigate('library')}
          />
        )}
        {view === 'library' && <Library onQuote={(item) => {
          if (sending.current) draftRevision.current += 1
          setQuote(item)
          navigate('chat')
        }} />}
        {view === 'admin' && isAdmin && <AdminDashboard />}
      </main>
    </div>
  )
}
