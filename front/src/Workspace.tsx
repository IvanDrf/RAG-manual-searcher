import {
  BookOpen, ChartNoAxesColumnIncreasing, ChevronDown, LogOut, Menu,
  PanelLeft, PanelLeftClose, Plus, UserRound,
} from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import { AdminDashboard } from './AdminDashboard'
import { Brand } from './AuthScreen'
import { ChatPanel, type Chat, type Quote, demoReply } from './ChatPanel'
import { Library } from './library/Library'
import type { Session } from './auth'
import { saveChatPhoto, type ChatPhoto } from './photoStore'
import { createReplyPresentation, type ReplyPresentation } from './replyPresentation'
import { ThemeButton, type ThemeControl } from './ThemeButton'

type View = 'chat' | 'library' | 'admin'

function readChats(userId: string): Chat[] {
  try {
    const stored: unknown = JSON.parse(localStorage.getItem('mathdesk.chats.' + userId) ?? '[]')
    if (!Array.isArray(stored)) return []
    return stored.filter((entry): entry is Chat =>
      typeof entry?.id === 'string' && typeof entry?.title === 'string' && Array.isArray(entry?.messages),
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
  const [photo, setPhoto] = useState<File | null>(null)
  const [saving, setSaving] = useState(false)
  const [sendError, setSendError] = useState('')
  const draftRevision = useRef(0)
  const savingPhoto = useRef(false)
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
      localStorage.setItem('mathdesk.chats.' + session.user_id, JSON.stringify(chats))
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
      setPhoto(null)
      setSendError('')
    }
    navigate('chat')
  }

  async function sendMessage(text: string) {
    const message = text.trim()
    if ((!message && !photo) || savingPhoto.current || (activeId && replyTimers.current.has(activeId))) return

    const id = currentChat?.id ?? crypto.randomUUID()
    const revision = draftRevision.current
    let attachment: ChatPhoto | undefined
    setSendError('')
    if (photo) {
      attachment = { id: crypto.randomUUID(), name: photo.name }
      savingPhoto.current = true
      setSaving(true)
      try {
        await saveChatPhoto(session.user_id, attachment, photo)
      } catch {
        if (revision === draftRevision.current) setSendError('Не удалось сохранить фото в браузере. Попробуйте отправить его ещё раз.')
        return
      } finally {
        savingPhoto.current = false
        setSaving(false)
      }
    }

    const subject = message || attachment?.name || 'Фото'
    const title = subject.length > 42 ? subject.slice(0, 41) + '…' : subject
    const reply = { id: crypto.randomUUID(), role: 'assistant' as const, text: demoReply(message, quote, !!attachment) }
    const updated: Chat = {
      id,
      title: currentChat?.title ?? title,
      messages: [
        ...(currentChat?.messages ?? []),
        { id: crypto.randomUUID(), role: 'user', text: message, quote: quote ?? undefined, photo: attachment },
        reply,
      ],
    }
    // Persist the completed demo exchange independently of its onscreen playback.
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
    setChats((previous) => [updated, ...previous.filter((chat) => chat.id !== id)])
    if (photo) setPhoto((current) => current === photo ? null : current)
    if (revision === draftRevision.current) {
      setActiveId(id)
      setDraft('')
      setQuote(null)
    }
  }

  async function logout() {
    if (savingPhoto.current) return
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
        <button className="new-chat" onClick={() => selectChat(null)}><Plus size={19} /> Новый чат</button>
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
        <p className="history-note">История в этом браузере</p>
      </aside>

      <main className="main-workspace">
        <header className="workspace-header">
          <button className="icon-button open-sidebar" aria-label="Переключить боковую панель" onClick={toggleSidebar}>{sidebarOpen ? <Menu size={18} /> : <PanelLeft size={18} />}</button>
          {view === 'chat'
            ? <span className="header-title">{title}</span>
            : <button className="text-button header-title return-chat" onClick={() => navigate('chat')}>Вернуться в чат</button>}
          {view === 'chat' && <span className="demo-pill">Демо</span>}
          <ThemeButton theme={theme} onTheme={onTheme} />
        </header>
        {view === 'chat' && (
          <ChatPanel
            userId={session.user_id}
            chat={currentChat}
            presentation={presentation}
            draft={draft}
            quote={quote}
            photo={photo}
            saving={saving}
            sendError={sendError}
            onDraft={setDraft}
            onPhoto={(file) => { setPhoto(file); setSendError('') }}
            onClearQuote={() => setQuote(null)}
            onSend={sendMessage}
            onLibrary={() => navigate('library')}
          />
        )}
        {view === 'library' && <Library onQuote={(item) => {
          if (savingPhoto.current) draftRevision.current += 1
          setQuote(item)
          navigate('chat')
        }} />}
        {view === 'admin' && isAdmin && <AdminDashboard />}
      </main>
    </div>
  )
}
