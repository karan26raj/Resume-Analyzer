import { useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Building2, Eye, Plus, RefreshCw, Search, Sparkles, Trash2 } from 'lucide-react'
import { embeddingsApi, jobsApi } from '../api/services'
import { useApi } from '../hooks/useApi'
import { usePollWhile } from '../hooks/usePollWhile'
import { IndexStatusBadge, isIndexing } from '../components/ui/IndexStatusBadge'
import { useToast } from '../components/ui/Toast'
import { PageHeader } from '../components/ui/PageHeader'
import { TextArea, TextField } from '../components/ui/Field'
import { ConfirmDialog, Modal } from '../components/ui/Modal'
import { EmptyState, ErrorState, InlineError, SkeletonCards, Spinner } from '../components/ui/States'
import { BriefcaseIllustration } from '../components/ui/Illustrations'
import { formatDate, formatRelative } from '../utils/format'

// Limits from server/app/schemas/job.py
const LIMITS = { title: 255, company: 255, description: 10000 }
const EMPTY_FORM = { title: '', company: '', description: '' }

function validate(form) {
  const errors = {}
  for (const [field, max] of Object.entries(LIMITS)) {
    const value = form[field].trim()
    if (!value) errors[field] = 'This field is required'
    else if (value.length > max) errors[field] = `Keep it under ${max.toLocaleString()} characters`
  }
  return errors
}

export function JobsPage() {
  const toast = useToast()
  const navigate = useNavigate()
  const jobs = useApi((signal) => jobsApi.list({ signal }))
  const [form, setForm] = useState(EMPTY_FORM)
  const [touched, setTouched] = useState({})
  const [submitting, setSubmitting] = useState(false)
  const [submitError, setSubmitError] = useState(null)
  const [filter, setFilter] = useState('')
  const [viewing, setViewing] = useState(null)
  const [toDelete, setToDelete] = useState(null)
  const [deleting, setDeleting] = useState(false)
  const [indexing, setIndexing] = useState(null)

  // New jobs are indexed by the background worker; refresh until none is still in progress.
  usePollWhile((jobs.data || []).some(isIndexing), jobs.reload)

  const errors = validate(form)
  const update = (field) => (event) => setForm((current) => ({ ...current, [field]: event.target.value }))
  const blur = (field) => () => setTouched((current) => ({ ...current, [field]: true }))

  const onSubmit = async (event) => {
    event.preventDefault()
    setTouched({ title: true, company: true, description: true })
    if (Object.keys(errors).length) return
    setSubmitting(true)
    setSubmitError(null)
    try {
      const job = await jobsApi.create({
        title: form.title.trim(),
        company: form.company.trim(),
        description: form.description.trim(),
      })
      jobs.setData((current) => [job, ...(current || [])])
      setForm(EMPTY_FORM)
      setTouched({})
      toast.success(`Saved “${job.title}” at ${job.company}`)
    } catch (error) {
      setSubmitError(error.message)
    } finally {
      setSubmitting(false)
    }
  }

  const reindex = async (job) => {
    setIndexing(job.id)
    try {
      const result = await embeddingsApi.indexJob(job.id)
      toast.success(`Indexed “${job.title}” into ${result.chunk_count} chunk${result.chunk_count === 1 ? '' : 's'}`)
    } catch (error) {
      toast.error(`Indexing failed: ${error.message}`)
    } finally {
      setIndexing(null)
      jobs.reload()
    }
  }

  const confirmDelete = async () => {
    setDeleting(true)
    try {
      await jobsApi.remove(toDelete.id)
      jobs.setData((current) => (current || []).filter((item) => item.id !== toDelete.id))
      toast.success(`Deleted “${toDelete.title}”`)
      setToDelete(null)
    } catch (error) {
      toast.error(error.message)
    } finally {
      setDeleting(false)
    }
  }

  const filtered = useMemo(() => {
    const query = filter.trim().toLowerCase()
    return (jobs.data || []).filter(
      (job) => !query || job.title.toLowerCase().includes(query) || job.company.toLowerCase().includes(query),
    )
  }, [jobs.data, filter])

  const descriptionLength = form.description.trim().length

  return (
    <>
      <PageHeader
        eyebrow="Documents"
        title="Jobs"
        description="Save job descriptions to analyze your resumes against them. Line breaks are fine — paste the posting as-is."
      />

      <div className="jobs-layout">
        <section className="card card--glass job-form">
          <header className="card__header">
            <div>
              <h2>Add a job description</h2>
              <p className="text-secondary">All fields are required.</p>
            </div>
          </header>
          <form onSubmit={onSubmit} noValidate className="form-stack">
            <TextField
              label="Job title"
              value={form.title}
              onChange={update('title')}
              onBlur={blur('title')}
              error={touched.title ? errors.title : null}
              maxLength={LIMITS.title + 50}
            />
            <TextField
              label="Company"
              value={form.company}
              onChange={update('company')}
              onBlur={blur('company')}
              error={touched.company ? errors.company : null}
              maxLength={LIMITS.company + 50}
            />
            <TextArea
              label="Job description"
              rows={10}
              value={form.description}
              onChange={update('description')}
              onBlur={blur('description')}
              error={touched.description ? errors.description : null}
              hint="Responsibilities, requirements and nice-to-haves"
              counter={{
                text: `${descriptionLength.toLocaleString()} / ${LIMITS.description.toLocaleString()}`,
                over: descriptionLength > LIMITS.description,
              }}
            />
            <InlineError>{submitError}</InlineError>
            <button type="submit" className="btn btn--primary btn--block" disabled={submitting}>
              {submitting ? <Spinner size={16} /> : <Plus size={16} />} Save job
            </button>
          </form>
        </section>

        <section className="section jobs-list">
          <div className="section__toolbar">
            <h2>
              Saved jobs {jobs.data && <span className="count-badge">{jobs.data.length}</span>}
            </h2>
            <label className="search-input">
              <Search size={16} aria-hidden="true" />
              <input
                type="search"
                placeholder="Filter by title or company"
                value={filter}
                onChange={(event) => setFilter(event.target.value)}
                aria-label="Filter jobs"
              />
            </label>
          </div>

          {jobs.loading ? (
            <SkeletonCards count={4} height={150} />
          ) : jobs.error ? (
            <div className="card">
              <ErrorState error={jobs.error} onRetry={jobs.reload} />
            </div>
          ) : !jobs.data.length ? (
            <div className="card">
              <EmptyState
                illustration={BriefcaseIllustration}
                title="No jobs saved yet"
                description="Add a job description with the form to start matching your resumes against it."
              />
            </div>
          ) : !filtered.length ? (
            <div className="card">
              <EmptyState compact title="No matches" description={`No job title or company contains “${filter}”.`} />
            </div>
          ) : (
            <div className={`card-grid card-grid--jobs ${jobs.refreshing ? 'is-refreshing' : ''}`}>
              {filtered.map((job) => (
                <article key={job.id} className="card job-card">
                  <div className="job-card__company">
                    <span className="job-card__logo" aria-hidden="true">
                      {job.company.charAt(0).toUpperCase()}
                    </span>
                    <span>
                      <Building2 size={13} aria-hidden="true" /> {job.company}
                    </span>
                  </div>
                  <h3 className="job-card__title">{job.title}</h3>
                  <p className="job-card__excerpt">{job.description}</p>
                  <IndexStatusBadge document={job} />
                  <div className="job-card__footer">
                    <span className="text-muted" title={formatDate(job.created_at)}>
                      Saved {formatRelative(job.created_at)}
                    </span>
                    <div className="row-actions">
                      <button className="icon-button" onClick={() => setViewing(job)} aria-label={`View ${job.title}`} title="View description">
                        <Eye size={16} />
                      </button>
                      <button
                        className="icon-button"
                        onClick={() => reindex(job)}
                        disabled={indexing === job.id}
                        aria-label={`Re-index ${job.title}`}
                        title="Re-index for search"
                      >
                        {indexing === job.id ? <Spinner size={14} /> : <RefreshCw size={16} />}
                      </button>
                      <button
                        className="icon-button icon-button--danger"
                        onClick={() => setToDelete(job)}
                        aria-label={`Delete ${job.title}`}
                        title="Delete"
                      >
                        <Trash2 size={16} />
                      </button>
                      <button className="btn btn--secondary btn--sm" onClick={() => navigate(`/analysis?job=${job.id}`)}>
                        <Sparkles size={14} /> Analyze
                      </button>
                    </div>
                  </div>
                </article>
              ))}
            </div>
          )}
        </section>
      </div>

      <Modal
        open={Boolean(viewing)}
        title={viewing?.title}
        subtitle={viewing ? `${viewing.company} · saved ${formatDate(viewing.created_at)}` : ''}
        onClose={() => setViewing(null)}
        size="lg"
        footer={
          <button className="btn btn--primary" onClick={() => navigate(`/analysis?job=${viewing.id}`)}>
            <Sparkles size={16} /> Analyze a resume against this job
          </button>
        }
      >
        <p className="prose-text">{viewing?.description}</p>
      </Modal>

      <ConfirmDialog
        open={Boolean(toDelete)}
        title="Delete job?"
        message={`“${toDelete?.title}” at ${toDelete?.company} will be permanently deleted along with its analyses and search index entries.`}
        busy={deleting}
        onConfirm={confirmDelete}
        onClose={() => setToDelete(null)}
      />
    </>
  )
}
