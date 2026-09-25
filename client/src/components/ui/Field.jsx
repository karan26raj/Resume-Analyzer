import { useId } from 'react'

export function TextField({ label, error, hint, className = '', counter, ...props }) {
  const id = useId()
  const describedBy = error || hint ? `${id}-help` : undefined
  return (
    <div className={`field ${error ? 'field--invalid' : ''} ${className}`}>
      <div className="field__control">
        <input id={id} placeholder=" " aria-invalid={Boolean(error)} aria-describedby={describedBy} {...props} />
        <label htmlFor={id}>{label}</label>
      </div>
      <FieldFooter id={describedBy} error={error} hint={hint} counter={counter} />
    </div>
  )
}

export function TextArea({ label, error, hint, className = '', counter, rows = 8, ...props }) {
  const id = useId()
  const describedBy = error || hint ? `${id}-help` : undefined
  return (
    <div className={`field field--textarea ${error ? 'field--invalid' : ''} ${className}`}>
      <div className="field__control">
        <textarea
          id={id}
          rows={rows}
          placeholder=" "
          aria-invalid={Boolean(error)}
          aria-describedby={describedBy}
          {...props}
        />
        <label htmlFor={id}>{label}</label>
      </div>
      <FieldFooter id={describedBy} error={error} hint={hint} counter={counter} />
    </div>
  )
}

export function SelectField({ label, error, hint, className = '', children, ...props }) {
  const id = useId()
  const describedBy = error || hint ? `${id}-help` : undefined
  return (
    <div className={`field field--select ${error ? 'field--invalid' : ''} ${className}`}>
      <div className="field__control">
        <select id={id} aria-invalid={Boolean(error)} aria-describedby={describedBy} {...props}>
          {children}
        </select>
        <label htmlFor={id}>{label}</label>
      </div>
      <FieldFooter id={describedBy} error={error} hint={hint} />
    </div>
  )
}

function FieldFooter({ id, error, hint, counter }) {
  if (!error && !hint && !counter) return null
  return (
    <div className="field__footer">
      <span id={id} className={error ? 'field__error' : 'field__hint'}>
        {error || hint}
      </span>
      {counter && <span className={`field__counter ${counter.over ? 'field__counter--over' : ''}`}>{counter.text}</span>}
    </div>
  )
}
