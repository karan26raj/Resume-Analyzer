import { Link } from 'react-router-dom'
import { EmptyState } from '../components/ui/States'
import { SearchIllustration } from '../components/ui/Illustrations'

export function NotFoundPage() {
  return (
    <div className="card">
      <EmptyState
        illustration={SearchIllustration}
        title="Page not found"
        description="The page you are looking for does not exist."
        action={
          <Link to="/" className="btn btn--primary">
            Back to dashboard
          </Link>
        }
      />
    </div>
  )
}
