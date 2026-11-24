interface Course {
  id: string
  title: string
  description: string
  cover: number
  matches: (file: string) => boolean
}

export interface Lecture {
  id: string
  title: string
  url: string
}

const files = import.meta.glob<string>('../../../data/student_book_pdf/*.pdf', {
  eager: true,
  query: '?url',
  import: 'default',
})

const courses: Course[] = [
  { id: 'analysis', title: 'Математический анализ', description: 'Пределы, производные, кратные интегралы и ряды', cover: 0, matches: (file) => /^(MA|FNP|FPM|KIR)/.test(file) },
  { id: 'algebra', title: 'Линейная алгебра', description: 'Матрицы, векторы и линейные пространства', cover: 1, matches: (file) => file.startsWith('LA-') },
  { id: 'probability', title: 'Теория вероятностей', description: 'События, случайные величины и распределения', cover: 2, matches: (file) => file === 'TV' },
  { id: 'geometry', title: 'Аналитическая геометрия', description: 'Векторы, координаты и дифференциальные формы', cover: 3, matches: (file) => /^(AG|DGM)/.test(file) },
  { id: 'discrete', title: 'Дискретная математика', description: 'Булевы функции, доказательства и графы', cover: 4, matches: (file) => /^(FN_DM|IU9_ML)/.test(file) },
  { id: 'differential', title: 'Дифференциальные уравнения', description: 'Интегралы, уравнения и методы решения', cover: 5, matches: (file) => /^(IDU|UD)/.test(file) },
]

const titled: Record<string, string> = {
  TV: 'Теория вероятностей · конспект лекций',
  AGall: 'Аналитическая геометрия · конспект лекций',
  DGM_FN12: 'Дифференциальные формы и нелинейные системы',
  DGMTU_FN12: 'Дифференциальная геометрия и теория управления',
  FPM_2sem_IU9: 'Функции нескольких переменных',
  MAall: 'Математический анализ · полный курс',
  MA_1sem_IU9: 'Математический анализ · семестр 1',
  MA_2sem_IU9: 'Математический анализ · семестр 2',
  UD1: 'Дифференциальные уравнения · конспект лекций',
  'LA-01': 'Линейные пространства',
  'LA-02': 'Линейные подпространства',
  'LA-03': 'Линейные операторы',
  'LA-04': 'Характеристический многочлен и собственные значения',
  'LA-05': 'Сопряжённые операторы',
  'LA-06': 'Квадратичные формы',
  'LA-07': 'Поверхности второго порядка',
  'FN_DM2-1': 'Булевы функции',
  'FN_DM2-2': 'Логика высказываний',
  'FN_DM2-6': 'Графы',
}

function lectureTitle(file: string): string {
  if (titled[file]) return titled[file]
  const idu = /^IDU_M(\d)_L(\d+)(?:_(\d+))?$/.exec(file)
  if (idu) return 'Модуль ' + idu[1] + ' · лекция ' + Number(idu[2]) + (idu[3] ? '–' + Number(idu[3]) : '')
  const lecture = /^(?:FNP|FN_DM2|IU9_ML)-(\d+)(?:-(\d+))?$/.exec(file)
  if (lecture) {
    const series = file.startsWith('FNP') ? 'Функции нескольких переменных' :
      file.startsWith('IU9') ? 'Математическая логика' : 'Дискретная математика'
    return series + ' · лекция ' + Number(lecture[1]) + (lecture[2] ? '–' + Number(lecture[2]) : '')
  }
  const integrals = /^KIR(\d+)-(\d+)$/.exec(file)
  if (integrals) return 'Кратные интегралы и ряды · лекции ' + Number(integrals[1]) + '–' + Number(integrals[2])
  return file
}

export const lectures: Lecture[] = Object.entries(files)
  .map(([path, url]) => {
    const id = path.split('/').at(-1)!.slice(0, -4)
    return { id, title: lectureTitle(id), url }
  })
  .sort((first, second) => first.id.localeCompare(second.id, 'ru', { numeric: true }))

export const catalog = courses.map(({ matches, ...course }) => ({
  ...course,
  lectures: lectures.filter((lecture) => matches(lecture.id)),
}))
