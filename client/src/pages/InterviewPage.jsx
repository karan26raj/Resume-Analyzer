import { useEffect, useMemo, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import {
  AlertTriangle,
  BookOpen,
  ChevronDown,
  Cpu,
  EyeOff,
  Eye,
  FileText,
  MessagesSquare,
  RotateCcw,
  ShieldCheck,
} from 'lucide-react'
import { interviewApi, jobsApi, resumesApi } from '../api/services'
import { useApi } from '../hooks/useApi'
import { PageHeader } from '../components/ui/PageHeader'
import { SelectField } from '../components/ui/Field'
import { EmptyState, InlineError, Spinner } from '../components/ui/States'
import { ChatIllustration } from '../components/ui/Illustrations'
import { formatNumber } from '../utils/format'

const SOURCE = {
  both: { label: 'In the job and your résumé', tone: 'good' },
  job: { label: 'Not on your résumé — prepare for it', tone: 'warning' },
  resume: { label: 'From your résumé', tone: 'neutral' },
}

const TYPE_LABELS = {
  conceptual: 'Conceptual',
  practical: 'Practical',
  scenario: 'Scenario',
  experience: 'Your experience',
}

function QuestionItem({ item, number, showGuides }) {
  return (
    <li className="interview-question">
      <div className="interview-question__head">
        <span className="interview-question__number" aria-hidden="true">
          {number}
        </span>
        <div className="interview-question__body">
          <p className="interview-question__text">{item.question}</p>
          <div className="interview-question__tags">
            <span className={`tag difficulty difficulty--${item.difficulty}`}>{item.difficulty}</span>
            <span className="tag">{TYPE_LABELS[item.type] || item.type}</span>
          </div>
          {item.resume_evidence && (
            <blockquote className="interview-question__evidence">
              <FileText size={13} aria-hidden="true" /> “{item.resume_evidence}”
            </blockquote>
          )}
          <details key={String(showGuides)} className="answer-guide" open={showGuides}>
            <summary>
              <BookOpen size={14} aria-hidden="true" /> Answer guide
              <ChevronDown size={15} className="answer-guide__chevron" aria-hidden="true" />
            </summary>
            {item.what_they_assess && (
              <p className="answer-guide__assess">
                <strong>What they&apos;re looking for:</strong> {item.what_they_assess}
              </p>
            )}
            {item.answer_tips.length > 0 && (
              <ul className="answer-guide__tips">
                {item.answer_tips.map((tip, index) => (
                  <li key={`${index}-${tip}`}>{tip}</li>
                ))}
              </ul>
            )}
          </details>
        </div>
      </div>
    </li>
  )
}

function TechnologySection({ group, index, showGuides }) {
  const source = SOURCE[group.source] || SOURCE.both
  return (
    <section className="card interview-tech" id={`tech-${index}`} aria-labelledby={`tech-${index}-title`}>
      <header className="interview-tech__header">
        <div>
          <h2 id={`tech-${index}-title`}>{group.technology}</h2>
          <span className={`status-pill status-pill--${source.tone}`}>
            {group.source === 'job' && <AlertTriangle size={13} aria-hidden="true" />}
            {source.label}
          </span>
        </div>
        <span className="count-badge">{group.questions.length} questions</span>
      </header>
      <ol className="interview-questions">
        {group.questions.map((item, questionIndex) => (
          <QuestionItem key={`${questionIndex}-${item.question}`} item={item} number={questionIndex + 1} showGuides={showGuides} />
        ))}
      </ol>
    </section>
  )
}

export function InterviewPage() {
  const [params] = useSearchParams()
  const resumes = useApi((signal) => resumesApi.list({ signal }))
  const jobs = useApi((signal) => jobsApi.list({ signal }))
  const [resumeId, setResumeId] = useState(params.get('resume') || '')
  const [jobId, setJobId] = useState(params.get('job') || '')
  const [running, setRunning] = useState(false)
  const [error, setError] = useState(null)
  const [result, setResult] = useState(null)
  const [showGuides, setShowGuides] = useState(false)

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
      setResult(await interviewApi.questions(Number(targetResumeId), Number(targetJobId), options))
      setShowGuides(false)
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
  const questionCount = useMemo(
    () => (result ? result.technologies.reduce((total, group) => total + group.questions.length, 0) : 0),
    [result],
  )

  return (
    <>
      <PageHeader
        eyebrow="Interview prep"
        title="Interview coach"
        description="Likely interview questions for a job, grouped by technology, with a guide to what a strong answer covers."
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
            {running ? <Spinner size={16} /> : <MessagesSquare size={18} />} {running ? 'Preparing…' : 'Get questions'}
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
            <MessagesSquare size={24} />
          </div>
          <h2>Preparing your interview questions</h2>
          <p className="text-secondary">
            Picking the technologies this job cares about and writing 4–5 questions for each, then checking every
            technology and résumé quote against your documents. This usually takes 10–40 seconds.
          </p>
        </section>
      ) : result ? (
        <div className="interview-result">
          <div className="rewrite-summary">
            <p>
              <strong>{questionCount}</strong> questions across <strong>{result.technologies.length}</strong>{' '}
              technolog{result.technologies.length === 1 ? 'y' : 'ies'} for{' '}
              <strong>{resultJob ? `${resultJob.title} · ${resultJob.company}` : `Job #${result.job_id}`}</strong>, based on{' '}
              <strong>{resultResume?.filename || `Resume #${result.resume_id}`}</strong>
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
                <ShieldCheck size={13} aria-hidden="true" /> Checked against your documents
              </span>
            </p>
          </div>

          {result.cached ? (
            <p className="notice notice--info notice--row">
              <span>These are the questions you generated earlier for this pair — no new AI call was made.</span>
              <button
                className="btn btn--secondary btn--sm"
                onClick={() => request(result.resume_id, result.job_id, { force: true })}
              >
                <RotateCcw size={15} aria-hidden="true" /> Generate new questions
              </button>
            </p>
          ) : (
            <p className="notice notice--info">
              Try answering each question out loud before opening its answer guide. Questions are kept for 24 hours.
            </p>
          )}

          <div className="interview-toolbar">
            <nav className="interview-jump" aria-label="Jump to a technology">
              {result.technologies.map((group, index) => (
                <a key={group.technology} href={`#tech-${index}`} className={`suggestion-chip interview-jump__${group.source}`}>
                  {group.technology}
                </a>
              ))}
            </nav>
            <button className="btn btn--ghost btn--sm" onClick={() => setShowGuides((value) => !value)}>
              {showGuides ? <EyeOff size={15} aria-hidden="true" /> : <Eye size={15} aria-hidden="true" />}
              {showGuides ? 'Hide all answer guides' : 'Show all answer guides'}
            </button>
          </div>

          {result.technologies.map((group, index) => (
            <TechnologySection key={group.technology} group={group} index={index} showGuides={showGuides} />
          ))}

          {result.skipped.length > 0 && (
            <details className="insight insight--accent">
              <summary>
                <span className="insight__icon">
                  <ShieldCheck size={16} aria-hidden="true" />
                </span>
                <span className="insight__title">
                  Left out after checking
                  <span className="insight__subtitle">Technologies the check couldn&apos;t confirm in your documents.</span>
                </span>
                <span className="count-badge">{result.skipped.length}</span>
                <ChevronDown size={18} className="insight__chevron" aria-hidden="true" />
              </summary>
              <ul className="insight__list">
                {result.skipped.map((item, index) => (
                  <li key={`${index}-${item.technology}`}>
                    <strong>{item.technology}</strong> — {item.reason}
                  </li>
                ))}
              </ul>
            </details>
          )}
        </div>
      ) : (
        <div className="card">
          <EmptyState
            illustration={ChatIllustration}
            title="Practise for your next interview"
            description="Choose a resume and a target job. You'll get 4–5 likely questions for each technology the job cares about — including the ones missing from your resume — with a guide to what a strong answer covers."
          />
        </div>
      )}
    </>
  )
}
