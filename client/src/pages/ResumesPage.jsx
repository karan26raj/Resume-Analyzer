import { useMemo, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  CheckCircle2,
  CloudUpload,
  Eye,
  FileText,
  LayoutGrid,
  List,
  RefreshCw,
  Search,
  Sparkles,
  Target,
  Trash2,
  X,
  XCircle,
} from 'lucide-react'
import { embeddingsApi, resumesApi } from '../api/services'
import { useApi } from '../hooks/useApi'
import { usePollWhile } from '../hooks/usePollWhile'
import { IndexStatusBadge, isIndexing } from '../components/ui/IndexStatusBadge'
import { useToast } from '../components/ui/Toast'
import { PageHeader } from '../components/ui/PageHeader'
import { ConfirmDialog, Modal } from '../components/ui/Modal'
import { EmptyState, ErrorState, SkeletonCards, Spinner } from '../components/ui/States'
import { DocumentIllustration } from '../components/ui/Illustrations'
import { fileTypeLabel, formatBytes, formatDate, formatRelative, parseApiDate } from '../utils/format'

const MAX_BYTES = 10 * 1024 * 1024
const ALLOWED = ['.pdf', '.docx']

function validateFile(file) {
  const extension = file.name.slice(file.name.lastIndexOf('.')).toLowerCase()
  if (!ALLOWED.includes(extension)) return 'Only PDF and DOCX files are allowed'
  if (file.size === 0) return 'The file is empty'
  if (file.size > MAX_BYTES) return `File is ${formatBytes(file.size)} — the limit is 10 MB`
  return null
}

function UploadItem({ item, onCancel, onDismiss }) {
  const percent = Math.round(item.progress * 100)
  return (
    <li className={`upload-item upload-item--${item.status}`}>
      <span className="upload-item__icon">
        {item.status === 'done' ? (
          <CheckCircle2 size={18} />
        ) : item.status === 'error' ? (
          <XCircle size={18} />
        ) : (
          <FileText size={18} />
        )}
      </span>
      <div className="upload-item__body">
        <div className="upload-item__row">
          <span className="upload-item__name">{item.file.name}</span>
          <span className="upload-item__size">{formatBytes(item.file.size)}</span>
        </div>
        {item.status === 'uploading' && (
          <div className="progress" role="progressbar" aria-valuenow={percent} aria-valuemin={0} aria-valuemax={100}>
            <span style={{ width: `${percent}%` }} />
          </div>
        )}
        <p className="upload-item__status">
          {item.status === 'uploading' && `Uploading… ${percent}%`}
          {item.status === 'processing' && (
            <>
              <Spinner size={12} /> Validating & extracting text…
            </>
          )}
          {item.status === 'done' && `Uploaded — ${item.result.text_length.toLocaleString()} characters extracted`}
          {item.status === 'error' && item.error}
        </p>
      </div>
      {item.status === 'uploading' ? (
        <button className="icon-button icon-button--sm" onClick={onCancel} aria-label={`Cancel ${item.file.name}`}>
          <X size={16} />
        </button>
      ) : item.status === 'done' || item.status === 'error' ? (
        <button className="icon-button icon-button--sm" onClick={onDismiss} aria-label="Dismiss">
          <X size={16} />
        </button>
      ) : null}
    </li>
  )
}

export function ResumesPage() {
  const toast = useToast()
  const navigate = useNavigate()
  const resumes = useApi((signal) => resumesApi.list({ signal }))
  const [uploads, setUploads] = useState([])
  const [dragging, setDragging] = useState(false)
  const [view, setView] = useState('cards')
  const [filter, setFilter] = useState('')
  const [preview, setPreview] = useState(null)
  const [toDelete, setToDelete] = useState(null)
  const [deleting, setDeleting] = useState(false)
  const [indexing, setIndexing] = useState(null)
  const inputRef = useRef(null)
  const aborters = useRef(new Map())
  const nextId = useRef(1)

  usePollWhile((resumes.data || []).some(isIndexing), resumes.reload)

  const updateUpload = (id, patch) =>
    setUploads((current) => current.map((item) => (item.id === id ? { ...item, ...patch } : item)))

  const startUpload = (file) => {
    const id = nextId.current++
    const validationError = validateFile(file)
    setUploads((current) => [
      { id, file, progress: 0, status: validationError ? 'error' : 'uploading', error: validationError },
      ...current,
    ])
    if (validationError) return

    const { promise, abort } = resumesApi.upload(file, (fraction) => {
      updateUpload(id, fraction >= 1 ? { progress: 1, status: 'processing' } : { progress: fraction })
    })
    aborters.current.set(id, abort)

    promise
      .then((result) => {
        updateUpload(id, { status: 'done', progress: 1, result })
        toast.success(`${result.filename} uploaded`)
        resumes.reload()
      })
      .catch((error) => {
        if (error.name === 'AbortError') {
          setUploads((current) => current.filter((item) => item.id !== id))
          return
        }
        updateUpload(id, { status: 'error', error: error.message })
      })
      .finally(() => aborters.current.delete(id))
  }

  const onFiles = (fileList) => Array.from(fileList || []).forEach(startUpload)

  const onDrop = (event) => {
    event.preventDefault()
    setDragging(false)
    onFiles(event.dataTransfer.files)
  }

  const openPreview = async (resume) => {
    setPreview({ resume, loading: true })
    try {
      const data = await resumesApi.text(resume.id)
      setPreview({ resume, text: data.text })
    } catch (error) {
      setPreview({ resume, error })
    }
  }

  const reindex = async (resume) => {
    setIndexing(resume.id)
    try {
      const result = await embeddingsApi.indexResume(resume.id)
      toast.success(`Indexed ${resume.filename} into ${result.chunk_count} chunk${result.chunk_count === 1 ? '' : 's'}`)
    } catch (error) {
      toast.error(`Indexing failed: ${error.message}`)
    } finally {
      setIndexing(null)
      resumes.reload()
    }
  }

  const confirmDelete = async () => {
    setDeleting(true)
    try {
      await resumesApi.remove(toDelete.id)
      toast.success(`${toDelete.filename} deleted`)
      resumes.setData((current) => (current || []).filter((item) => item.id !== toDelete.id))
      setToDelete(null)
    } catch (error) {
      toast.error(error.message)
    } finally {
      setDeleting(false)
    }
  }

  const sorted = useMemo(() => {
    const query = filter.trim().toLowerCase()
    return [...(resumes.data || [])]
      .filter((resume) => !query || resume.filename.toLowerCase().includes(query))
      .sort((a, b) => (parseApiDate(b.created_at) || 0) - (parseApiDate(a.created_at) || 0))
  }, [resumes.data, filter])

  const actions = (resume) => (
    <div className="row-actions">
      <button className="icon-button" onClick={() => openPreview(resume)} aria-label={`Preview ${resume.filename}`} title="Preview text">
        <Eye size={16} />
      </button>
      <button
        className="icon-button"
        onClick={() => reindex(resume)}
        disabled={indexing === resume.id}
        aria-label={`Re-index ${resume.filename}`}
        title="Re-index for search"
      >
        {indexing === resume.id ? <Spinner size={14} /> : <RefreshCw size={16} />}
      </button>
      <button
        className="icon-button"
        onClick={() => navigate(`/analysis?resume=${resume.id}`)}
        aria-label={`Analyze ${resume.filename}`}
        title="Analyze against a job"
      >
        <Sparkles size={16} />
      </button>
      <button
        className="icon-button"
        onClick={() => navigate(`/matches?resume=${resume.id}`)}
        aria-label={`Find job matches for ${resume.filename}`}
        title="Rank saved jobs for this resume"
      >
        <Target size={16} />
      </button>
      <button
        className="icon-button icon-button--danger"
        onClick={() => setToDelete(resume)}
        aria-label={`Delete ${resume.filename}`}
        title="Delete"
      >
        <Trash2 size={16} />
      </button>
    </div>
  )

  return (
    <>
      <PageHeader
        eyebrow="Documents"
        title="Resumes"
        description="Upload PDF or DOCX resumes. Text is extracted and indexed for semantic search automatically."
      />

      <section
        className={`dropzone ${dragging ? 'is-dragging' : ''}`}
        onDragOver={(event) => {
          event.preventDefault()
          setDragging(true)
        }}
        onDragLeave={(event) => {
          if (!event.currentTarget.contains(event.relatedTarget)) setDragging(false)
        }}
        onDrop={onDrop}
        onClick={() => inputRef.current?.click()}
        onKeyDown={(event) => (event.key === 'Enter' || event.key === ' ') && inputRef.current?.click()}
        role="button"
        tabIndex={0}
        aria-label="Upload resumes: drop files here or press Enter to browse"
      >
        <input
          ref={inputRef}
          type="file"
          accept=".pdf,.docx,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
          multiple
          hidden
          onChange={(event) => {
            onFiles(event.target.files)
            event.target.value = ''
          }}
        />
        <span className="dropzone__icon">
          <CloudUpload size={28} />
        </span>
        <h2>{dragging ? 'Drop to upload' : 'Drag & drop your resume'}</h2>
        <p>
          or <span className="link-text">browse files</span> · PDF or DOCX · up to 10 MB
        </p>
      </section>

      {uploads.length > 0 && (
        <ul className="upload-list" aria-label="Uploads">
          {uploads.map((item) => (
            <UploadItem
              key={item.id}
              item={item}
              onCancel={() => aborters.current.get(item.id)?.()}
              onDismiss={() => setUploads((current) => current.filter((upload) => upload.id !== item.id))}
            />
          ))}
        </ul>
      )}

      <section className="section">
        <div className="section__toolbar">
          <h2>
            Your resumes {resumes.data && <span className="count-badge">{resumes.data.length}</span>}
          </h2>
          <div className="toolbar">
            <label className="search-input">
              <Search size={16} aria-hidden="true" />
              <input
                type="search"
                placeholder="Filter by filename"
                value={filter}
                onChange={(event) => setFilter(event.target.value)}
                aria-label="Filter resumes by filename"
              />
            </label>
            <div className="segmented" role="tablist" aria-label="Layout">
              <button role="tab" aria-selected={view === 'cards'} className={view === 'cards' ? 'is-active' : ''} onClick={() => setView('cards')}>
                <LayoutGrid size={14} /> Cards
              </button>
              <button role="tab" aria-selected={view === 'table'} className={view === 'table' ? 'is-active' : ''} onClick={() => setView('table')}>
                <List size={14} /> Table
              </button>
            </div>
          </div>
        </div>

        {resumes.loading ? (
          <SkeletonCards count={3} />
        ) : resumes.error ? (
          <div className="card">
            <ErrorState error={resumes.error} onRetry={resumes.reload} />
          </div>
        ) : !resumes.data.length ? (
          <div className="card">
            <EmptyState
              illustration={DocumentIllustration}
              title="No resumes yet"
              description="Upload your first resume above to start matching it against job descriptions."
              action={
                <button className="btn btn--primary" onClick={() => inputRef.current?.click()}>
                  <CloudUpload size={16} /> Upload resume
                </button>
              }
            />
          </div>
        ) : !sorted.length ? (
          <div className="card">
            <EmptyState compact title="No matches" description={`No resume filename contains “${filter}”.`} />
          </div>
        ) : view === 'cards' ? (
          <div className={`card-grid ${resumes.refreshing ? 'is-refreshing' : ''}`}>
            {sorted.map((resume) => (
              <article key={resume.id} className="card doc-card">
                <div className="doc-card__top">
                  <span className={`file-badge file-badge--${fileTypeLabel(resume.file_type).toLowerCase()}`}>
                    {fileTypeLabel(resume.file_type)}
                  </span>
                  {actions(resume)}
                </div>
                <h3 className="doc-card__title" title={resume.filename}>
                  {resume.filename}
                </h3>
                <p className="doc-card__meta">
                  Uploaded {formatDate(resume.created_at)} · {formatRelative(resume.created_at)}
                </p>
                <IndexStatusBadge document={resume} />
              </article>
            ))}
          </div>
        ) : (
          <div className={`card table-card ${resumes.refreshing ? 'is-refreshing' : ''}`}>
            <div className="table-wrap">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Filename</th>
                    <th>Type</th>
                    <th>Uploaded</th>
                    <th>Search index</th>
                    <th className="actions-col">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {sorted.map((resume) => (
                    <tr key={resume.id}>
                      <td className="cell-strong">
                        <FileText size={16} aria-hidden="true" /> {resume.filename}
                      </td>
                      <td>
                        <span className={`file-badge file-badge--${fileTypeLabel(resume.file_type).toLowerCase()}`}>
                          {fileTypeLabel(resume.file_type)}
                        </span>
                      </td>
                      <td>{formatDate(resume.created_at)}</td>
                      <td>
                        <IndexStatusBadge document={resume} />
                      </td>
                      <td className="actions-col">{actions(resume)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </section>

      <Modal
        open={Boolean(preview)}
        title={preview?.resume.filename}
        subtitle="Extracted text (first 2,000 characters, as returned by the API)"
        onClose={() => setPreview(null)}
        size="lg"
      >
        {preview?.loading ? (
          <div className="center-pad">
            <Spinner size={24} />
          </div>
        ) : preview?.error ? (
          <ErrorState compact error={preview.error} onRetry={() => openPreview(preview.resume)} />
        ) : preview?.text ? (
          <pre className="text-preview">{preview.text}</pre>
        ) : (
          <EmptyState compact title="No text extracted" description="This document did not contain extractable text." />
        )}
      </Modal>

      <ConfirmDialog
        open={Boolean(toDelete)}
        title="Delete resume?"
        message={`“${toDelete?.filename}” will be permanently deleted along with its analyses and search index entries.`}
        busy={deleting}
        onConfirm={confirmDelete}
        onClose={() => setToDelete(null)}
      />
    </>
  )
}
