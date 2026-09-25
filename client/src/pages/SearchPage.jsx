import { useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { ArrowRight, BriefcaseBusiness, FileText, ScanSearch, Search, Sparkles } from 'lucide-react'
import { embeddingsApi, jobsApi, resumesApi } from '../api/services'
import { useApi } from '../hooks/useApi'
import { PageHeader } from '../components/ui/PageHeader'
import { EmptyState, ErrorState, Skeleton, Spinner } from '../components/ui/States'
import { SearchIllustration } from '../components/ui/Illustrations'
import { similarityPercent } from '../utils/format'

const SUGGESTIONS = [
  'Backend API development experience',
  'Cloud and DevOps skills',
  'Machine learning projects',
  'Leadership and teamwork',
  'Database and SQL experience',
]

const TYPE_OPTIONS = [
  { value: '', label: 'All documents' },
  { value: 'resume', label: 'Resumes' },
  { value: 'job', label: 'Jobs' },
]

function escapeRegExp(text) {
  return text.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
}

const STOPWORDS = new Set(['and', 'the', 'for', 'with', 'from', 'that', 'this', 'are', 'was', 'you', 'your', 'have', 'has', 'into', 'about'])

function Highlighted({ text, query }) {
  const terms = [
    ...new Set(
      query
        .toLowerCase()
        .split(/\W+/)
        .filter((term) => term.length >= 3 && !STOPWORDS.has(term)),
    ),
  ]
  if (!terms.length) return text
  const pattern = new RegExp(`\\b(${terms.map(escapeRegExp).join('|')})\\b`, 'gi')
  return text.split(pattern).map((part, index) =>
    terms.includes(part.toLowerCase()) ? <mark key={index}>{part}</mark> : <span key={index}>{part}</span>,
  )
}

function ResultCard({ result, query, sourceName }) {
  const [expanded, setExpanded] = useState(false)
  const percent = similarityPercent(result.score)
  const isResume = result.document_type === 'resume'
  const long = result.content.length > 420
  const shown = expanded || !long ? result.content : `${result.content.slice(0, 420)}…`
  const documentLink = isResume ? '/resumes' : '/jobs'

  return (
    <article className="card result-card">
      <header className="result-card__header">
        <span className={`source-tag source-tag--${result.document_type}`}>
          {isResume ? <FileText size={14} aria-hidden="true" /> : <BriefcaseBusiness size={14} aria-hidden="true" />}
          {isResume ? 'Resume' : 'Job'}
        </span>
        <Link to={documentLink} className="result-card__source" title={sourceName}>
          {sourceName}
        </Link>
        <span className="result-card__chunk">Chunk {result.chunk_index + 1}</span>
        <span className="similarity" title={`Cosine similarity ${result.score.toFixed(3)}`}>
          <span className="similarity__bar" aria-hidden="true">
            <span style={{ width: `${percent}%` }} />
          </span>
          <span className="similarity__value">{percent}% similar</span>
        </span>
      </header>
      <p className="result-card__content">
        <Highlighted text={shown} query={query} />
      </p>
      {long && (
        <button className="link-button" onClick={() => setExpanded((value) => !value)}>
          {expanded ? 'Show less' : 'Show full chunk'}
        </button>
      )}
    </article>
  )
}

export function SearchPage() {
  const resumes = useApi((signal) => resumesApi.list({ signal }))
  const jobs = useApi((signal) => jobsApi.list({ signal }))
  const [query, setQuery] = useState('')
  const [documentType, setDocumentType] = useState('')
  const [limit, setLimit] = useState(10)
  const [state, setState] = useState({ status: 'idle' })

  const names = useMemo(() => {
    const map = new Map()
    ;(resumes.data || []).forEach((resume) => map.set(`resume-${resume.id}`, resume.filename))
    ;(jobs.data || []).forEach((job) => map.set(`job-${job.id}`, `${job.title} · ${job.company}`))
    return map
  }, [resumes.data, jobs.data])

  const search = async (text = query) => {
    const trimmed = text.trim()
    if (!trimmed) return
    setQuery(trimmed)
    setState((current) => ({ ...current, status: 'loading' }))
    try {
      const results = await embeddingsApi.search({ query: trimmed, documentType, limit })
      setState({ status: 'done', results, query: trimmed })
    } catch (error) {
      setState({ status: 'error', error, query: trimmed })
    }
  }

  const sourceName = (result) => {
    const id = result.document_type === 'resume' ? result.resume_id : result.job_id
    return names.get(`${result.document_type}-${id}`) || `${result.document_type === 'resume' ? 'Resume' : 'Job'} #${id}`
  }

  return (
    <>
      <PageHeader
        eyebrow="Retrieval"
        title="Semantic search"
        description="Search your resumes and job descriptions by meaning, not just keywords."
      />

      <section className="search-hero card card--glass">
        <form
          className="search-hero__form"
          onSubmit={(event) => {
            event.preventDefault()
            search()
          }}
        >
          <label className="search-hero__input">
            <ScanSearch size={22} aria-hidden="true" />
            <input
              type="search"
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="e.g. experience building REST APIs with Python"
              aria-label="Search query"
              maxLength={5000}
              autoFocus
            />
          </label>
          <button type="submit" className="btn btn--primary btn--lg" disabled={!query.trim() || state.status === 'loading'}>
            {state.status === 'loading' ? <Spinner size={16} /> : <Search size={18} />} Search
          </button>
        </form>

        <div className="search-hero__filters">
          <div className="segmented" role="tablist" aria-label="Document type">
            {TYPE_OPTIONS.map((option) => (
              <button
                key={option.value}
                role="tab"
                aria-selected={documentType === option.value}
                className={documentType === option.value ? 'is-active' : ''}
                onClick={() => setDocumentType(option.value)}
              >
                {option.label}
              </button>
            ))}
          </div>
          <label className="compact-select">
            Results
            <select value={limit} onChange={(event) => setLimit(Number(event.target.value))}>
              {[5, 10, 20].map((value) => (
                <option key={value} value={value}>
                  {value}
                </option>
              ))}
            </select>
          </label>
        </div>

        <div className="suggestions" aria-label="Suggested searches">
          <Sparkles size={14} aria-hidden="true" />
          <span className="text-muted">Try:</span>
          {SUGGESTIONS.map((suggestion) => (
            <button key={suggestion} className="suggestion-chip" onClick={() => search(suggestion)}>
              {suggestion}
            </button>
          ))}
        </div>
      </section>

      <section className="section" aria-live="polite">
        {state.status === 'idle' && (
          <div className="card">
            <EmptyState
              illustration={SearchIllustration}
              title="Search across your documents"
              description="Results are the passages from your indexed resumes and jobs closest in meaning to your query, ranked by similarity."
            />
          </div>
        )}

        {state.status === 'loading' && (
          <div className="stack">
            {Array.from({ length: 3 }, (_, index) => (
              <div key={index} className="card">
                <Skeleton height={14} width="45%" />
                <Skeleton height={60} className="mt-sm" />
              </div>
            ))}
          </div>
        )}

        {state.status === 'error' && (
          <div className="card">
            <ErrorState title="Search failed" error={state.error} onRetry={() => search(state.query)} />
          </div>
        )}

        {state.status === 'done' &&
          (state.results.length === 0 ? (
            <div className="card">
              <EmptyState
                illustration={SearchIllustration}
                title="No indexed passages found"
                description="Upload a resume or add a job — they are indexed automatically. You can also re-index a document from its page."
                action={
                  <Link to="/resumes" className="btn btn--secondary">
                    Go to resumes <ArrowRight size={16} />
                  </Link>
                }
              />
            </div>
          ) : (
            <>
              <p className="results-summary">
                {state.results.length} passage{state.results.length === 1 ? '' : 's'} for “{state.query}”
              </p>
              <div className="stack">
                {state.results.map((result) => (
                  <ResultCard key={result.chunk_id} result={result} query={state.query} sourceName={sourceName(result)} />
                ))}
              </div>
            </>
          ))}
      </section>
    </>
  )
}
