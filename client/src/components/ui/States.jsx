import { RefreshCw } from 'lucide-react'
import { ErrorIllustration } from './Illustrations'

export function Spinner({ size = 18, label }) {
  return (
    <span className="spinner" style={{ width: size, height: size }} role="status" aria-label={label || 'Loading'} />
  )
}

export function Skeleton({ height = 16, width = '100%', radius = 8, className = '' }) {
  return <span className={`skeleton ${className}`} style={{ height, width, borderRadius: radius }} aria-hidden="true" />
}

export function SkeletonCards({ count = 3, height = 120 }) {
  return (
    <div className="card-grid" aria-busy="true" aria-label="Loading">
      {Array.from({ length: count }, (_, index) => (
        <div key={index} className="card skeleton-card">
          <Skeleton height={14} width="40%" />
          <Skeleton height={height - 60} />
          <Skeleton height={12} width="65%" />
        </div>
      ))}
    </div>
  )
}

export function EmptyState({ illustration: Illustration, title, description, action, compact = false }) {
  return (
    <div className={`empty-state ${compact ? 'empty-state--compact' : ''}`}>
      {Illustration && <Illustration />}
      <h3>{title}</h3>
      {description && <p>{description}</p>}
      {action && <div className="empty-state__action">{action}</div>}
    </div>
  )
}

export function ErrorState({ error, onRetry, title = 'Something went wrong', compact = false }) {
  return (
    <div className={`empty-state empty-state--error ${compact ? 'empty-state--compact' : ''}`} role="alert">
      {!compact && <ErrorIllustration />}
      <h3>{title}</h3>
      <p>{error?.message || 'An unexpected error occurred.'}</p>
      {onRetry && (
        <div className="empty-state__action">
          <button className="btn btn--secondary" onClick={onRetry}>
            <RefreshCw size={16} /> Try again
          </button>
        </div>
      )}
    </div>
  )
}

export function InlineError({ children }) {
  if (!children) return null
  return (
    <p className="inline-error" role="alert">
      {children}
    </p>
  )
}
