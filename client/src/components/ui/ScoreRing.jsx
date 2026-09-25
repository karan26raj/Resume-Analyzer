import { useEffect, useState } from 'react'
import { AlertTriangle, CheckCircle2, CircleAlert } from 'lucide-react'
import { scoreBand } from '../../utils/format'

const BAND_ICONS = { good: CheckCircle2, warning: CircleAlert, critical: AlertTriangle }

export function ScoreRing({ score, size = 200, stroke = 14, showBand = true, animate = true }) {
  const [shown, setShown] = useState(animate ? 0 : score)
  const radius = (size - stroke) / 2
  const circumference = 2 * Math.PI * radius
  const band = scoreBand(score)
  const BandIcon = BAND_ICONS[band.key]

  useEffect(() => {
    if (!animate || window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
      setShown(score)
      return undefined
    }
    let frame
    const start = performance.now()
    const duration = 1100
    const tick = (now) => {
      const progress = Math.min(1, (now - start) / duration)
      const eased = 1 - Math.pow(1 - progress, 3)
      setShown(Math.round(score * eased))
      if (progress < 1) frame = requestAnimationFrame(tick)
    }
    frame = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(frame)
  }, [score, animate])

  const offset = circumference * (1 - shown / 100)

  return (
    <div className="score-ring" style={{ width: size }}>
      <div className="score-ring__graphic" style={{ width: size, height: size }}>
        <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} role="img" aria-label={`Match score ${score} out of 100, ${band.label}`}>
          <circle cx={size / 2} cy={size / 2} r={radius} className={`score-ring__track score-ring__track--${band.key}`} strokeWidth={stroke} />
          <circle
            cx={size / 2}
            cy={size / 2}
            r={radius}
            className={`score-ring__value score-ring__value--${band.key}`}
            strokeWidth={stroke}
            strokeDasharray={circumference}
            strokeDashoffset={offset}
            strokeLinecap="round"
            transform={`rotate(-90 ${size / 2} ${size / 2})`}
          />
        </svg>
        <div className="score-ring__label">
          <span className="score-ring__number" style={{ fontSize: size * 0.26 }}>
            {shown}
          </span>
          <span className="score-ring__max">/ 100</span>
        </div>
      </div>
      {showBand && (
        <span className={`status-pill status-pill--${band.key}`}>
          <BandIcon size={14} aria-hidden="true" /> {band.label}
        </span>
      )}
    </div>
  )
}
