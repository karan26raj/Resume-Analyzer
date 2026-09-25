import {
  BarChart3,
  Bot,
  BriefcaseBusiness,
  FileText,
  LayoutDashboard,
  PenLine,
  ScanSearch,
  Settings,
  Target,
} from 'lucide-react'

export const NAV_ITEMS = [
  { to: '/', label: 'Dashboard', icon: LayoutDashboard, end: true },
  { to: '/resumes', label: 'Resumes', icon: FileText },
  { to: '/jobs', label: 'Jobs', icon: BriefcaseBusiness },
  { to: '/analysis', label: 'Analysis', icon: BarChart3 },
  { to: '/matches', label: 'Job Matches', icon: Target },
  { to: '/rewrite', label: 'Resume Rewrite', icon: PenLine },
  { to: '/search', label: 'Semantic Search', icon: ScanSearch },
  { to: '/assistant', label: 'AI Assistant', icon: Bot },
  { to: '/settings', label: 'Settings', icon: Settings },
]

export function titleForPath(pathname) {
  const match = NAV_ITEMS.filter((item) => (item.end ? pathname === item.to : pathname.startsWith(item.to)))
  return match.length ? match[match.length - 1].label : 'ResumeIQ'
}
