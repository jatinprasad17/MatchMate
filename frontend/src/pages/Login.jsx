import { Trophy } from 'lucide-react'

function Login() {
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
      }}
    >
      <Trophy size={40} color="var(--accent)" />
      <h1 style={{ fontSize: '24px', fontWeight: 500, margin: '16px 0 8px' }}>
        MatchMate
      </h1>
      <p style={{ color: 'var(--text-muted)', fontSize: '14px', margin: '0 0 24px' }}>
        Follow your teams, get a weekly recap.
      </p>
      <button
        type="button"
        onClick={() => {
          window.location.href = 'http://localhost:8000/auth/google/start'
        }}
        style={{
          background: 'var(--accent)',
          border: 'none',
          borderRadius: '8px',
          color: 'var(--accent-text)',
          cursor: 'pointer',
          fontSize: '14px',
          padding: '12px 24px',
        }}
      >
        Sign in with Google
      </button>
    </main>
  )
}

export default Login
