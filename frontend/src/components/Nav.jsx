import { Link, useNavigate } from 'react-router-dom'

function Nav() {
  const navigate = useNavigate()

  const logout = () => {
    localStorage.removeItem('matchmate_user_id')
    navigate('/')
  }

  return (
    <nav
      style={{
        alignItems: 'center',
        background: 'var(--bg)',
        borderBottom: '1px solid var(--border)',
        boxSizing: 'border-box',
        display: 'flex',
        justifyContent: 'space-between',
        padding: '16px 24px',
      }}
    >
      <Link to="/home" style={{ color: 'var(--text)', fontSize: '15px', fontWeight: 500, textDecoration: 'none' }}>
        MatchMate
      </Link>
      <div style={{ alignItems: 'center', display: 'flex', gap: '20px' }}>
        <Link
          to="/dashboard"
          style={{ color: 'var(--text)', fontSize: '14px', textDecoration: 'none' }}
        >
          Dashboard
        </Link>
        <button
          type="button"
          onClick={logout}
          style={{ background: 'transparent', border: 'none', color: 'var(--text-muted)', cursor: 'pointer', font: 'inherit', fontSize: '14px', padding: 0 }}
        >
          Logout
        </button>
      </div>
    </nav>
  )
}

export default Nav
