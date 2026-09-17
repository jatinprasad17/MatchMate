import { useEffect, useState } from 'react'
import { Circle, Gauge, X } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import Nav from '../components/Nav.jsx'

const API_URL = 'http://localhost:8000'

function Dashboard() {
  const navigate = useNavigate()
  const userId = localStorage.getItem('matchmate_user_id') || ''
  const [follows, setFollows] = useState([])
  const [loading, setLoading] = useState(true)
  const [removeErrors, setRemoveErrors] = useState({})

  useEffect(() => {
    const loadFollows = async () => {
      try {
        const response = await fetch(`${API_URL}/follows/${userId}`)
        if (!response.ok) throw new Error('Unable to load teams.')
        setFollows(await response.json())
      } catch (error) {
        console.error(error)
        setFollows([])
      } finally {
        setLoading(false)
      }
    }

    loadFollows()
  }, [userId])

  const removeFollow = async (followId) => {
    setRemoveErrors((current) => ({ ...current, [followId]: '' }))

    try {
      const response = await fetch(`${API_URL}/follows/${followId}`, { method: 'DELETE' })
      if (!response.ok) throw new Error('delete failed')
      setFollows((current) => current.filter((follow) => follow.id !== followId))
    } catch (error) {
      console.error(error)
      setRemoveErrors((current) => ({ ...current, [followId]: "Couldn't remove this team." }))
    }
  }

  const sportIcon = (sport) => {
    if (sport === 'f1') return <Gauge size={20} color="var(--accent)" />
    return <Circle size={20} color="var(--accent)" />
  }

  return (
    <div style={{ background: 'var(--bg)', color: 'var(--text)', minHeight: '100vh' }}>
      <Nav />
      <main style={{ boxSizing: 'border-box', margin: '0 auto', maxWidth: '620px', padding: '40px 20px' }}>
      <section
        style={{
          background: 'var(--surface)',
          border: '1px solid var(--border)',
          borderRadius: '8px',
          boxSizing: 'border-box',
          margin: '0 auto',
          maxWidth: '620px',
          padding: '32px',
        }}
      >
        <p style={{ color: 'var(--text-muted)', fontSize: '14px', margin: '0 0 8px' }}>
          Next digest: Sunday
        </p>
        <h1 style={{ fontSize: '18px', fontWeight: 500, margin: '0 0 20px' }}>
          Manage your teams
        </h1>

        {loading ? (
          <p style={{ color: 'var(--text-muted)' }}>Loading your teams...</p>
        ) : follows.length === 0 ? (
          <p style={{ color: 'var(--text-muted)' }}>No teams followed yet.</p>
        ) : (
          <div>
            {follows.map((follow) => (
              <div
                key={follow.id}
                style={{
                  alignItems: 'center',
                  borderBottom: '1px solid var(--border)',
                  display: 'flex',
                  justifyContent: 'space-between',
                  padding: '12px 0',
                }}
              >
                <div style={{ alignItems: 'center', display: 'flex', gap: '10px' }}>
                  {sportIcon(follow.sport)}
                  <span>{follow.team_or_player}</span>
                </div>
                <div style={{ alignItems: 'center', display: 'flex', gap: '8px' }}>
                  {removeErrors[follow.id] && (
                    <span style={{ color: 'var(--accent)', fontSize: '12px' }}>
                      {removeErrors[follow.id]}
                    </span>
                  )}
                  <button
                    type="button"
                    aria-label={`Remove ${follow.team_or_player}`}
                    onClick={() => removeFollow(follow.id)}
                    style={{
                      background: 'transparent',
                      border: 'none',
                      color: 'var(--text-muted)',
                      cursor: 'pointer',
                      padding: '4px',
                    }}
                  >
                    <X size={18} />
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}

        <button
          type="button"
          onClick={() => navigate('/onboarding?mode=add')}
          style={{
            background: 'var(--accent)',
            border: 'none',
            borderRadius: '8px',
            color: 'var(--accent-text)',
            cursor: 'pointer',
            font: 'inherit',
            marginTop: '28px',
            padding: '12px 20px',
            width: '100%',
          }}
        >
          Add another team
        </button>

      </section>
      </main>
    </div>
  )
}

export default Dashboard
