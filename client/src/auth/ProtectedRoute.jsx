import { Navigate, Outlet, useLocation } from 'react-router-dom'
import { useAuth } from './AuthContext'
import { ErrorState, Spinner } from '../components/ui/States'

export function ProtectedRoute() {
  const { status, retry, logout } = useAuth()
  const location = useLocation()

  if (status === 'anonymous') {
    return <Navigate to="/login" replace state={{ from: location.pathname }} />
  }

  if (status === 'loading') {
    return (
      <div className="fullscreen-center">
        <Spinner size={28} label="Loading your workspace" />
      </div>
    )
  }

  if (status === 'error') {
    return (
      <div className="fullscreen-center">
        <div className="card card--glass" style={{ maxWidth: 440 }}>
          <ErrorState
            title="Can't reach the API"
            error={{ message: 'Make sure the FastAPI server is running on port 8000, then try again.' }}
            onRetry={retry}
          />
          <button className="btn btn--ghost btn--block" onClick={() => logout()}>
            Sign out
          </button>
        </div>
      </div>
    )
  }

  return <Outlet />
}
