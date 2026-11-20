import { ChevronLeft, ChevronRight, FileText, LayoutGrid, List } from 'lucide-react'
import { lazy, Suspense, useState } from 'react'
import type { Quote } from '../ChatPanel'
import { catalog, lectures, type Lecture } from './catalog'

const PdfReader = lazy(() => import('./PdfReader'))
const series = ['I', 'II', 'III', 'IV', 'V', 'VI']

export function Library({ onQuote }: { onQuote: (quote: Quote) => void }) {
  const [courseId, setCourseId] = useState<string | null>(null)
  const [lecture, setLecture] = useState<Lecture | null>(null)
  const [layout, setLayout] = useState<'grid' | 'list'>('grid')
  const course = catalog.find((item) => item.id === courseId)

  if (lecture && course) {
    return (
      <Suspense fallback={<div className="center-status" role="status">Открываем читалку…</div>}>
        <PdfReader key={lecture.id} lecture={lecture} onBack={() => setLecture(null)} onQuote={onQuote} />
      </Suspense>
    )
  }

  return (
    <section className="library page-scroll" aria-labelledby="library-title">
      <div className="page-heading">
        {course && <button className="text-button back-link" onClick={() => setCourseId(null)}><ChevronLeft size={18} /> Все предметы</button>}
        <div className="collection-heading">
          <div>
            {!course && <p className="collection-label">Библиотека MathContext</p>}
            <h1 id="library-title">{course?.title ?? 'Коллекция знаний'}</h1>
            <p>{course?.description ?? (catalog.length + ' предметов · ' + lectures.length + ' PDF')}</p>
          </div>
          {!course && <div className="layout-switch" role="group" aria-label="Вид каталога">
            <button className="icon-button" type="button" aria-label="Сетка" aria-pressed={layout === 'grid'} onClick={() => setLayout('grid')}><LayoutGrid size={18} /></button>
            <button className="icon-button" type="button" aria-label="Список" aria-pressed={layout === 'list'} onClick={() => setLayout('list')}><List size={19} /></button>
          </div>}
        </div>
      </div>
      {course ? (
        <div className="lecture-list glass">
          {course.lectures.map((item) => (
            <button key={item.id} className="lecture-row" onClick={() => setLecture(item)}>
              <span className="lecture-icon"><FileText size={20} /></span>
              <span><strong>{item.title}</strong><small>{item.id}.pdf</small></span>
              <ChevronRight size={19} />
            </button>
          ))}
        </div>
      ) : (
          <div className={'course-grid' + (layout === 'list' ? ' course-list' : '')}>
            {catalog.map((item) => (
              <button key={item.id} className="course-card glass" onClick={() => setCourseId(item.id)}>
                <span className={'course-cover cover-' + item.cover} aria-hidden="true">
                  <span>MathContext</span><strong>{series[item.cover]}</strong>
                </span>
                <span className="course-info">
                  <strong>{item.title}</strong>
                  <span className="course-description">{item.description}</span>
                </span>
                <span className="course-action">Открыть · {item.lectures.length} PDF</span>
              </button>
            ))}
          </div>
      )}
    </section>
  )
}
