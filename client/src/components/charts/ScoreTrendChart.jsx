import { useState } from 'react'
import { BarChart3, Table2 } from 'lucide-react'
import { useElementWidth } from '../../hooks/useElementWidth'
import { formatDateTime } from '../../utils/format'

const HEIGHT = 220
const MARGIN = { top: 16, right: 12, bottom: 30, left: 36 }
const MAX_BAR = 24
const TICKS = [0, 25, 50, 75, 100]

export function ScoreTrendChart({ points }) {
  const [ref, width] = useElementWidth()
  const [active, setActive] = useState(null)
  const [view, setView] = useState('chart')

  const plotWidth = Math.max(0, width - MARGIN.left - MARGIN.right)
  const plotHeight = HEIGHT - MARGIN.top - MARGIN.bottom
  const slot = points.length ? plotWidth / points.length : 0
  const barWidth = Math.max(4, Math.min(MAX_BAR, slot - 2))
  const y = (score) => MARGIN.top + plotHeight * (1 - score / 100)

  // Label only the first and last columns on the x axis to avoid collisions.
  const labelIndexes = new Set(points.length ? [0, points.length - 1] : [])
  const activePoint = active !== null ? points[active] : null

  return (
    <div className="chart">
      <div className="chart__toolbar">
        <div className="segmented" role="tablist" aria-label="View">
          <button role="tab" aria-selected={view === 'chart'} className={view === 'chart' ? 'is-active' : ''} onClick={() => setView('chart')}>
            <BarChart3 size={14} /> Chart
          </button>
          <button role="tab" aria-selected={view === 'table'} className={view === 'table' ? 'is-active' : ''} onClick={() => setView('table')}>
            <Table2 size={14} /> Table
          </button>
        </div>
      </div>

      {view === 'table' ? (
        <div className="table-wrap">
          <table className="data-table">
            <thead>
              <tr>
                <th>#</th>
                <th>Resume</th>
                <th>Job</th>
                <th>Date</th>
                <th className="num">Score</th>
              </tr>
            </thead>
            <tbody>
              {points.map((point, index) => (
                <tr key={point.id}>
                  <td className="num">{index + 1}</td>
                  <td>{point.resumeLabel}</td>
                  <td>{point.jobLabel}</td>
                  <td>{formatDateTime(point.createdAt)}</td>
                  <td className="num">{point.score}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <div className="chart__plot" ref={ref} onMouseLeave={() => setActive(null)}>
          {width > 0 && (
            <svg width={width} height={HEIGHT} role="img" aria-label={`Match scores of ${points.length} analyses`}>
              {TICKS.map((tick) => (
                <g key={tick}>
                  <line x1={MARGIN.left} x2={width - MARGIN.right} y1={y(tick)} y2={y(tick)} className="chart__grid" />
                  <text x={MARGIN.left - 8} y={y(tick)} className="chart__tick" textAnchor="end" dominantBaseline="middle">
                    {tick}
                  </text>
                </g>
              ))}

              {points.map((point, index) => {
                const cx = MARGIN.left + slot * index + slot / 2
                const top = y(point.score)
                const height = Math.max(0, MARGIN.top + plotHeight - top)
                const radius = Math.min(4, barWidth / 2, height)
                const x = cx - barWidth / 2
                const bottom = MARGIN.top + plotHeight
                // 4px rounded data-end, square at the baseline.
                const path = height
                  ? `M${x},${bottom} V${top + radius} Q${x},${top} ${x + radius},${top} H${x + barWidth - radius} Q${x + barWidth},${top} ${x + barWidth},${top + radius} V${bottom} Z`
                  : ''
                return (
                  <g
                    key={point.id}
                    tabIndex={0}
                    className="chart__hit"
                    onMouseEnter={() => setActive(index)}
                    onFocus={() => setActive(index)}
                    onBlur={() => setActive(null)}
                    aria-label={`Analysis ${index + 1}: score ${point.score}, ${point.resumeLabel} vs ${point.jobLabel}`}
                  >
                    <rect x={cx - slot / 2} y={MARGIN.top} width={slot} height={plotHeight} fill="transparent" />
                    <path d={path} className={`chart__bar ${active === index ? 'is-active' : ''}`} />
                    {labelIndexes.has(index) && (
                      <text x={cx} y={HEIGHT - 10} className="chart__tick" textAnchor="middle">
                        #{index + 1}
                      </text>
                    )}
                  </g>
                )
              })}
              <line
                x1={MARGIN.left}
                x2={width - MARGIN.right}
                y1={MARGIN.top + plotHeight}
                y2={MARGIN.top + plotHeight}
                className="chart__axis"
              />
            </svg>
          )}

          {activePoint && (
            <div
              className="chart__tooltip"
              style={{
                left: Math.min(
                  Math.max(8, MARGIN.left + slot * active + slot / 2 - 110),
                  Math.max(8, width - 228),
                ),
                top: 4,
              }}
            >
              <strong>Score {activePoint.score}</strong>
              <span>{activePoint.resumeLabel}</span>
              <span className="text-muted">vs {activePoint.jobLabel}</span>
              <span className="text-muted">{formatDateTime(activePoint.createdAt)}</span>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
