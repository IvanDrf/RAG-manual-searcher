import { ChartNoAxesColumnIncreasing, Coins, Users } from 'lucide-react'
import { useState } from 'react'

const demoUsers = [
  { name: 'anna_math', daily: [3200, 2400, 4200, 3700, 5400, 4700, 6100] },
  { name: 'ivan_algebra', daily: [2800, 1900, 3800, 2500, 4100, 3900, 4750] },
  { name: 'maria_stats', daily: [1200, 1600, 2100, 1800, 2900, 2500, 3800] },
  { name: 'pavel_calculus', daily: [1400, 900, 1300, 1500, 2600, 1800, 2750] },
  { name: 'olga_logic', daily: [800, 600, 1100, 900, 1600, 1250, 2300] },
  { name: 'kirill_vector', daily: [300, 450, 750, 520, 1100, 900, 1500] },
]

const days = ['12 ноя', '13 ноя', '14 ноя', '15 ноя', '16 ноя', '17 ноя', '18 ноя']
const number = new Intl.NumberFormat('ru-RU')
const dailyTotals = days.map((_, index) => demoUsers.reduce((sum, user) => sum + user.daily[index], 0))
const ranking = demoUsers.map((user) => ({
  name: user.name,
  total: user.daily.reduce((sum, value) => sum + value, 0),
})).sort((first, second) => second.total - first.total || first.name.localeCompare(second.name))
const total = dailyTotals.reduce((sum, value) => sum + value, 0)
const ceiling = Math.ceil(Math.max(...dailyTotals) / 4000) * 4000

export function AdminDashboard() {
  const [activeDay, setActiveDay] = useState(days.length - 1)

  return (
    <section className="dashboard page-scroll" aria-labelledby="dashboard-title">
      <div className="page-heading">
        <span className="demo-pill">Демоданные</span>
        <h1 id="dashboard-title">Расход токенов</h1>
        <p>Сводка по пользователям за 12–18 ноября.</p>
      </div>
      <div className="stats-grid">
        <article className="stat-card glass"><Coins size={21} /><span>Всего токенов</span><strong>{number.format(total)}</strong></article>
        <article className="stat-card glass"><Users size={21} /><span>Активные пользователи</span><strong>{demoUsers.length}</strong></article>
      </div>
      <article className="dashboard-chart glass" aria-labelledby="chart-title">
        <div className="chart-heading">
          <h2 id="chart-title"><ChartNoAxesColumnIncreasing size={20} /> Токены по дням</h2>
          <span className="muted" aria-live="polite">{days[activeDay]} · {number.format(dailyTotals[activeDay])}</span>
        </div>
        <div className="chart">
          {days.map((day, index) => (
            <button className={'chart-day' + (activeDay === index ? ' chart-active' : '')} key={day} type="button" onClick={() => setActiveDay(index)}
              aria-label={day + ', токенов ' + number.format(dailyTotals[index])} aria-pressed={activeDay === index}>
              <span className="chart-bar-space"><span className="chart-bar" style={{ height: (dailyTotals[index] / ceiling * 100) + '%' }} /></span>
              <span>{day}</span>
            </button>
          ))}
        </div>
      </article>
      <article className="dashboard-table glass">
        <h2>Пользователи по расходу</h2>
        <table>
          <thead><tr><th scope="col">Пользователь</th><th scope="col">Токены ↓</th></tr></thead>
          <tbody>{ranking.map((user) => <tr key={user.name}><td>{user.name}</td><td>{number.format(user.total)}</td></tr>)}</tbody>
        </table>
      </article>
    </section>
  )
}
