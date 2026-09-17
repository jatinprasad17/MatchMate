import { CheckCircle } from 'lucide-react'
import { useNavigate } from 'react-router-dom'

function OnboardingSuccess() {
  const navigate = useNavigate()

  return (
    <main
      style={{
        alignItems: 'center',
        background: 'var(--bg)',
        color: 'var(--text)',
        display: 'flex',
        flexDirection: 'column',
        height: '100vh',
        justifyContent: 'center',
        padding: '20px',
        textAlign: 'center',
      }}
    >
      <CheckCircle size={48} color="var(--accent)" />
      <h1 style={{ fontSize: '20px', fontWeight: 500, margin: '16px 0 8px' }}>
        All set!
      </h1>
      <p style={{ color: 'var(--text-muted)', fontSize: '14px', margin: '0 0 24px' }}>
        Events added to your calendar. We'll send your first digest this Sunday.
      </p>
      <button
        type="button"
        onClick={() => navigate('/dashboard')}
        style={{
          background: 'var(--accent)',
          border: 'none',
          borderRadius: '8px',
          color: 'var(--accent-text)',
          cursor: 'pointer',
          padding: '12px 24px',
        }}
      >
        Go to Dashboard
      </button>
    </main>
  )
}

export default OnboardingSuccess