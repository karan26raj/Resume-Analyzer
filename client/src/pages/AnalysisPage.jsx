import { useEffect, useMemo, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import {
  AlertTriangle,
  BriefcaseBusiness,
  Check,
  ChevronDown,
  Cpu,
  FileText,
  History,
  Lightbulb,
  MessagesSquare,
  PenLine,
  RotateCcw,
  Sparkles,
  ThumbsUp,
  X,
} from 'lucide-react'
import { analysisApi, jobsApi, resumesApi } from '../api/services'
import { useApi } from '../hooks/useApi'
import { useToast } from '../components/ui/Toast'
import { PageHeader } from '../components/ui/PageHeader'
import { SelectField } from '../components/ui/Field'
import { ScoreRing } from '../components/ui/ScoreRing'
import { EmptyState, ErrorState, InlineError, Skeleton, Spinner } from '../components/ui/States'
import { ChartIllustration } from '../components/ui/Illustrations'
import { RequirementsList, RetrievedEvidence, ScoreBreakdown } from '../components/analysis/ExplainableAnalysis'
import { formatDateTime, formatNumber, formatRelative, scoreBand } from '../utils/format'

function InsightSection({ icon: Icon, title, items, tone, defaultOpen = true, emptyText }) {
  return (
    <details className={`insight insight--${tone}`} open={defaultOpen}>
      <summary>
        <span className="insight__icon">
          <Icon size={16} aria-hidden="true" />
        </span>
        <span className="insight__title">{title}</span>
        <span className="count-badge">{items.length}</span>
        <ChevronDown size={18} className="insight__chevron" aria-hidden="true" />
      </summary>
      {items.length ? (
        <ul className="insight__list">
          {items.map((item, index) => (
            <li key={`${index}-${item}`}>{item}</li>
          ))}
        </ul>
      ) : (
        <p className="insight__empty">{emptyText}</p>
      )}
    </details>
  )
}

function SkillCoverage({ matched, missing }) {
  const total = matched + missing
  if (!total) return null
  const percent = Math.round((matched / total) * 100)
  return (
    <div className="coverage">
      <div className="coverage__header">
        <span>Skill coverage</span>
        <strong>{percent}%</strong>
      </div>
      <div className="coverage__bar" role="img" aria-label={`${matched} of ${total} identified skills matched`}>
        {matched > 0 && <span className="coverage__matched" style={{ flexGrow: matched }} />}
        {missing > 0 && <span className="coverage__missing" style={{ flexGrow: missing }} />}
      </div>
      <div className="coverage__legend">
        <span>
          <span className="legend-swatch legend-swatch--good" aria-hidden="true" /> {matched} matched
        </span>
        <span>
          <span className="legend-swatch legend-swatch--critical" aria-hidden="true" /> {missing} missing
        </span>
      </div>
    </div>
  )
}

function AnalysisResult({ analysis, resumeName, job, fromCache, onRerun, rerunDisabled }) {
  const band = scoreBand(analysis.match_score)
  const explainable = Boolean(analysis.score_breakdown && analysis.requirements)
  return (
    <div className="analysis-result">
      {fromCache && (
        <p className="notice notice--info notice--row">
          <span>
            You already analyzed this pair {formatRelative(analysis.created_at)}, so this is that result — no new AI
            call was made.
          </span>
          <button className="btn btn--secondary btn--sm" onClick={onRerun} disabled={rerunDisabled}>
            <RotateCcw size={15} aria-hidden="true" /> Run a fresh analysis
          </button>
        </p>
      )}
      <section className={`card score-hero score-hero--${band.key}`}>
        <div className="score-hero__ring">
          <ScoreRing key={analysis.id} score={analysis.match_score} size={210} />
        </div>
        <div className="score-hero__details">
          <p className="page-header__eyebrow">Match result</p>
          <h2 className="score-hero__title">
            <span>
              <FileText size={18} aria-hidden="true" /> {resumeName}
            </span>
            <span className="score-hero__vs">vs</span>
            <span>
              <BriefcaseBusiness size={18} aria-hidden="true" /> {job ? `${job.title} · ${job.company}` : `Job #${analysis.job_id}`}
            </span>
          </h2>
          <SkillCoverage matched={analysis.matched_skills.length} missing={analysis.missing_skills.length} />
          <dl className="meta-list">
            <div>
              <dt>
                <Cpu size={14} aria-hidden="true" /> Model
              </dt>
              <dd>{analysis.model}</dd>
            </div>
            <div>
              <dt>Tokens</dt>
              <dd>
                {analysis.input_tokens != null
                  ? `${formatNumber(analysis.input_tokens)} in · ${formatNumber(analysis.output_tokens)} out`
                  : 'Not reported'}
              </dd>
            </div>
            <div>
              <dt>Analyzed</dt>
              <dd>{formatDateTime(analysis.created_at)}</dd>
            </div>
          </dl>
          <div className="score-hero__actions">
            <Link
              to={`/rewrite?resume=${analysis.resume_id}&job=${analysis.job_id}`}
              className="btn btn--secondary btn--sm"
            >
              <PenLine size={15} aria-hidden="true" /> Tailor resume for this job
            </Link>
            <Link
              to={`/interview?resume=${analysis.resume_id}&job=${analysis.job_id}`}
              className="btn btn--secondary btn--sm"
            >
              <MessagesSquare size={15} aria-hidden="true" /> Prepare for the interview
            </Link>
          </div>
        </div>
      </section>

      {explainable ? (
        <>
          <ScoreBreakdown breakdown={analysis.score_breakdown} score={analysis.match_score} />
          <RequirementsList requirements={analysis.requirements} />
        </>
      ) : (
        <p className="notice notice--info notice--row">
          <span>
            This analysis was created before evidence-based scoring, so it has no score breakdown or requirement
            evidence. Run it again to get them.
          </span>
          <button className="btn btn--secondary btn--sm" onClick={onRerun} disabled={rerunDisabled}>
            <RotateCcw size={15} aria-hidden="true" /> Run again
          </button>
        </p>
      )}

      <section className="skills-grid">
        <article className="card">
          <header className="card__header">
            <h3>
              <Check size={18} className="icon-good" aria-hidden="true" /> Matched skills
            </h3>
            <span className="count-badge">{analysis.matched_skills.length}</span>
          </header>
          {analysis.matched_skills.length ? (
            <ul className="chip-list">
              {analysis.matched_skills.map((skill, index) => (
                <li key={`${index}-${skill}`} className="chip chip--good">
                  <Check size={13} aria-hidden="true" /> {skill}
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-muted">No matching skills were identified.</p>
          )}
        </article>
        <article className="card">
          <header className="card__header">
            <h3>
              <X size={18} className="icon-critical" aria-hidden="true" /> Missing skills
            </h3>
            <span className="count-badge">{analysis.missing_skills.length}</span>
          </header>
          {analysis.missing_skills.length ? (
            <ul className="chip-list">
              {analysis.missing_skills.map((skill, index) => (
                <li key={`${index}-${skill}`} className="chip chip--critical">
                  <X size={13} aria-hidden="true" /> {skill}
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-muted">No missing skills — the resume covers every identified requirement.</p>
          )}
        </article>
      </section>

      <section className="insights">
        <InsightSection
          icon={ThumbsUp}
          title="Strengths"
          tone="good"
          items={analysis.strengths}
          emptyText="No specific strengths were listed."
        />
        <InsightSection
          icon={AlertTriangle}
          title="Weaknesses"
          tone="critical"
          items={analysis.weaknesses}
          emptyText="No evidence-based weaknesses were found."
        />
        <InsightSection
          icon={Lightbulb}
          title="Recommendations"
          tone="accent"
          items={analysis.recommendations}
          emptyText="No recommendations were returned."
        />
        {analysis.retrieved_evidence && (
          <RetrievedEvidence passages={analysis.retrieved_evidence} similarity={analysis.semantic_similarity} />
        )}
      </section>
    </div>
  )
}

export function AnalysisPage() {
  const toast = useToast()
  const [params, setParams] = useSearchParams()
  const resumes = useApi((signal) => resumesApi.list({ signal }))
  const jobs = useApi((signal) => jobsApi.list({ signal }))
  const history = useApi((signal) => analysisApi.list(undefined, { signal }))

  const [resumeId, setResumeId] = useState(params.get('resume') || '')
  const [jobId, setJobId] = useState(params.get('job') || '')
  const [running, setRunning] = useState(false)
  const [runError, setRunError] = useState(null)
  const [cachedId, setCachedId] = useState(null)
  const selectedId = Number(params.get('id')) || null

  const resumeNames = useMemo(() => new Map((resumes.data || []).map((resume) => [resume.id, resume.filename])), [resumes.data])
  const jobsById = useMemo(() => new Map((jobs.data || []).map((job) => [job.id, job])), [jobs.data])

  const selected = useMemo(() => {
    const list = history.data || []
    return (selectedId && list.find((item) => item.id === selectedId)) || (!selectedId ? list[0] : null) || null
  }, [history.data, selectedId])

  useEffect(() => {
    if (resumes.data && resumeId && !resumes.data.some((resume) => String(resume.id) === resumeId)) setResumeId('')
  }, [resumes.data, resumeId])
  useEffect(() => {
    if (jobs.data && jobId && !jobs.data.some((job) => String(job.id) === jobId)) setJobId('')
  }, [jobs.data, jobId])

  const analyze = async (targetResumeId, targetJobId, options) => {
    setRunning(true)
    setRunError(null)
    try {
      const result = await analysisApi.match(Number(targetResumeId), Number(targetJobId), options)
      if (result.cached) {
        setCachedId(result.id)
        toast.info(`Showing your recent analysis — score ${result.match_score}`)
      } else {
        setCachedId(null)
        history.setData((current) => [result, ...(current || []).filter((item) => item.id !== result.id)])
        toast.success(`Analysis complete — score ${result.match_score}`)
      }
      setParams({ id: String(result.id) })
    } catch (error) {
      setRunError(error.message)
    } finally {
      setRunning(false)
    }
  }

  const run = (event) => {
    event.preventDefault()
    if (resumeId && jobId) analyze(resumeId, jobId)
  }

  const rerun = (analysis) => {
    setResumeId(String(analysis.resume_id))
    setJobId(String(analysis.job_id))
    analyze(analysis.resume_id, analysis.job_id, { force: true })
  }

  const listsLoading = resumes.loading || jobs.loading
  const missingDocs = !listsLoading && (!resumes.data?.length || !jobs.data?.length)

  return (
    <>
      <PageHeader
        eyebrow="AI analysis"
        title="Resume vs job match"
        description="Compare a resume with a job description to get a structured, evidence-based match report."
      />

      <section className="card card--glass analysis-runner">
        <form onSubmit={run} className="analysis-runner__form">
          <SelectField
            label="Resume"
            value={resumeId}
            onChange={(event) => setResumeId(event.target.value)}
            disabled={listsLoading || running}
          >
            <option value="">{resumes.loading ? 'Loading…' : 'Choose a resume'}</option>
            {(resumes.data || []).map((resume) => (
              <option key={resume.id} value={resume.id}>
                {resume.filename}
              </option>
            ))}
          </SelectField>
          <span className="analysis-runner__vs" aria-hidden="true">
            vs
          </span>
          <SelectField
            label="Job description"
            value={jobId}
            onChange={(event) => setJobId(event.target.value)}
            disabled={listsLoading || running}
          >
            <option value="">{jobs.loading ? 'Loading…' : 'Choose a job'}</option>
            {(jobs.data || []).map((job) => (
              <option key={job.id} value={job.id}>
                {job.title} · {job.company}
              </option>
            ))}
          </SelectField>
          <button type="submit" className="btn btn--primary btn--lg" disabled={!resumeId || !jobId || running}>
            {running ? <Spinner size={16} /> : <Sparkles size={18} />} {running ? 'Analyzing…' : 'Run analysis'}
          </button>
        </form>
        {(resumes.error || jobs.error) && <InlineError>{(resumes.error || jobs.error).message}</InlineError>}
        {missingDocs && !resumes.error && !jobs.error && (
          <p className="notice notice--info">
            You need at least one resume and one job.{' '}
            {!resumes.data?.length && <Link to="/resumes">Upload a resume</Link>}
            {!resumes.data?.length && !jobs.data?.length && ' and '}
            {!jobs.data?.length && <Link to="/jobs">add a job description</Link>}.
          </p>
        )}
        <InlineError>{runError}</InlineError>
      </section>

      <div className="analysis-layout">
        <div className="analysis-layout__main">
          {running ? (
            <section className="card analyzing" aria-live="polite">
              <div className="analyzing__orb" aria-hidden="true">
                <Sparkles size={26} />
              </div>
              <h2>Analyzing with Gemini</h2>
              <p className="text-secondary">
                Retrieving the most relevant resume passages, checking every job requirement against them and
                verifying the quoted evidence. This usually takes 5–30 seconds, longer if the primary model is busy
                and a fallback model is used.
              </p>
            </section>
          ) : history.loading ? (
            <div className="stack">
              <Skeleton height={260} radius={20} />
              <Skeleton height={160} radius={20} />
            </div>
          ) : history.error ? (
            <div className="card">
              <ErrorState error={history.error} onRetry={history.reload} />
            </div>
          ) : selected ? (
            <AnalysisResult
              analysis={selected}
              resumeName={resumeNames.get(selected.resume_id) || `Resume #${selected.resume_id}`}
              job={jobsById.get(selected.job_id)}
              fromCache={selected.id === cachedId}
              onRerun={() => rerun(selected)}
              rerunDisabled={running}
            />
          ) : (
            <div className="card">
              <EmptyState
                illustration={ChartIllustration}
                title={selectedId ? 'Analysis not found' : 'No analyses yet'}
                description={
                  selectedId
                    ? 'It may have been deleted together with its resume or job.'
                    : 'Choose a resume and a job above, then run your first analysis.'
                }
              />
            </div>
          )}
        </div>

        <aside className="card analysis-history" aria-label="Analysis history">
          <header className="card__header">
            <h2>
              <History size={18} aria-hidden="true" /> History
            </h2>
            {history.data && <span className="count-badge">{history.data.length}</span>}
          </header>
          {history.loading ? (
            <div className="stack-sm">
              {Array.from({ length: 4 }, (_, index) => (
                <Skeleton key={index} height={56} />
              ))}
            </div>
          ) : history.error ? (
            <ErrorState compact error={history.error} onRetry={history.reload} />
          ) : !history.data.length ? (
            <p className="text-muted">Past analyses will be listed here.</p>
          ) : (
            <ul className="history-list">
              {history.data.map((item) => {
                const band = scoreBand(item.match_score)
                const job = jobsById.get(item.job_id)
                return (
                  <li key={item.id}>
                    <button
                      className={`history-item ${selected?.id === item.id ? 'is-active' : ''}`}
                      onClick={() => setParams({ id: String(item.id) })}
                    >
                      <span className={`score-badge score-badge--${band.key}`} title={band.label}>
                        {item.match_score}
                      </span>
                      <span className="history-item__body">
                        <span className="history-item__title">
                          {job ? job.title : `Job #${item.job_id}`}
                        </span>
                        <span className="history-item__sub">
                          {resumeNames.get(item.resume_id) || `Resume #${item.resume_id}`}
                        </span>
                      </span>
                      <span className="history-item__time">{formatRelative(item.created_at)}</span>
                    </button>
                  </li>
                )
              })}
            </ul>
          )}
        </aside>
      </div>
    </>
  )
}
