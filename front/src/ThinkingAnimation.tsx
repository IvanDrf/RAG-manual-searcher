import { useEffect, useRef, useState } from 'react'
import { SHAPE_INTERVAL_MS } from './replyPresentation'

type Point = readonly [number, number]
type Path = readonly Point[]
type Shape = { label: string; strokes: Path[]; dots?: Point[] }

const width = 180
const height = 76
const segments = 26
const graphNodes: Point[] = [[50, 25], [88, 11], [132, 27], [117, 58], [74, 62], [90, 36]]
const graphEdges = [[0, 1], [1, 2], [2, 3], [3, 4], [4, 0], [0, 5], [1, 5], [2, 5], [3, 5], [4, 5]]
const axes: Path[] = [[[31, 59], [150, 59]], [[49, 66], [49, 13]]]

function curve(formula: (t: number) => number): Point[] {
  return Array.from({ length: segments + 1 }, (_, index) => {
    const t = index / segments * 2 - 1
    return [91 + t * 55, formula(t)]
  })
}

function arrow(start: Point, end: Point): Path[] {
  const angle = Math.atan2(end[1] - start[1], end[0] - start[0])
  const head = (offset: number): Point => [
    end[0] - Math.cos(angle + offset) * 9,
    end[1] - Math.sin(angle + offset) * 9,
  ]
  return [[start, end], [head(-.47), end, head(.47)]]
}

const shapes: Shape[] = [
  { label: 'Граф', strokes: graphEdges.map(([a, b]) => [graphNodes[a], graphNodes[b]]), dots: graphNodes },
  {
    label: 'Функция',
    strokes: [
      curve((t) => 42 - 22 * t + 13 * Math.sin(t * Math.PI)),
      ...axes,
      [[113, 44], [113, 59]],
    ],
    dots: [[113, 44]],
  },
  {
    label: 'Дифференциальное уравнение',
    // The individual strokes form y′ + ky = 0 so the equation can morph like the diagrams.
    strokes: [
      [[38, 31], [45, 45], [55, 30]],
      [[53, 32], [46, 52], [40, 57]],
      [[62, 25], [58, 31]],
      [[69, 39], [84, 39]],
      [[76, 32], [76, 46]],
      [[93, 27], [90, 49]],
      [[102, 32], [91, 40], [100, 48]],
      [[107, 33], [113, 45], [121, 32], [114, 52], [108, 56]],
      [[126, 37], [138, 37]],
      [[126, 42], [138, 42]],
      [[149, 34], [153, 32], [158, 34], [160, 40], [158, 46], [153, 48], [149, 46], [147, 40], [149, 34]],
    ],
  },
  {
    label: 'Векторы',
    strokes: [
      ...arrow([69, 58], [123, 26]),
      ...arrow([69, 58], [134, 54]),
      ...arrow([69, 58], [70, 17]),
      [[70, 22], [123, 22], [123, 55]],
    ],
    dots: [[69, 58]],
  },
  {
    label: 'Гауссово распределение',
    strokes: [
      curve((t) => 59 - 42 * Math.exp(-6 * t * t)),
      [[29, 61], [152, 61]],
      [[91, 61], [91, 16]],
      [[68, 61], [68, 43]],
      [[114, 61], [114, 43]],
    ],
  },
]

function interpolate(from: number, to: number, progress: number) {
  return from + (to - from) * progress
}

function sample(path: Path): Point[] {
  const lengths = path.slice(1).map((point, index) =>
    Math.hypot(point[0] - path[index][0], point[1] - path[index][1]),
  )
  const total = lengths.reduce((sum, length) => sum + length, 0)
  let edge = 0
  let before = 0

  return Array.from({ length: segments + 1 }, (_, index) => {
    if (total === 0) return path[0]
    const distance = total * index / segments
    while (edge < lengths.length - 1 && distance > before + lengths[edge]) {
      before += lengths[edge]
      edge += 1
    }
    const progress = lengths[edge] ? (distance - before) / lengths[edge] : 0
    return [
      interpolate(path[edge][0], path[edge + 1][0], progress),
      interpolate(path[edge][1], path[edge + 1][1], progress),
    ]
  })
}

const drawings = shapes.map((shape) => ({ ...shape, strokes: shape.strokes.map(sample) }))
const origin: Point = [90, 40]

function drawMorph(context: CanvasRenderingContext2D, index: number, progress: number) {
  const from = drawings[index]
  const to = drawings[(index + 1) % drawings.length]
  const count = Math.max(from.strokes.length, to.strokes.length)
  context.clearRect(0, 0, width, height)

  for (let stroke = 0; stroke < count; stroke++) {
    const left = from.strokes[stroke]
    const right = to.strokes[stroke]
    context.globalAlpha = .83 * (left && right ? 1 : left ? 1 - progress : progress)
    context.beginPath()
    for (let point = 0; point <= segments; point++) {
      const start = left?.[point] ?? right?.[0] ?? origin
      const end = right?.[point] ?? left?.[segments] ?? origin
      const x = interpolate(start[0], end[0], progress)
      const y = interpolate(start[1], end[1], progress)
      if (point === 0) context.moveTo(x, y)
      else context.lineTo(x, y)
    }
    context.stroke()
  }

  const fromDots = from.dots ?? []
  const toDots = to.dots ?? []
  for (let dot = 0; dot < Math.max(fromDots.length, toDots.length); dot++) {
    const start = fromDots[dot] ?? origin
    const end = toDots[dot] ?? origin
    context.globalAlpha = fromDots[dot] && toDots[dot] ? 1 : fromDots[dot] ? 1 - progress : progress
    context.beginPath()
    context.arc(interpolate(start[0], end[0], progress), interpolate(start[1], end[1], progress), 2.3, 0, 2 * Math.PI)
    context.fill()
  }
  context.globalAlpha = 1
}

export function ThinkingAnimation({ startedAt }: { startedAt: number }) {
  const canvas = useRef<HTMLCanvasElement>(null)
  const [label, setLabel] = useState(shapes[0].label)

  useEffect(() => {
    const surface = canvas.current
    const context = surface?.getContext('2d')
    if (!surface || !context) return
    const density = Math.min(window.devicePixelRatio || 1, 2)
    surface.width = width * density
    surface.height = height * density
    context.scale(density, density)
    context.lineWidth = 1.45
    context.lineCap = 'round'
    context.lineJoin = 'round'

    let frame = 0
    let shownLabel = ''
    function paint(now: number) {
      if (!context || !surface) return
      const elapsed = Math.max(0, now - startedAt) / SHAPE_INTERVAL_MS
      const step = Math.floor(elapsed)
      const index = step % drawings.length
      const fraction = elapsed - step
      const t = Math.max(0, (fraction - .38) / .62)
      const progress = t * t * (3 - 2 * t)
      const nextLabel = drawings[(index + (progress > .5 ? 1 : 0)) % drawings.length].label
      if (nextLabel !== shownLabel) {
        shownLabel = nextLabel
        setLabel(nextLabel)
      }
      context.strokeStyle = context.fillStyle = getComputedStyle(surface).color
      drawMorph(context, index, progress)
      frame = requestAnimationFrame(paint)
    }
    frame = requestAnimationFrame(paint)
    return () => cancelAnimationFrame(frame)
  }, [startedAt])

  return (
    <div className="thinking-animation" role="status" aria-label="Готовим ответ">
      <canvas ref={canvas} aria-hidden="true" />
      <div aria-hidden="true">
        <span>Готовим ответ</span>
        <small>{label}</small>
      </div>
    </div>
  )
}
