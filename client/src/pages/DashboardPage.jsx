import { useMemo } from 'react'
import { Link } from 'react-router-dom'
import {
  ArrowUpRight,
  BarChart3,
  Bot,
  BriefcaseBusiness,
  Database,
  FileText,
  Sparkles,
  Target,
  Upload,
} from 'lucide-react'
import { analysisApi, jobsApi, recommendationsApi, resumesApi } from '../api/services'
import { useAuth } from '../auth/AuthContext'
import { useApi } from '../hooks/useApi'
import { usePollWhile } from '../hooks/usePollWhile'
import { isIndexing } from '../components/ui/IndexStatusBadge'
import { PageHeader } from '../components/ui/PageHeader'
import { EmptyState, ErrorState, Skeleton } from '../components/ui/States'
import { ChartIllustration, SearchIllustration } from '../components/ui/Illustrations'
import { ScoreTrendChart } from '../components/charts/ScoreTrendChart'
import { SkillGapChart } from '../components/charts/SkillGapChart'
import { countAnsweredQuestions } from '../utils/chatHistory'
import { formatNumber, formatRelative, parseApiDate, scoreBand } from '../utils/format'

function StatCard({ icon: Icon, label, value, loading, error, note, to, accent }) {
  const content = (
    <>
      <div className="stat-card__top">
        <span className={`stat-card__icon stat-card__icon--${accent}`}>
          <Icon size={18} aria-hidden="true" />
        </span>
        {to && <ArrowUpRight size={16} className="stat-card__arrow" aria-hidden="true" />}
      </div>
      <p className="stat-card__label">{label}</p>
      {loading ? (
        <Skeleton height={34} width="45%" />
      ) : (
        <p className="stat-card__value">{error ? '—' : value}</p>
      )}
      <p className="stat-card__note">{error ? 'Could not load' : note}</p>
    </>
  )
  return to ? (
    <Link to={to} className="card stat-card stat-card--link">
      {content}
    </Link>
  ) : (
    <div className="card stat-card">{content}</div>
  )
}

const ACTIVITY_META = {
  resume: { icon: FileText, verb: 'Uploaded resume', to: '/resumes' },
  job: { icon: BriefcaseBusiness, verb: 'Saved job', to: '/jobs' },
  analysis: { icon: BarChart3, verb: 'Ran analysis', to: '/analysis' },
}

export function DashboardPage() {
  const { user } = useAuth()
  const resumes = useApi((signal) => resumesApi.list({ signal }))
  const jobs = useApi((signal) => jobsApi.list({ signal }))
  const analyses = useApi((signal) => analysisApi.list(undefined, { signal }))
  const insights = useApi((signal) => recommendationsApi.get(8, { signal }))
  const canRank = Boolean(resumes.data?.length && jobs.data?.length)
  const topMatches = useApi(
    (signal) => (canRank ? recommendationsApi.jobs({ limit: 3 }, { signal }) : Promise.resolve(null)),
    [canRank],
  )

  const answered = user ? countAnsweredQuestions(user.id) : 0

  const indexStats = useMemo(() => {
    const documents = [...(resumes.data || []), ...(jobs.data || [])]
    const count = (predicate) => documents.filter(predicate).length
    return {
      total: documents.length,
      indexed: count((document) => document.index_status === 'indexed'),
      failed: count((document) => document.index_status === 'failed'),
      inProgress: count(isIndexing),
    }
  }, [resumes.data, jobs.data])
  usePollWhile(indexStats.inProgress > 0, () => {
    resumes.reload()
    jobs.reload()
  })

  const resumeNames = useMemo(
    () => new Map((resumes.data || []).map((resume) => [resume.id, resume.filename])),
    [resumes.data],
  )
  const jobNames = useMemo(
    () => new Map((jobs.data || []).map((job) => [job.id, `${job.title} · ${job.company}`])),
    [jobs.data],
  )

  const scorePoints = useMemo(
    () =>
      [...(analyses.data || [])]
        .sort((a, b) => a.id - b.id)
        .map((analysis) => ({
          id: analysis.id,
          score: analysis.match_score,
          createdAt: analysis.created_at,
          resumeLabel: resumeNames.get(analysis.resume_id) || `Resume #${analysis.resume_id}`,
          jobLabel: jobNames.get(analysis.job_id) || `Job #${analysis.job_id}`,
        })),
    [analyses.data, resumeNames, jobNames],
  )

  const activity = useMemo(() => {
    const items = [
      ...(resumes.data || []).map((resume) => ({
        key: `resume-${resume.id}`,
        type: 'resume',
        title: resume.filename,
        date: resume.created_at,
      })),
      ...(jobs.data || []).map((job) => ({
        key: `job-${job.id}`,
        type: 'job',
        title: `${job.title} at ${job.company}`,
        date: job.created_at,
      })),
      ...(analyses.data || []).map((analysis) => ({
        key: `analysis-${analysis.id}`,
        type: 'analysis',
        title: `${resumeNames.get(analysis.resume_id) || `Resume #${analysis.resume_id}`} vs ${
          jobNames.get(analysis.job_id) || `Job #${analysis.job_id}`
        }`,
        detail: `Score ${analysis.match_score}`,
        date: analysis.created_at,
      })),
    ]
    return items
      .map((item) => ({ ...item, parsed: parseApiDate(item.date) }))
      .filter((item) => item.parsed)
      .sort((a, b) => b.parsed - a.parsed)
      .slice(0, 8)
  }, [resumes.data, jobs.data, analyses.data, resumeNames, jobNames])

  const activityLoading = resumes.loading || jobs.loading || analyses.loading
  const activityError = resumes.error || jobs.error || analyses.error
  const isNewUser =
    !activityLoading && !activityError && !resumes.data?.length && !jobs.data?.length && !analyses.data?.length

  return (
    <>
      <PageHeader
        eyebrow="Overview"
        title="Dashboard"
        description="Your resumes, jobs and AI analyses at a glance."
        actions={
          <>
            <Link to="/resumes" className="btn btn--secondary">
              <Upload size={16} /> Upload resume
            </Link>
            <Link to="/analysis" className="btn btn--primary">
              <Sparkles size={16} /> New analysis
            </Link>
          </>
        }
      />

      <section className="stat-grid" aria-label="Key statistics">
        <StatCard
          icon={FileText}
          accent="blue"
          label="Total resumes"
          value={formatNumber(resumes.data?.length)}
          loading={resumes.loading}
          error={resumes.error}
          note="Uploaded PDF & DOCX files"
          to="/resumes"
        />
        <StatCard
          icon={BriefcaseBusiness}
          accent="cyan"
          label="Total jobs"
          value={formatNumber(jobs.data?.length)}
          loading={jobs.loading}
          error={jobs.error}
          note="Saved job descriptions"
          to="/jobs"
        />
        <StatCard
          icon={BarChart3}
          accent="purple"
          label="Total analyses"
          value={formatNumber(analyses.data?.length)}
          loading={analyses.loading}
          error={analyses.error}
          note={
            insights.data?.average_match_score != null
              ? `Average score ${insights.data.average_match_score}`
              : 'Resume vs job matches'
          }
          to="/analysis"
        />
        <StatCard
          icon={Database}
          accent="blue"
          label="Indexed documents"
          loading={resumes.loading || jobs.loading}
          error={resumes.error || jobs.error}
          value={formatNumber(indexStats.indexed)}
          note={
            indexStats.inProgress
              ? `${indexStats.inProgress} being indexed`
              : `of ${indexStats.total} searchable${indexStats.failed ? ` · ${indexStats.failed} failed` : ''}`
          }
          to="/search"
        />
        <StatCard
          icon={Bot}
          accent="cyan"
          label="AI assistant usage"
          value={formatNumber(answered)}
          note="Answers in this browser"
          to="/assistant"
        />
      </section>

      {isNewUser && (
        <section className="card onboarding">
          <div>
            <h2>Get started in three steps</h2>
            <p className="text-secondary">Your dashboard fills in as you add documents and run analyses.</p>
          </div>
          <ol className="onboarding__steps">
            <li>
              <span>1</span>
              <Link to="/resumes">Upload a resume</Link>
            </li>
            <li>
              <span>2</span>
              <Link to="/jobs">Save a job description</Link>
            </li>
            <li>
              <span>3</span>
              <Link to="/analysis">Run your first analysis</Link>
            </li>
          </ol>
        </section>
      )}

      <section className="dashboard-grid">
        <article className="card dashboard-grid__wide">
          <header className="card__header">
            <div>
              <h2>Match score by analysis</h2>
              <p className="text-secondary">Each column is one analysis, oldest to newest (0–100).</p>
            </div>
          </header>
          {analyses.loading ? (
            <Skeleton height={220} />
          ) : analyses.error ? (
            <ErrorState compact error={analyses.error} onRetry={analyses.reload} />
          ) : scorePoints.length === 0 ? (
            <EmptyState
              compact
              illustration={ChartIllustration}
              title="No analyses yet"
              description="Run a resume vs job analysis to see your match scores here."
              action={
                <Link to="/analysis" className="btn btn--secondary">
                  Run analysis
                </Link>
              }
            />
          ) : (
            <ScoreTrendChart points={scorePoints} />
          )}
        </article>

        <article className="card">
          <header className="card__header">
            <div>
              <h2>Top skill gaps</h2>
              <p className="text-secondary">Skills most often missing across your analyses.</p>
            </div>
          </header>
          {insights.loading ? (
            <div className="stack-sm">
              {Array.from({ length: 5 }, (_, index) => (
                <Skeleton key={index} height={18} />
              ))}
            </div>
          ) : insights.error ? (
            <ErrorState compact error={insights.error} onRetry={insights.reload} />
          ) : !insights.data?.top_missing_skills?.length ? (
            <EmptyState
              compact
              illustration={SearchIllustration}
              title="No skill gaps yet"
              description="Missing skills from your analyses will be ranked here."
            />
          ) : (
            <SkillGapChart skills={insights.data.top_missing_skills} total={insights.data.analysis_count} />
          )}
        </article>

        <article className="card">
          <header className="card__header">
            <div>
              <h2>Recent activity</h2>
              <p className="text-secondary">Latest uploads, jobs and analyses.</p>
            </div>
          </header>
          {activityLoading ? (
            <div className="stack-sm">
              {Array.from({ length: 4 }, (_, index) => (
                <Skeleton key={index} height={40} />
              ))}
            </div>
          ) : activityError ? (
            <ErrorState
              compact
              error={activityError}
              onRetry={() => {
                resumes.reload()
                jobs.reload()
                analyses.reload()
              }}
            />
          ) : activity.length === 0 ? (
            <EmptyState compact title="Nothing here yet" description="Your recent actions will appear here." />
          ) : (
            <ul className="activity-list">
              {activity.map((item) => {
                const meta = ACTIVITY_META[item.type]
                const Icon = meta.icon
                return (
                  <li key={item.key}>
                    <Link to={meta.to} className="activity-item">
                      <span className={`activity-item__icon activity-item__icon--${item.type}`}>
                        <Icon size={16} aria-hidden="true" />
                      </span>
                      <span className="activity-item__body">
                        <span className="activity-item__verb">{meta.verb}</span>
                        <span className="activity-item__title">{item.title}</span>
                      </span>
                      <span className="activity-item__meta">
                        {item.detail && <span>{item.detail}</span>}
                        <time dateTime={item.parsed.toISOString()}>{formatRelative(item.parsed)}</time>
                      </span>
                    </Link>
                  </li>
                )
              })}
            </ul>
          )}
        </article>

        <article className="card">
          <header className="card__header">
            <div>
              <h2>Best job matches</h2>
              <p className="text-secondary">
                {canRank && resumes.data ? `Saved jobs closest to ${resumes.data[0].filename}.` : 'Saved jobs closest to your newest resume.'}
              </p>
            </div>
            {canRank && (
              <Link to="/matches" className="link-text">
                View all
              </Link>
            )}
          </header>
          {resumes.loading || jobs.loading || (canRank && !topMatches.data && !topMatches.error) ? (
            <div className="stack-sm">
              {Array.from({ length: 3 }, (_, index) => (
                <Skeleton key={index} height={44} />
              ))}
            </div>
          ) : resumes.error || jobs.error ? (
            <ErrorState compact error={resumes.error || jobs.error} />
          ) : !canRank ? (
            <EmptyState
              compact
              title="Nothing to rank yet"
              description="Upload a resume and save a job description to see which jobs fit you best."
            />
          ) : topMatches.error ? (
            <ErrorState compact error={topMatches.error} onRetry={topMatches.reload} />
          ) : !topMatches.data.recommendations.length ? (
            <EmptyState compact title="No matches yet" description="Your saved jobs could not be ranked right now." />
          ) : (
            <ul className="activity-list">
              {topMatches.data.recommendations.map((match) => {
                const band = scoreBand(match.match_score)
                return (
                  <li key={match.job_id}>
                    <Link to={`/matches?resume=${topMatches.data.resume_id}`} className="activity-item">
                      <span className="activity-item__icon activity-item__icon--job">
                        <Target size={16} aria-hidden="true" />
                      </span>
                      <span className="activity-item__body">
                        <span className="activity-item__verb">{match.company}</span>
                        <span className="activity-item__title">{match.title}</span>
                      </span>
                      <span className={`score-badge score-badge--${band.key}`} title={band.label}>
                        {match.match_score}
                      </span>
                    </Link>
                  </li>
                )
              })}
            </ul>
          )}
        </article>

        <article className="card">
          <header className="card__header">
            <div>
              <h2>Latest recommendations</h2>
              <p className="text-secondary">From your most recent analyses.</p>
            </div>
          </header>
          {insights.loading ? (
            <div className="stack-sm">
              {Array.from({ length: 3 }, (_, index) => (
                <Skeleton key={index} height={36} />
              ))}
            </div>
          ) : insights.error ? (
            <ErrorState compact error={insights.error} onRetry={insights.reload} />
          ) : !insights.data?.recommendations?.length ? (
            <EmptyState
              compact
              title="No recommendations yet"
              description="Run an analysis to receive specific, actionable suggestions."
            />
          ) : (
            <ul className="recommendation-list">
              {insights.data.recommendations.slice(0, 5).map((text, index) => (
                <li key={`${index}-${text}`}>
                  <Sparkles size={15} aria-hidden="true" />
                  <span>{text}</span>
                </li>
              ))}
            </ul>
          )}
        </article>
      </section>
    </>
  )
}
