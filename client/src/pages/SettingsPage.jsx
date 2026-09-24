import { useState } from 'react'
import { CheckCircle2, Clock, Database, LogOut, Server, Trash2, UserRound, XCircle } from 'lucide-react'
import { API_BASE_URL } from '../api/client'
import { systemApi } from '../api/services'
import { useAuth } from '../auth/AuthContext'
import { useToast } from '../components/ui/Toast'
import { PageHeader } from '../components/ui/PageHeader'
import { ConfirmDialog } from '../components/ui/Modal'
import { Spinner } from '../components/ui/States'
import { clearChat, loadChat } from '../utils/chatHistory'
import { formatRelative } from '../utils/format'

function SettingRow({ icon: Icon, title, description, children }) {
  return (
    <div className="setting-row">
      <span className="setting-row__icon">
        <Icon size={18} aria-hidden="true" />
      </span>
      <div className="setting-row__text">
        <h3>{title}</h3>
        {description && <p className="text-secondary">{description}</p>}
      </div>
      <div className="setting-row__control">{children}</div>
    </div>
  )
}

export function SettingsPage() {
  const { user, expiresAt, logout } = useAuth()
  const toast = useToast()
  const [health, setHealth] = useState({ status: 'idle' })
  const [confirmClear, setConfirmClear] = useState(false)
  const [chatCount, setChatCount] = useState(() => loadChat(user?.id).length)

  const checkHealth = async () => {
    setHealth({ status: 'checking' })
    const started = performance.now()
    try {
      const data = await systemApi.health()
      setHealth({ status: data?.status === 'healthy' ? 'online' : 'offline', ms: Math.round(performance.now() - started) })
    } catch (error) {
      setHealth({ status: 'offline', error: error.message })
    }
  }

  return (
    <>
      <PageHeader eyebrow="Workspace" title="Settings" description="Your account, session and connection details." />

      <div className="settings">
        <section className="card">
          <header className="card__header">
            <h2>Account</h2>
          </header>
          <SettingRow icon={UserRound} title="Email" description="The address you sign in with.">
            <span className="setting-value">{user?.email}</span>
          </SettingRow>
          <SettingRow icon={Database} title="User ID" description="Your account identifier in the API.">
            <span className="setting-value mono">{user?.id}</span>
          </SettingRow>
        </section>

        <section className="card">
          <header className="card__header">
            <h2>Session</h2>
          </header>
          <SettingRow
            icon={Clock}
            title="Session expires"
            description="Access tokens are short-lived. You will be asked to sign in again when this one expires."
          >
            <span className="setting-value">{expiresAt ? `${expiresAt.toLocaleTimeString()} (${formatRelative(expiresAt)})` : '—'}</span>
          </SettingRow>
          <SettingRow icon={LogOut} title="Sign out" description="End this session on this device.">
            <button className="btn btn--secondary" onClick={() => logout()}>
              <LogOut size={16} /> Sign out
            </button>
          </SettingRow>
        </section>

        <section className="card">
          <header className="card__header">
            <h2>API connection</h2>
          </header>
          <SettingRow icon={Server} title="API base URL" description="Requests are sent here (proxied to FastAPI in development).">
            <span className="setting-value mono">{API_BASE_URL}</span>
          </SettingRow>
          <SettingRow icon={Server} title="Health check" description="Calls GET /health on the API.">
            <div className="health-result">
              {health.status === 'online' && (
                <span className="status-pill status-pill--good">
                  <CheckCircle2 size={14} /> Healthy · {health.ms} ms
                </span>
              )}
              {health.status === 'offline' && (
                <span className="status-pill status-pill--critical" title={health.error}>
                  <XCircle size={14} /> Unreachable
                </span>
              )}
              <button className="btn btn--secondary" onClick={checkHealth} disabled={health.status === 'checking'}>
                {health.status === 'checking' && <Spinner size={14} />} Check now
              </button>
            </div>
          </SettingRow>
        </section>

        <section className="card">
          <header className="card__header">
            <h2>Data in this browser</h2>
          </header>
          <SettingRow
            icon={Trash2}
            title="Assistant conversation"
            description={`${chatCount} message${chatCount === 1 ? '' : 's'} saved locally. The API does not store chat history.`}
          >
            <button className="btn btn--danger-ghost" onClick={() => setConfirmClear(true)} disabled={!chatCount}>
              <Trash2 size={16} /> Clear
            </button>
          </SettingRow>
        </section>
      </div>

      <ConfirmDialog
        open={confirmClear}
        title="Clear assistant conversation?"
        message="The conversation saved in this browser will be removed. Your documents and analyses are not affected."
        confirmLabel="Clear"
        onConfirm={() => {
          clearChat(user?.id)
          setChatCount(0)
          setConfirmClear(false)
          toast.success('Conversation cleared')
        }}
        onClose={() => setConfirmClear(false)}
      />
    </>
  )
}
