import { useEffect, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { BarChart3, Building2, FileText, PenLine, RefreshCw, Sparkles, Target } from 'lucide-react'
import { recommendationsApi, resumesApi } from '../api/services'
import { useApi } from '../hooks/useApi'
import { PageHeader } from '../components/ui/PageHeader'
import { SelectField } from '../components/ui/Field'
import { EmptyState, ErrorState, InlineError, Skeleton } from '../components/ui/States'
import { BriefcaseIllustration, DocumentIllustration } from '../components/ui/Illustrations'
import { scoreBand, similarityPercent } from '../utils/format'

// Upper bound accepted by GET /recommendations/jobs
const MATCH_LIMIT = 50

function MatchCard({ match, rank, resumeId }) {
  const band = scoreBand(match.match_score)
  return (
    <article className="card match-card">
      <header className="match-card__header">
        <span className="match-card__rank" aria-label={`Rank ${rank}`}>
          {rank}
        </span>
        <div className="match-card__title">
          <h2>{match.title}</h2>
          <p>
            <Building2 size={14} aria-hidden="true" /> {match.company}
          </p>
        </div>
        <div className="match-card__score">
          <span className={`score-badge score-badge--${band.key}`} title={band.label}>
            {match.match_score}
          </span>
          <span className="match-card__similarity">{similarityPercent(match.similarity)}% similar</span>
        </div>
      </header>

      <p className="match-card__reason">{match.reason}</p>

      <div className="match-card__passages">
        <figure className="passage-pair">
          <figcaption>
            <FileText size={13} aria-hidden="true" /> From your resume
          </figcaption>
          <blockquote>{match.resume_passage}</blockquote>
        </figure>
        <figure className="passage-pair">
          <figcaption>
            <Target size={13} aria-hidden="true" /> Closest part of the job
          </figcaption>
          <blockquote>{match.job_passage}</blockquote>
        </figure>
      </div>

      <footer className="match-card__actions">
        {match.analysis_id ? (
          <Link to={`/analysis?id=${match.analysis_id}`} className="btn btn--secondary btn--sm">
            <BarChart3 size={15} aria-hidden="true" /> View full analysis ({match.analysis_score})
          </Link>
        ) : (
          <Link to={`/analysis?resume=${resumeId}&job=${match.job_id}`} className="btn btn--primary btn--sm">
            <Sparkles size={15} aria-hidden="true" /> Run full analysis
          </Link>
        )}
        <Link to={`/rewrite?resume=${resumeId}&job=${match.job_id}`} className="btn btn--ghost btn--sm">
          <PenLine size={15} aria-hidden="true" /> Tailor resume
        </Link>
      </footer>
    </article>
  )
}

export function JobMatchesPage() {
  const [params, setParams] = useSearchParams()
  const resumes = useApi((signal) => resumesApi.list({ signal }))
  const [resumeId, setResumeId] = useState(params.get('resume') || '')

  // Default to the newest resume, and drop a selection that no longer exists.
  useEffect(() => {
    if (!resumes.data?.length) return
    if (!resumeId || !resumes.data.some((resume) => String(resume.id) === resumeId)) {
      setResumeId(String(resumes.data[0].id))
    }
  }, [resumes.data, resumeId])

  const matches = useApi(
    (signal) => (resumeId ? recommendationsApi.jobs({ resumeId: Number(resumeId), limit: MATCH_LIMIT }, { signal }) : Promise.resolve(null)),
    [resumeId],
  )

  const selectResume = (event) => {
    setResumeId(event.target.value)
    setParams({ resume: event.target.value }, { replace: true })
  }

  const data = matches.data
  const waiting = resumes.loading || (resumeId && !data && !matches.error)
  const unindexed = data?.unindexed_job_ids?.length || 0

  return (
    <>
      <PageHeader
        eyebrow="Recommendations"
        title="Job matches"
        description="Your saved jobs ranked by how closely they match a resume, using semantic similarity between their passages."
        actions={
          resumeId && (
            <button className="btn btn--secondary" onClick={matches.reload} disabled={matches.loading || matches.refreshing}>
              <RefreshCw size={16} className={matches.refreshing ? 'is-spinning' : ''} aria-hidden="true" /> Refresh
            </button>
          )
        }
      />

      <section className="card matches-toolbar">
        <SelectField
          label="Resume"
          value={resumeId}
          onChange={selectResume}
          disabled={resumes.loading || !resumes.data?.length}
        >
          {resumes.loading && <option value="">Loading…</option>}
          {!resumes.loading && !resumes.data?.length && <option value="">No resumes yet</option>}
          {(resumes.data || []).map((resume) => (
            <option key={resume.id} value={resume.id}>
              {resume.filename}
            </option>
          ))}
        </SelectField>
        <p className="text-secondary matches-toolbar__hint">
          The score rescales similarity to 0–100. Run a full analysis for an evidence-based score.
        </p>
      </section>
      {resumes.error && <InlineError>{resumes.error.message}</InlineError>}

      {!resumes.loading && !resumes.error && !resumes.data?.length ? (
        <div className="card">
          <EmptyState
            illustration={DocumentIllustration}
            title="Upload a resume first"
            description="Job matches rank your saved jobs against one of your resumes."
            action={
              <Link to="/resumes" className="btn btn--primary">
                Upload a resume
              </Link>
            }
          />
        </div>
      ) : waiting ? (
        <div className="stack" aria-busy="true" aria-label="Ranking jobs">
          {Array.from({ length: 3 }, (_, index) => (
            <Skeleton key={index} height={220} radius={12} />
          ))}
        </div>
      ) : matches.error ? (
        <div className="card">
          <ErrorState error={matches.error} onRetry={matches.reload} title="Could not rank your jobs" />
        </div>
      ) : !data?.recommendations.length ? (
        <div className="card">
          <EmptyState
            illustration={BriefcaseIllustration}
            title={unindexed ? 'Your jobs could not be indexed' : 'No saved jobs to rank'}
            description={
              unindexed
                ? 'The embedding service is unavailable right now. Try again in a minute.'
                : 'Save job descriptions and they will be ranked here automatically.'
            }
            action={
              !unindexed && (
                <Link to="/jobs" className="btn btn--primary">
                  Add a job description
                </Link>
              )
            }
          />
        </div>
      ) : (
        <div className={`stack ${matches.refreshing ? 'is-refreshing' : ''}`}>
          {unindexed > 0 && (
            <p className="notice notice--info">
              {unindexed} job{unindexed === 1 ? ' is' : 's are'} missing from this list because {unindexed === 1 ? 'it' : 'they'}{' '}
              could not be indexed right now. Refresh to try again.
            </p>
          )}
          {data.recommendations.map((match, index) => (
            <MatchCard key={match.job_id} match={match} rank={index + 1} resumeId={data.resume_id} />
          ))}
        </div>
      )}
    </>
  )
}
