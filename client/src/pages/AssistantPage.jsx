import { useEffect, useMemo, useRef, useState } from 'react'
import { ArrowUp, Bot, BriefcaseBusiness, FileText, RotateCcw, Sparkles, Trash2, User } from 'lucide-react'
import { assistantApi, jobsApi, resumesApi } from '../api/services'
import { useAuth } from '../auth/AuthContext'
import { useApi } from '../hooks/useApi'
import { SelectField } from '../components/ui/Field'
import { ConfirmDialog } from '../components/ui/Modal'
import { Markdown } from '../components/ui/Markdown'
import { ChatIllustration } from '../components/ui/Illustrations'
import { clearChat, loadChat, saveChat } from '../utils/chatHistory'
import { formatRelative, similarityPercent } from '../utils/format'

let idCounter = 0
function newId() {
  idCounter += 1
  return `${Date.now().toString(36)}-${idCounter}-${Math.random().toString(36).slice(2, 8)}`
}

const STARTERS = [
  'What are my strongest technical skills?',
  'Which skills am I missing for this job?',
  'Which of my projects best fit this role?',
  'Summarize my work experience.',
]

function SourceCards({ sources, nameFor }) {
  if (!sources?.length) return null
  return (
    <div className="sources">
      <p className="sources__label">Sources · {sources.length} retrieved passage{sources.length === 1 ? '' : 's'}</p>
      <ul className="sources__list">
        {sources.map((source, index) => {
          const isResume = source.document_type === 'resume'
          return (
            <li key={`${source.document_type}-${source.document_id}-${source.chunk_index}`} className="source-card">
              <span className="source-card__index">{index + 1}</span>
              <span className={`source-card__icon source-card__icon--${source.document_type}`}>
                {isResume ? <FileText size={14} aria-hidden="true" /> : <BriefcaseBusiness size={14} aria-hidden="true" />}
              </span>
              <span className="source-card__body">
                <span className="source-card__name" title={nameFor(source)}>
                  {nameFor(source)}
                </span>
                <span className="source-card__meta">
                  {isResume ? 'Resume' : 'Job'} · chunk {source.chunk_index + 1}
                  {typeof source.score === 'number' && ` · ${similarityPercent(source.score)}% similar`}
                </span>
              </span>
            </li>
          )
        })}
      </ul>
    </div>
  )
}

function TypingIndicator() {
  return (
    <div className="message message--assistant" aria-live="polite" aria-label="Assistant is typing">
      <span className="message__avatar message__avatar--assistant">
        <Bot size={16} />
      </span>
      <div className="message__bubble message__bubble--typing">
        <span className="typing">
          <span />
          <span />
          <span />
        </span>
        <span className="text-muted">Searching your documents…</span>
      </div>
    </div>
  )
}

export function AssistantPage() {
  const { user } = useAuth()
  const resumes = useApi((signal) => resumesApi.list({ signal }))
  const jobs = useApi((signal) => jobsApi.list({ signal }))
  const [messages, setMessages] = useState(() => loadChat(user?.id))
  const [draft, setDraft] = useState('')
  const [pending, setPending] = useState(false)
  const [resumeId, setResumeId] = useState('')
  const [jobId, setJobId] = useState('')
  const [confirmClear, setConfirmClear] = useState(false)
  const endRef = useRef(null)
  const inputRef = useRef(null)

  useEffect(() => {
    saveChat(user?.id, messages)
  }, [messages, user?.id])

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' })
  }, [messages, pending])

  const names = useMemo(() => {
    const map = new Map()
    ;(resumes.data || []).forEach((resume) => map.set(`resume-${resume.id}`, resume.filename))
    ;(jobs.data || []).forEach((job) => map.set(`job-${job.id}`, `${job.title} · ${job.company}`))
    return map
  }, [resumes.data, jobs.data])

  const nameFor = (source) =>
    names.get(`${source.document_type}-${source.document_id}`) ||
    `${source.document_type === 'resume' ? 'Resume' : 'Job'} #${source.document_id} (deleted)`

  const ask = async (text, scopeOverride) => {
    const question = text.trim()
    if (!question || pending) return
    const scope = scopeOverride || {
      resumeId: resumeId ? Number(resumeId) : null,
      jobId: jobId ? Number(jobId) : null,
    }
    const userMessage = { id: newId(), role: 'user', content: question, at: new Date().toISOString(), scope }
    setMessages((current) => [...current, userMessage])
    setDraft('')
    setPending(true)
    try {
      const response = await assistantApi.ask({ question, ...scope })
      setMessages((current) => [
        ...current,
        {
          id: newId(),
          role: 'assistant',
          content: response.answer,
          sources: response.sources,
          at: new Date().toISOString(),
        },
      ])
    } catch (error) {
      setMessages((current) => [
        ...current,
        { id: newId(), role: 'assistant', error: error.message, question, scope, at: new Date().toISOString() },
      ])
    } finally {
      setPending(false)
      inputRef.current?.focus()
    }
  }

  // Drop the failed answer and the question right before it, then ask again with the same scope.
  const retry = (message) => {
    setMessages((current) => {
      const index = current.findIndex((item) => item.id === message.id)
      if (index === -1) return current
      const previous = current[index - 1]
      const removeQuestion = previous?.role === 'user' && previous.content === message.question
      return current.filter((_, position) => position !== index && !(removeQuestion && position === index - 1))
    })
    ask(message.question, message.scope || { resumeId: null, jobId: null })
  }

  const onKeyDown = (event) => {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault()
      ask(draft)
    }
  }

  const scopeLabel = [
    resumeId && names.get(`resume-${resumeId}`),
    jobId && names.get(`job-${jobId}`),
  ].filter(Boolean)

  return (
    <div className="chat">
      <header className="chat__header card card--glass">
        <div className="chat__title">
          <span className="chat__title-icon">
            <Sparkles size={18} />
          </span>
          <div>
            <h1>AI Assistant</h1>
            <p className="text-secondary">Answers are grounded only in your uploaded resumes and jobs.</p>
          </div>
        </div>
        <div className="chat__scope">
          <SelectField label="Resume" value={resumeId} onChange={(event) => setResumeId(event.target.value)} disabled={resumes.loading}>
            <option value="">All resumes</option>
            {(resumes.data || []).map((resume) => (
              <option key={resume.id} value={resume.id}>
                {resume.filename}
              </option>
            ))}
          </SelectField>
          <SelectField label="Job" value={jobId} onChange={(event) => setJobId(event.target.value)} disabled={jobs.loading}>
            <option value="">All jobs</option>
            {(jobs.data || []).map((job) => (
              <option key={job.id} value={job.id}>
                {job.title} · {job.company}
              </option>
            ))}
          </SelectField>
          <button
            className="icon-button"
            onClick={() => setConfirmClear(true)}
            disabled={!messages.length || pending}
            aria-label="Clear conversation"
            title="Clear conversation"
          >
            <Trash2 size={18} />
          </button>
        </div>
      </header>

      <section className="chat__messages" aria-label="Conversation">
        {messages.length === 0 && !pending ? (
          <div className="chat__empty">
            <ChatIllustration />
            <h2>Ask anything about your documents</h2>
            <p className="text-secondary">
              The assistant retrieves the most relevant passages from your indexed resumes and jobs, then answers with
              citations. Narrow the scope with the selectors above.
            </p>
            <div className="starter-grid">
              {STARTERS.map((starter) => (
                <button key={starter} className="starter" onClick={() => ask(starter)}>
                  <Sparkles size={14} aria-hidden="true" /> {starter}
                </button>
              ))}
            </div>
          </div>
        ) : (
          messages.map((message) =>
            message.role === 'user' ? (
              <div key={message.id} className="message message--user">
                <div className="message__bubble">
                  <p>{message.content}</p>
                </div>
                <span className="message__avatar message__avatar--user">
                  <User size={16} />
                </span>
              </div>
            ) : (
              <div key={message.id} className="message message--assistant">
                <span className="message__avatar message__avatar--assistant">
                  <Bot size={16} />
                </span>
                <div className={`message__bubble ${message.error ? 'message__bubble--error' : ''}`}>
                  {message.error ? (
                    <>
                      <p>
                        <strong>Couldn’t get an answer.</strong> {message.error}
                      </p>
                      <button className="btn btn--secondary btn--sm" onClick={() => retry(message)} disabled={pending}>
                        <RotateCcw size={14} /> Retry
                      </button>
                    </>
                  ) : (
                    <>
                      <Markdown text={message.content} />
                      <SourceCards sources={message.sources} nameFor={nameFor} />
                    </>
                  )}
                  <time className="message__time" dateTime={message.at}>
                    {formatRelative(new Date(message.at))}
                  </time>
                </div>
              </div>
            ),
          )
        )}
        {pending && <TypingIndicator />}
        <div ref={endRef} />
      </section>

      <form
        className="composer card card--glass"
        onSubmit={(event) => {
          event.preventDefault()
          ask(draft)
        }}
      >
        {scopeLabel.length > 0 && (
          <p className="composer__scope">
            Scoped to: <strong>{scopeLabel.join(' + ')}</strong>
          </p>
        )}
        <div className="composer__row">
          <textarea
            ref={inputRef}
            value={draft}
            onChange={(event) => setDraft(event.target.value)}
            onKeyDown={onKeyDown}
            placeholder="Ask about your resume or a job description…"
            rows={1}
            maxLength={2000}
            aria-label="Message"
            disabled={pending}
          />
          <button type="submit" className="btn btn--primary composer__send" disabled={!draft.trim() || pending} aria-label="Send">
            <ArrowUp size={18} />
          </button>
        </div>
        <p className="composer__hint">Enter to send · Shift + Enter for a new line · {draft.length}/2000</p>
      </form>

      <ConfirmDialog
        open={confirmClear}
        title="Clear conversation?"
        message="This removes the conversation saved in this browser. Your documents are not affected."
        confirmLabel="Clear"
        onConfirm={() => {
          setMessages([])
          clearChat(user?.id)
          setConfirmClear(false)
        }}
        onClose={() => setConfirmClear(false)}
      />
    </div>
  )
}
