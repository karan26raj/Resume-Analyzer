import { useState } from 'react'
import { Link, Navigate, useLocation, useNavigate } from 'react-router-dom'
import { ArrowRight, BrainCircuit, FileSearch, ShieldCheck } from 'lucide-react'
import { useAuth } from '../auth/AuthContext'
import { Brand } from '../components/layout/Sidebar'
import { TextField } from '../components/ui/Field'
import { InlineError, Spinner } from '../components/ui/States'

const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/

export function AuthPage({ mode }) {
  const isRegister = mode === 'register'
  const { status, login, register, sessionExpired } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [confirm, setConfirm] = useState('')
  const [touched, setTouched] = useState({})
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState(null)

  if (status === 'authenticated') {
    return <Navigate to={location.state?.from || '/'} replace />
  }

  // Validation mirrors the API: a valid email, and 8-100 character passwords on register.
  const errors = {
    email: !email ? 'Email is required' : !EMAIL_PATTERN.test(email) ? 'Enter a valid email address' : null,
    password: !password
      ? 'Password is required'
      : isRegister && password.length < 8
        ? 'Use at least 8 characters'
        : isRegister && password.length > 100
          ? 'Use at most 100 characters'
          : null,
    confirm: isRegister && confirm !== password ? 'Passwords do not match' : null,
  }
  const hasErrors = Object.values(errors).some(Boolean)

  const onSubmit = async (event) => {
    event.preventDefault()
    setTouched({ email: true, password: true, confirm: true })
    if (hasErrors) return
    setSubmitting(true)
    setError(null)
    try {
      if (isRegister) await register(email.trim(), password)
      else await login(email.trim(), password)
      navigate(location.state?.from || '/', { replace: true })
    } catch (err) {
      setError(err.status === 409 ? 'An account with this email already exists.' : err.message)
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="auth">
      <section className="auth__intro">
        <Brand />
        <h1>
          Career intelligence, <span className="accent-text">grounded in your documents.</span>
        </h1>
        <p>Upload resumes, save job descriptions and get evidence-based AI match analysis in seconds.</p>
        <ul className="auth__features">
          <li>
            <BrainCircuit size={18} /> Structured resume-to-job match scoring
          </li>
          <li>
            <FileSearch size={18} /> Semantic search across everything you upload
          </li>
          <li>
            <ShieldCheck size={18} /> Your documents stay private to your account
          </li>
        </ul>
      </section>

      <section className="auth__panel card card--glass">
        <h2>{isRegister ? 'Create your account' : 'Welcome back'}</h2>
        <p className="text-secondary">
          {isRegister ? 'Start analyzing your resume in minutes.' : 'Sign in to continue to your workspace.'}
        </p>

        {sessionExpired && !isRegister && (
          <p className="notice notice--info">Your session expired. Please sign in again.</p>
        )}

        <form onSubmit={onSubmit} noValidate className="form-stack">
          <TextField
            label="Email address"
            type="email"
            autoComplete="email"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            onBlur={() => setTouched((value) => ({ ...value, email: true }))}
            error={touched.email ? errors.email : null}
          />
          <TextField
            label="Password"
            type="password"
            autoComplete={isRegister ? 'new-password' : 'current-password'}
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            onBlur={() => setTouched((value) => ({ ...value, password: true }))}
            error={touched.password ? errors.password : null}
            hint={isRegister ? '8 to 100 characters' : undefined}
          />
          {isRegister && (
            <TextField
              label="Confirm password"
              type="password"
              autoComplete="new-password"
              value={confirm}
              onChange={(event) => setConfirm(event.target.value)}
              onBlur={() => setTouched((value) => ({ ...value, confirm: true }))}
              error={touched.confirm ? errors.confirm : null}
            />
          )}

          <InlineError>{error}</InlineError>

          <button type="submit" className="btn btn--primary btn--block btn--lg" disabled={submitting}>
            {submitting ? <Spinner size={16} /> : null}
            {isRegister ? 'Create account' : 'Sign in'}
            {!submitting && <ArrowRight size={18} />}
          </button>
        </form>

        <p className="auth__switch">
          {isRegister ? 'Already have an account?' : "Don't have an account?"}{' '}
          <Link to={isRegister ? '/login' : '/register'}>{isRegister ? 'Sign in' : 'Create one'}</Link>
        </p>
      </section>
    </div>
  )
}
