import { Navigate, useLocation } from 'react-router-dom'
import { useAuth } from '../lib/AuthContext'

export default function ProtectedRoute({ children }) {
  const { isAuthed, loading } = useAuth()
  const location = useLocation()

  if (loading) {
    return (
      <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', fontFamily: 'var(--mono)', color: 'var(--text3)', fontSize: '0.85rem' }}>
        Verifying session…
      </div>
    )
  }
  if (!isAuthed) {
    return <Navigate to="/login" replace state={{ from: location.pathname }} />
  }
  return children
}
