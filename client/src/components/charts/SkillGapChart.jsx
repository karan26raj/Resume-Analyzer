import { useState } from 'react'

export function SkillGapChart({ skills, total }) {
  const [active, setActive] = useState(null)
  const max = Math.max(1, ...skills.map((item) => item.count))

  return (
    <ul className="bar-list" aria-label="Most frequent missing skills">
      {skills.map((item, index) => (
        <li
          key={item.skill}
          className={`bar-list__row ${active === index ? 'is-active' : ''}`}
          onMouseEnter={() => setActive(index)}
          onMouseLeave={() => setActive(null)}
          tabIndex={0}
          onFocus={() => setActive(index)}
          onBlur={() => setActive(null)}
          title={`${item.skill}: missing in ${item.count} of ${total} analyses`}
        >
          <span className="bar-list__label">{item.skill}</span>
          <span className="bar-list__track">
            <span className="bar-list__bar" style={{ width: `${(item.count / max) * 100}%` }} />
          </span>
          <span className="bar-list__value">{item.count}</span>
        </li>
      ))}
    </ul>
  )
}
