// The API stores naive UTC timestamps ("2026-09-24T18:27:01.644466"); mark them as UTC
// so the browser converts them to the viewer's local time.
export function parseApiDate(value) {
  if (!value) return null
  const hasZone = /[zZ]|[+-]\d{2}:?\d{2}$/.test(value)
  const date = new Date(hasZone ? value : `${value}Z`)
  return Number.isNaN(date.getTime()) ? null : date
}

const dateFormatter = new Intl.DateTimeFormat(undefined, { day: 'numeric', month: 'short', year: 'numeric' })
const dateTimeFormatter = new Intl.DateTimeFormat(undefined, {
  day: 'numeric',
  month: 'short',
  hour: 'numeric',
  minute: '2-digit',
})

export function formatDate(value) {
  const date = parseApiDate(value)
  return date ? dateFormatter.format(date) : '—'
}

export function formatDateTime(value) {
  const date = parseApiDate(value)
  return date ? dateTimeFormatter.format(date) : '—'
}

export function formatRelative(value) {
  const date = value instanceof Date ? value : parseApiDate(value)
  if (!date) return '—'
  const seconds = Math.round((date.getTime() - Date.now()) / 1000)
  const units = [
    ['year', 31536000],
    ['month', 2592000],
    ['week', 604800],
    ['day', 86400],
    ['hour', 3600],
    ['minute', 60],
  ]
  const formatter = new Intl.RelativeTimeFormat(undefined, { numeric: 'auto' })
  for (const [unit, size] of units) {
    if (Math.abs(seconds) >= size) return formatter.format(Math.round(seconds / size), unit)
  }
  return 'just now'
}

export function formatNumber(value) {
  if (value === null || value === undefined) return '—'
  return new Intl.NumberFormat(undefined, { notation: value >= 10000 ? 'compact' : 'standard' }).format(value)
}

export function formatBytes(bytes) {
  if (!bytes && bytes !== 0) return '—'
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

export function fileTypeLabel(fileType) {
  return (fileType || '').replace('.', '').toUpperCase() || 'FILE'
}

export function scoreBand(score) {
  if (score >= 75) return { key: 'good', label: 'Strong match' }
  if (score >= 50) return { key: 'warning', label: 'Partial match' }
  return { key: 'critical', label: 'Weak match' }
}

export function similarityPercent(score) {
  return Math.round(Math.max(0, Math.min(1, score)) * 100)
}
