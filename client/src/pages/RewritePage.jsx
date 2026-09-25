import { useEffect, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { ArrowDown, Check, ChevronDown, Copy, Cpu, PenLine, RotateCcw, ShieldAlert, ShieldCheck } from 'lucide-react'
import { jobsApi, resumesApi } from '../api/services'
import { useApi } from '../hooks/useApi'
import { useToast } from '../components/ui/Toast'
import { PageHeader } from '../components/ui/PageHeader'
import { SelectField } from '../components/ui/Field'
import { EmptyState, InlineError, Spinner } from '../components/ui/States'
import { DocumentIllustration } from '../components/ui/Illustrations'
import { formatNumber } from '../utils/format'

async function copyText(text) {
  if (navigator.clipboard && window.isSecureContext) {
    await navigator.clipboard.writeText(text)
    return
  }
  const area = document.createElement('textarea')
  area.value = text
  area.setAttribute('readonly', '')
  area.style.position = 'fixed'
  area.style.opacity = '0'
  document.body.appendChild(area)
  area.select()
  const ok = document.execCommand('copy')
  area.remove()
  if (!ok) throw new Error('Copy is not supported in this browser')
}

function SuggestionCard({ suggestion }) {
  const toast = useToast()
  const [copied, setCopied] = useState(false)

  const copy = async () => {
    try {
      await copyText(suggestion.rewritten)
      setCopied(true)
      setTimeout(() => setCopied(false), 1600)
    } catch (error) {
      toast.error(error.message)
    }
  }

  return (
    <article className="card rewrite-card">
      <header className="rewrite-card__header">
        {suggestion.section && <span className="tag">{suggestion.section}</span>}
        <button className="btn btn--ghost btn--sm" onClick={copy} aria-label="Copy rewritten line">
          {copied ? <Check size={15} aria-hidden="true" /> : <Copy size={15} aria-hidden="true" />}
          {copied ? 'Copied' : 'Copy'}
        </button>
      </header>
      <div className="rewrite-card__diff">
        <div className="rewrite-card__line rewrite-card__line--original">
          <span className="rewrite-card__label">Current</span>
          <p>{suggestion.original}</p>
        </div>
        <ArrowDown size={16} className="rewrite-card__arrow" aria-hidden="true" />
        <div className="rewrite-card__line rewrite-card__line--new">
          <span className="rewrite-card__label">Suggested</span>
          <p>{suggestion.rewritten}</p>
        </div>
      </div>
      {suggestion.rationale && <p className="rewrite-card__rationale">{suggestion.rationale}</p>}
    </article>
  )
}

function RejectedList({ rejected }) {
  return (
    <details className="insight insight--critical">
      <summary>
        <span className="insight__icon">
          <ShieldAlert size={16} aria-hidden="true" />
        </span>
        <span className="insight__title">
          Blocked suggestions
          <span className="insight__subtitle">
            Rewrites that added something your resume doesn&apos;t contain were removed.
          </span>
        </span>
        <span className="count-badge">{rejected.length}</span>
        <ChevronDown size={18} className="insight__chevron" aria-hidden="true" />
      </summary>
      <ul className="rejected-list">
        {rejected.map((item, index) => (
          <li key={`${index}-${item.original}`} className="rejected">
            <p className="rejected__reason">{item.reason}</p>
            {item.unsupported_terms?.length > 0 && (
              <ul className="chip-list">
                {item.unsupported_terms.map((term) => (
                  <li key={term} className="chip chip--critical">
                    {term}
                  </li>
                ))}
              </ul>
            )}
            <p className="rejected__text">
              <span>Suggested:</span> {item.rewritten}
            </p>
          </li>
        ))}
      </ul>
    </details>
  )
}

export function RewritePage() {
  const [params] = useSearchParams()
  const resumes = useApi((signal) => resumesApi.list({ signal }))
  const jobs = useApi((signal) => jobsApi.list({ signal }))
  const [resumeId, setResumeId] = useState(params.get('resume') || '')
  const [jobId, setJobId] = useState(params.get('job') || '')
  const [running, setRunning] = useState(false)
  const [error, setError] = useState(null)
  const [result, setResult] = useState(null)

  useEffect(() => {
    if (resumes.data && resumeId && !resumes.data.some((resume) => String(resume.id) === resumeId)) setResumeId('')
  }, [resumes.data, resumeId])
  useEffect(() => {
    if (jobs.data && jobId && !jobs.data.some((job) => String(job.id) === jobId)) setJobId('')
  }, [jobs.data, jobId])

  const request = async (targetResumeId, targetJobId, options) => {
    setRunning(true)
    setError(null)
    try {
      setResult(await resumesApi.rewrite(Number(targetResumeId), Number(targetJobId), options))
    } catch (err) {
      setError(err.message)
    } finally {
      setRunning(false)
    }
  }

  const generate = (event) => {
    event.preventDefault()
    if (resumeId && jobId) request(resumeId, jobId)
  }

  const listsLoading = resumes.loading || jobs.loading
  const missingDocs = !listsLoading && (!resumes.data?.length || !jobs.data?.length)
  const resultJob = result && (jobs.data || []).find((job) => job.id === result.job_id)
  const resultResume = result && (resumes.data || []).find((resume) => resume.id === result.resume_id)

  return (
    <>
      <PageHeader
        eyebrow="AI writing"
        title="Resume rewrite"
        description="Rewrite existing resume lines to match a job's language. Nothing is invented: every suggestion is checked against your resume."
      />

      <section className="card analysis-runner">
        <form onSubmit={generate} className="analysis-runner__form">
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
            for
          </span>
          <SelectField
            label="Target job"
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
            {running ? <Spinner size={16} /> : <PenLine size={18} />} {running ? 'Rewriting…' : 'Suggest rewrites'}
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
        <InlineError>{error}</InlineError>
      </section>

      {running ? (
        <section className="card analyzing" aria-live="polite">
          <div className="analyzing__orb" aria-hidden="true">
            <PenLine size={24} />
          </div>
          <h2>Writing suggestions</h2>
          <p className="text-secondary">
            Gemini is rewording lines from your resume for this job, then every suggestion is checked so it adds no
            skill, number or name your resume doesn&apos;t already contain. This usually takes 5–30 seconds.
          </p>
        </section>
      ) : result ? (
        <div className="rewrite-result">
          <div className="rewrite-summary">
            <p>
              <strong>{result.suggestions.length}</strong> suggestion{result.suggestions.length === 1 ? '' : 's'} for{' '}
              <strong>{resultResume?.filename || `Resume #${result.resume_id}`}</strong> targeting{' '}
              <strong>{resultJob ? `${resultJob.title} · ${resultJob.company}` : `Job #${result.job_id}`}</strong>
            </p>
            <p className="rewrite-summary__meta">
              <span>
                <Cpu size={13} aria-hidden="true" /> {result.model}
              </span>
              {result.input_tokens != null && (
                <span>
                  {formatNumber(result.input_tokens)} in · {formatNumber(result.output_tokens)} out
                </span>
              )}
              <span>
                <ShieldCheck size={13} aria-hidden="true" /> Checked against your resume
              </span>
            </p>
          </div>
          {result.cached ? (
            <p className="notice notice--info notice--row">
              <span>These are the suggestions you generated earlier for this pair — no new AI call was made.</span>
              <button
                className="btn btn--secondary btn--sm"
                onClick={() => request(result.resume_id, result.job_id, { force: true })}
              >
                <RotateCcw size={15} aria-hidden="true" /> Generate new suggestions
              </button>
            </p>
          ) : (
            <p className="notice notice--info">
              Suggestions are kept for 24 hours, so you can come back to them. Copy the ones you want into your resume.
            </p>
          )}

          {result.suggestions.length ? (
            result.suggestions.map((suggestion, index) => (
              <SuggestionCard key={`${index}-${suggestion.original}`} suggestion={suggestion} />
            ))
          ) : (
            <div className="card">
              <EmptyState
                compact
                title="No safe rewrites found"
                description={
                  result.rejected.length
                    ? 'Every suggestion added something your resume does not contain, so they were all blocked.'
                    : 'Your resume already reads well for this job.'
                }
              />
            </div>
          )}
          {result.rejected.length > 0 && <RejectedList rejected={result.rejected} />}
        </div>
      ) : (
        <div className="card">
          <EmptyState
            illustration={DocumentIllustration}
            title="Tailor your resume to a job"
            description="Choose a resume and a target job. You'll get rewritten versions of your existing lines that use the job's wording, each with the reason for the change."
          />
        </div>
      )}
    </>
  )
}
