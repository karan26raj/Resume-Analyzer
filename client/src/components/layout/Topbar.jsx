import { useEffect, useRef, useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { LogOut, Menu, Settings } from 'lucide-react'
import { useAuth } from '../../auth/AuthContext'
import { systemApi } from '../../api/services'
import { titleForPath } from './navigation'

function ApiStatus() {
  const [status, setStatus] = useState('checking')

  useEffect(() => {
    let cancelled = false
    const check = () =>
      systemApi
        .health()
        .then((data) => !cancelled && setStatus(data?.status === 'healthy' ? 'online' : 'offline'))
        .catch(() => !cancelled && setStatus('offline'))
    check()
    const interval = setInterval(check, 60000)
    return () => {
      cancelled = true
      clearInterval(interval)
    }
  }, [])

  const label = { checking: 'Checking API', online: 'API online', offline: 'API offline' }[status]
  return (
    <span className={`api-status api-status--${status}`} title={label}>
      <span className="api-status__dot" aria-hidden="true" />
      <span className="api-status__label">{label}</span>
    </span>
  )
}

function UserMenu() {
  const { user, logout } = useAuth()
  const [open, setOpen] = useState(false)
  const navigate = useNavigate()
  const ref = useRef(null)

  useEffect(() => {
    if (!open) return undefined
    const onClick = (event) => !ref.current?.contains(event.target) && setOpen(false)
    const onKey = (event) => event.key === 'Escape' && setOpen(false)
    document.addEventListener('mousedown', onClick)
    document.addEventListener('keydown', onKey)
    return () => {
      document.removeEventListener('mousedown', onClick)
      document.removeEventListener('keydown', onKey)
    }
  }, [open])

  const email = user?.email || ''
  return (
    <div className="user-menu" ref={ref}>
      <button className="user-menu__trigger" onClick={() => setOpen((value) => !value)} aria-expanded={open} aria-haspopup="menu">
        <span className="avatar" aria-hidden="true">
          {email.charAt(0).toUpperCase() || '?'}
        </span>
        <span className="user-menu__email">{email}</span>
      </button>
      {open && (
        <div className="user-menu__panel" role="menu">
          <p className="user-menu__signed">Signed in as</p>
          <p className="user-menu__address">{email}</p>
          <button role="menuitem" onClick={() => navigate('/settings')}>
            <Settings size={16} /> Settings
          </button>
          <button role="menuitem" onClick={() => logout()}>
            <LogOut size={16} /> Sign out
          </button>
        </div>
      )}
    </div>
  )
}

export function Topbar({ onOpenNav }) {
  const { pathname } = useLocation()
  return (
    <header className="topbar">
      <div className="topbar__left">
        <button className="icon-button topbar__menu" onClick={onOpenNav} aria-label="Open navigation">
          <Menu size={20} />
        </button>
        <p className="topbar__title">{titleForPath(pathname)}</p>
      </div>
      <div className="topbar__right">
        <ApiStatus />
        <UserMenu />
      </div>
    </header>
  )
}
