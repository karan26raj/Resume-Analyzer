// Small line illustrations for empty states. Decorative only (aria-hidden).
const common = {
  width: 120,
  height: 96,
  viewBox: '0 0 120 96',
  fill: 'none',
  'aria-hidden': true,
  className: 'illustration',
}

function Defs({ id }) {
  return (
    <defs>
      <linearGradient id={id} x1="0" y1="0" x2="1" y2="1">
        <stop offset="0" stopColor="var(--accent)" />
        <stop offset="1" stopColor="var(--accent)" />
      </linearGradient>
    </defs>
  )
}

export function DocumentIllustration() {
  return (
    <svg {...common}>
      <Defs id="ill-doc" />
      <rect x="30" y="10" width="52" height="68" rx="8" className="ill-fill" />
      <rect x="38" y="18" width="52" height="68" rx="8" className="ill-card" stroke="url(#ill-doc)" strokeWidth="1.5" />
      <path d="M48 36h32M48 46h32M48 56h20" className="ill-line" strokeWidth="2" strokeLinecap="round" />
      <circle cx="88" cy="74" r="12" className="ill-card" stroke="url(#ill-doc)" strokeWidth="1.5" />
      <path d="M88 69v10M83 74h10" stroke="url(#ill-doc)" strokeWidth="2" strokeLinecap="round" />
    </svg>
  )
}

export function BriefcaseIllustration() {
  return (
    <svg {...common}>
      <Defs id="ill-job" />
      <rect x="24" y="30" width="72" height="48" rx="9" className="ill-card" stroke="url(#ill-job)" strokeWidth="1.5" />
      <path d="M46 30v-6a5 5 0 0 1 5-5h18a5 5 0 0 1 5 5v6" stroke="url(#ill-job)" strokeWidth="1.5" />
      <path d="M24 50h72" className="ill-line" strokeWidth="1.5" />
      <rect x="54" y="45" width="12" height="10" rx="3" className="ill-fill" stroke="url(#ill-job)" strokeWidth="1.5" />
    </svg>
  )
}

export function ChartIllustration() {
  return (
    <svg {...common}>
      <Defs id="ill-chart" />
      <rect x="18" y="14" width="84" height="66" rx="10" className="ill-card" />
      <path d="M30 66h60" className="ill-line" strokeWidth="1.5" />
      <path d="M36 62V46M50 62V36M64 62V50M78 62V28" stroke="url(#ill-chart)" strokeWidth="6" strokeLinecap="round" />
    </svg>
  )
}

export function SearchIllustration() {
  return (
    <svg {...common}>
      <Defs id="ill-search" />
      <rect x="16" y="20" width="62" height="10" rx="5" className="ill-fill" />
      <rect x="16" y="38" width="46" height="10" rx="5" className="ill-fill" />
      <rect x="16" y="56" width="54" height="10" rx="5" className="ill-fill" />
      <circle cx="80" cy="50" r="17" className="ill-card" stroke="url(#ill-search)" strokeWidth="2" />
      <path d="M92 62l12 12" stroke="url(#ill-search)" strokeWidth="3" strokeLinecap="round" />
    </svg>
  )
}

export function ChatIllustration() {
  return (
    <svg {...common}>
      <Defs id="ill-chat" />
      <rect x="14" y="16" width="60" height="36" rx="12" className="ill-card" stroke="url(#ill-chat)" strokeWidth="1.5" />
      <path d="M26 30h36M26 40h22" className="ill-line" strokeWidth="2" strokeLinecap="round" />
      <rect x="46" y="46" width="60" height="32" rx="12" className="ill-fill" />
      <circle cx="64" cy="62" r="3" fill="url(#ill-chat)" />
      <circle cx="76" cy="62" r="3" fill="url(#ill-chat)" />
      <circle cx="88" cy="62" r="3" fill="url(#ill-chat)" />
    </svg>
  )
}

export function ErrorIllustration() {
  return (
    <svg {...common}>
      <rect x="22" y="16" width="76" height="60" rx="12" className="ill-card" />
      <path d="M60 32v18" stroke="var(--status-critical)" strokeWidth="3" strokeLinecap="round" />
      <circle cx="60" cy="60" r="2.5" fill="var(--status-critical)" />
    </svg>
  )
}
