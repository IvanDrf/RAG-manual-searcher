import { ChevronLeft, ChevronRight, LoaderCircle, MessageSquarePlus } from 'lucide-react'
import { GlobalWorkerOptions, TextLayer, getDocument, type PDFDocumentProxy } from 'pdfjs-dist'
import workerUrl from 'pdfjs-dist/build/pdf.worker.min.mjs?url'
import { useEffect, useRef, useState, type CSSProperties } from 'react'
import type { Quote } from '../ChatPanel'
import type { Lecture } from './catalog'

GlobalWorkerOptions.workerSrc = workerUrl

type PdfState = { status: 'loading' } | { status: 'error' } | { status: 'ready'; document: PDFDocumentProxy }

interface ReaderProps {
  lecture: Lecture
  onBack: () => void
  onQuote: (quote: Quote) => void
}

export default function PdfReader({ lecture, onBack, onQuote }: ReaderProps) {
  const [state, setState] = useState<PdfState>({ status: 'loading' })
  const [page, setPage] = useState(1)
  const [selection, setSelection] = useState('')
  const [width, setWidth] = useState(700)
  const container = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const load = getDocument({ url: lecture.url })
    let active = true
    void load.promise.then(
      (document) => { if (active) setState({ status: 'ready', document }) },
      () => { if (active) setState({ status: 'error' }) },
    )
    return () => { active = false; void load.destroy().catch(() => undefined) }
  }, [lecture.url])

  useEffect(() => {
    if (!container.current) return
    const resize = new ResizeObserver(([entry]) => setWidth(Math.min(840, Math.max(190, Math.floor(entry.contentRect.width)))))
    resize.observe(container.current)
    return () => resize.disconnect()
  }, [])

  function go(next: number) {
    setPage(next)
    setSelection('')
    container.current?.scrollTo({ top: 0 })
  }

  return (
    <section className="reader glass" aria-labelledby="reader-title">
      <header className="reader-header">
        <button className="icon-button" aria-label="Назад к списку лекций" onClick={onBack}><ChevronLeft size={21} /></button>
        <div className="reader-title"><h1 id="reader-title">{lecture.title}</h1><span>{lecture.id}.pdf</span></div>
        <div className="reader-pages">
          <button className="icon-button" type="button" onClick={() => go(page - 1)} disabled={page <= 1} aria-label="Предыдущая страница"><ChevronLeft size={19} /></button>
          <span aria-live="polite">{page} / {state.status === 'ready' ? state.document.numPages : '—'}</span>
          <button className="icon-button" type="button" onClick={() => go(page + 1)} disabled={state.status !== 'ready' || page >= state.document.numPages} aria-label="Следующая страница"><ChevronRight size={19} /></button>
        </div>
      </header>
      <div className="reader-actions">
        <span>{selection ? 'Фрагмент выделен' : 'Выделите текст, чтобы обсудить его в чате.'}</span>
        <button type="button" className="primary" disabled={!selection} onMouseDown={(event) => { if (selection) event.preventDefault() }}
          onClick={() => onQuote({ text: selection, lecture: lecture.title, page })}>
          <MessageSquarePlus size={17} /> Обсудить в чате
        </button>
      </div>
      <div className="pdf-scroll" ref={container}>
        {state.status === 'error' && <p className="pdf-status" role="alert">Не удалось открыть PDF. <a href={lecture.url} target="_blank" rel="noreferrer">Открыть файл в новой вкладке</a></p>}
        {state.status === 'loading' && <p className="pdf-status" role="status"><LoaderCircle className="spin" size={20} /> Загружаем лекцию…</p>}
        {state.status === 'ready' && <PdfPage key={page + ':' + width} pdf={state.document} page={page} width={width} onSelection={setSelection} />}
      </div>
    </section>
  )
}

interface PageProps {
  pdf: PDFDocumentProxy
  page: number
  width: number
  onSelection: (text: string) => void
}

function PdfPage({ pdf, page, width, onSelection }: PageProps) {
  const canvas = useRef<HTMLCanvasElement>(null)
  const layer = useRef<HTMLDivElement>(null)
  const [size, setSize] = useState<{ width: number; height: number; scale: number } | null>(null)
  const [error, setError] = useState(false)
  const [hasText, setHasText] = useState<boolean | null>(null)

  useEffect(() => {
    let active = true
    let cancelCanvas: (() => void) | undefined
    let textLayer: TextLayer | undefined

    async function paint() {
      const pdfPage = await pdf.getPage(page)
      if (!active || !canvas.current || !layer.current) return
      const natural = pdfPage.getViewport({ scale: 1 })
      const viewport = pdfPage.getViewport({ scale: width / natural.width })
      const density = Math.min(window.devicePixelRatio || 1, 2)
      const surface = canvas.current
      const context = surface.getContext('2d')
      if (!context) throw new Error('Не удалось создать холст.')
      surface.width = Math.ceil(viewport.width * density)
      surface.height = Math.ceil(viewport.height * density)
      setSize({ width: viewport.width, height: viewport.height, scale: viewport.scale })

      const render = pdfPage.render({ canvas: surface, canvasContext: context, viewport, transform: [density, 0, 0, density, 0, 0] })
      cancelCanvas = () => render.cancel()
      const [content] = await Promise.all([pdfPage.getTextContent(), render.promise])
      if (!active || !layer.current) return
      textLayer = new TextLayer({ textContentSource: content, container: layer.current, viewport })
      await textLayer.render()
      if (active) setHasText(content.items.some((item) => 'str' in item && item.str.trim()))
    }

    void paint().catch(() => { if (active) setError(true) })
    return () => { active = false; cancelCanvas?.(); textLayer?.cancel() }
  }, [pdf, page, width])

  useEffect(() => {
    function captureSelection() {
      const selection = window.getSelection()
      if (!selection || !layer.current?.contains(selection.anchorNode) || !layer.current.contains(selection.focusNode)) return
      onSelection(selection.toString().replace(/\s+/g, ' ').trim().slice(0, 3000))
    }
    document.addEventListener('selectionchange', captureSelection)
    return () => document.removeEventListener('selectionchange', captureSelection)
  }, [onSelection])

  if (error) return <p className="pdf-status" role="alert">Не удалось отобразить эту страницу.</p>
  const style = size ? { width: size.width, height: size.height, '--scale-factor': size.scale, '--total-scale-factor': size.scale } as CSSProperties : undefined

  return (
    <>
      {!size && <p className="pdf-status" role="status">Загружаем страницу…</p>}
      {hasText === false && <p className="pdf-status">На этой странице нет текстового слоя для выделения.</p>}
      <div className="pdf-paper" style={style} hidden={!size}>
        <canvas ref={canvas} aria-label={'Страница ' + page} />
        <div ref={layer} className="textLayer" />
      </div>
    </>
  )
}
