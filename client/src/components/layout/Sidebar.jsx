import { NavLink } from 'react-router-dom'
import { Sparkles, X } from 'lucide-react'
import { NAV_ITEMS } from './navigation'

export function Brand() {
  return (
    <div className="brand">
      <span className="brand__mark" aria-hidden="true">
        <Sparkles size={18} />
      </span>
      <span className="brand__name">
        Resume<span>IQ</span>
      </span>
    </div>
  )
}

export function Sidebar({ open, onClose }) {
  return (
    <>
      <div className={`sidebar-scrim ${open ? 'is-open' : ''}`} onClick={onClose} aria-hidden="true" />
      <aside className={`sidebar ${open ? 'is-open' : ''}`} aria-label="Main navigation">
        <div className="sidebar__header">
          <Brand />
          <button className="icon-button sidebar__close" onClick={onClose} aria-label="Close navigation">
            <X size={18} />
          </button>
        </div>

        <nav className="sidebar__nav">
          <p className="sidebar__section">Workspace</p>
          {NAV_ITEMS.map(({ to, label, icon: Icon, end }) => (
            <NavLink key={to} to={to} end={end} className={({ isActive }) => `nav-link ${isActive ? 'is-active' : ''}`}>
              <Icon size={18} aria-hidden="true" />
              <span>{label}</span>
            </NavLink>
          ))}
        </nav>

        <div className="sidebar__footer">
          <p>AI resume analysis powered by Gemini &amp; Qdrant.</p>
        </div>
      </aside>
    </>
  )
}
