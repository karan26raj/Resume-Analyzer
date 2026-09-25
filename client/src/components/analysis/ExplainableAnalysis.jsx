import { useMemo, useState } from 'react'
import {
  ChevronDown,
  CircleCheck,
  CircleMinus,
  CircleX,
  Quote,
  Scale,
  ShieldAlert,
  ShieldCheck,
  TextSearch,
} from 'lucide-react'
import { similarityPercent } from '../../utils/format'

// Mirrors the component names in server/app/services/scoring.py
const COMPONENT_LABELS = {
  skills: 'Skills',
  experience: 'Experience',
  education: 'Education',
  semantic: 'Semantic similarity',
}

export const REQUIREMENT_STATUS = {
  met: { label: 'Met', tone: 'good', icon: CircleCheck },
  partial: { label: 'Partial', tone: 'warning', icon: CircleMinus },
  missing: { label: 'Missing', tone: 'critical', icon: CircleX },
}

const percent = (weight) => `${Math.round(weight * 100)}%`

export function ScoreBreakdown({ breakdown, score }) {
  return (
    <article className="card">
      <header className="card__header">
        <div>
          <h3>
            <Scale size={18} aria-hidden="true" /> How the score was calculated
          </h3>
          <p className="text-secondary">
            Computed in code from the verified requirements below, not guessed by the model.
          </p>
        </div>
        <span className="breakdown__total" aria-label={`Final score ${score} out of 100`}>
          {score}
          <span>/100</span>
        </span>
      </header>
      <ul className="breakdown">
        {breakdown.components.map((part) => {
          const measured = part.score !== null && part.score !== undefined
          const reweighted = measured && Math.abs(part.effective_weight - part.weight) >= 0.005
          return (
            <li key={part.name} className={`breakdown__row ${measured ? '' : 'is-unmeasured'}`}>
              <div className="breakdown__head">
                <span className="breakdown__name">{COMPONENT_LABELS[part.name] || part.name}</span>
                <span className="breakdown__weight">
                  {measured ? (
                    reweighted ? (
                      <>
                        weight <s>{percent(part.weight)}</s> {percent(part.effective_weight)}
                      </>
                    ) : (
                      <>weight {percent(part.effective_weight)}</>
                    )
                  ) : (
                    'not counted'
                  )}
                </span>
                <strong className="breakdown__score">{measured ? Math.round(part.score) : '—'}</strong>
              </div>
              <div
                className="breakdown__bar"
                role="img"
                aria-label={measured ? `${COMPONENT_LABELS[part.name]}: ${Math.round(part.score)} of 100` : 'Not measured'}
              >
                {measured && <span style={{ width: `${Math.max(0, Math.min(100, part.score))}%` }} />}
              </div>
              <p className="breakdown__detail">{part.detail}</p>
            </li>
          )
        })}
      </ul>
      <p className="breakdown__method">{breakdown.method}</p>
    </article>
  )
}

const FILTERS = ['all', 'met', 'partial', 'missing']

export function RequirementsList({ requirements }) {
  const [filter, setFilter] = useState('all')
  const counts = useMemo(() => {
    const result = { all: requirements.length, met: 0, partial: 0, missing: 0 }
    requirements.forEach((item) => {
      result[item.status] += 1
    })
    return result
  }, [requirements])
  const visible = filter === 'all' ? requirements : requirements.filter((item) => item.status === filter)
  const downgraded = requirements.filter((item) => item.model_status !== item.status).length

  return (
    <article className="card">
      <header className="card__header card__header--wrap">
        <div>
          <h3>
            <Quote size={18} aria-hidden="true" /> Requirements and evidence
          </h3>
          <p className="text-secondary">
            Each job requirement, judged against a verbatim quote from the resume.
            {downgraded > 0 &&
              ` ${downgraded} verdict${downgraded === 1 ? ' was' : 's were'} downgraded because the quote could not be found in the resume.`}
          </p>
        </div>
        <div className="segmented" role="tablist" aria-label="Filter requirements">
          {FILTERS.map((key) => (
            <button
              key={key}
              role="tab"
              aria-selected={filter === key}
              className={filter === key ? 'is-active' : ''}
              onClick={() => setFilter(key)}
              disabled={key !== 'all' && counts[key] === 0}
            >
              {key === 'all' ? 'All' : REQUIREMENT_STATUS[key].label} <span className="segmented__count">{counts[key]}</span>
            </button>
          ))}
        </div>
      </header>

      {!requirements.length ? (
        <p className="text-muted">No requirements were identified in this job description.</p>
      ) : (
        <ul className="requirements">
          {visible.map((item, index) => {
            const status = REQUIREMENT_STATUS[item.status]
            const StatusIcon = status.icon
            const wasDowngraded = item.model_status !== item.status
            return (
              <li key={`${index}-${item.requirement}`} className="requirement">
                <div className="requirement__head">
                  <span className={`status-pill status-pill--${status.tone}`}>
                    <StatusIcon size={14} aria-hidden="true" /> {status.label}
                  </span>
                  <span className="requirement__title">{item.requirement}</span>
                  <span className="requirement__tags">
                    <span className="tag">{item.category}</span>
                    <span className={`tag ${item.importance === 'required' ? 'tag--strong' : ''}`}>{item.importance}</span>
                  </span>
                </div>
                {item.evidence ? (
                  <blockquote className="requirement__evidence">“{item.evidence}”</blockquote>
                ) : (
                  <p className="requirement__none">No supporting evidence in the resume.</p>
                )}
                {item.evidence && (
                  <p className={`requirement__check ${item.evidence_verified ? 'is-verified' : 'is-unverified'}`}>
                    {item.evidence_verified ? (
                      <>
                        <ShieldCheck size={14} aria-hidden="true" /> Quote found in the resume
                      </>
                    ) : (
                      <>
                        <ShieldAlert size={14} aria-hidden="true" /> Quote not found in the resume
                        {wasDowngraded && ` — downgraded from ${REQUIREMENT_STATUS[item.model_status].label.toLowerCase()}`}
                      </>
                    )}
                  </p>
                )}
              </li>
            )
          })}
        </ul>
      )}
    </article>
  )
}

export function RetrievedEvidence({ passages, similarity }) {
  return (
    <details className="insight insight--accent">
      <summary>
        <span className="insight__icon">
          <TextSearch size={16} aria-hidden="true" />
        </span>
        <span className="insight__title">
          Resume passages retrieved for this job
          {similarity != null && (
            <span className="insight__subtitle">Average similarity {similarityPercent(similarity)}%</span>
          )}
        </span>
        <span className="count-badge">{passages.length}</span>
        <ChevronDown size={18} className="insight__chevron" aria-hidden="true" />
      </summary>
      {passages.length ? (
        <ol className="passages">
          {passages.map((passage) => (
            <li key={passage.chunk_index} className="passage">
              <div className="passage__meta">
                <span>Chunk {passage.chunk_index + 1}</span>
                <span>{similarityPercent(passage.score)}% similar</span>
              </div>
              <p>{passage.content}</p>
            </li>
          ))}
        </ol>
      ) : (
        <p className="insight__empty">No passages were retrieved.</p>
      )}
    </details>
  )
}
