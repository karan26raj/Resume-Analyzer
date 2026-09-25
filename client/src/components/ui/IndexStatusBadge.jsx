import { AlertTriangle, CheckCircle2, CircleDashed, Clock } from 'lucide-react'
import { Spinner } from './States'

// Mirrors IndexStatus in server/app/models/index_status.py
const STATUS = {
  pending: { label: 'Not indexed', tone: 'neutral', icon: CircleDashed, hint: 'Not in the search index yet. Use Re-index to add it.' },
  queued: { label: 'Queued', tone: 'neutral', icon: Clock, hint: 'Waiting for the background worker.' },
  processing: { label: 'Indexing…', tone: 'accent', hint: 'Being chunked and embedded for search.' },
  indexed: { label: 'Searchable', tone: 'good', icon: CheckCircle2, hint: 'In the search index.' },
  failed: { label: 'Indexing failed', tone: 'critical', icon: AlertTriangle, hint: 'Use Re-index to try again.' },
}

export const IN_PROGRESS_STATUSES = new Set(['queued', 'processing'])

export function isIndexing(document) {
  return IN_PROGRESS_STATUSES.has(document?.index_status)
}

export function IndexStatusBadge({ document }) {
  const status = STATUS[document.index_status] || STATUS.pending
  const Icon = status.icon
  // A queued document with an error is waiting to retry after a failed attempt.
  const detail = document.index_error ? `${status.hint} ${document.index_error}` : status.hint
  const chunks = document.index_status === 'indexed' && document.chunk_count
    ? ` · ${document.chunk_count} chunk${document.chunk_count === 1 ? '' : 's'}`
    : ''

  return (
    <span className={`status-pill status-pill--${status.tone} index-status`} title={detail}>
      {Icon ? <Icon size={13} aria-hidden="true" /> : <Spinner size={11} label="Indexing" />}
      {status.label}
      {chunks && <span className="index-status__chunks">{chunks}</span>}
    </span>
  )
}
