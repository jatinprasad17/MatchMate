import { useEffect, useState } from 'react'
import { Circle, Gauge } from 'lucide-react'
import Nav from '../components/Nav.jsx'
import formatDate from '../utils/formatDate.js'

const API_URL = import.meta.env.VITE_API_URL

function Home() {
  const userId = localStorage.getItem('matchmate_user_id') || ''
  const [follows, setFollows] = useState([])
  const [matches, setMatches] = useState([])
  const [loadingFollows, setLoadingFollows] = useState(true)
  const [loadingMatches, setLoadingMatches] = useState(true)

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
        setLoadingFollows(false)
      }
    }

    loadFollows()
  }, [userId])

  useEffect(() => {
    const loadMatches = async () => {
      try {
        const response = await fetch(`${API_URL}/matches/${userId}`)
        if (!response.ok) throw new Error('Unable to load matches.')
        const data = await response.json()
        setMatches(data.matches || [])
      } catch (error) {
        console.error(error)
        setMatches([])
      } finally {
        setLoadingMatches(false)
      }
    }

    loadMatches()
  }, [userId])

  const sportIcon = (sport) => (
    sport === 'f1'
      ? <Gauge size={20} color="var(--accent)" />
      : <Circle size={20} color="var(--accent)" />
  )

  return (
    <div style={{ background: 'var(--bg)', color: 'var(--text)', minHeight: '100vh' }}>
      <Nav />
      <main style={{ boxSizing: 'border-box', margin: '0 auto', maxWidth: '620px', padding: '40px 20px' }}>
        <p style={{ color: 'var(--text-muted)', fontSize: '14px', margin: '0 0 8px' }}>
          Next digest: Sunday
        </p>
        <h1 style={{ fontSize: '18px', fontWeight: 500, margin: '0 0 20px' }}>Your teams</h1>

        {loadingFollows ? (
          <p style={{ color: 'var(--text-muted)' }}>Loading your teams...</p>
        ) : follows.length === 0 ? (
          <p style={{ color: 'var(--text-muted)' }}>No teams followed yet.</p>
        ) : (
          <div>
            {follows.map((follow) => (
              <div key={follow.id} style={{ alignItems: 'center', borderBottom: '1px solid var(--border)', display: 'flex', gap: '10px', padding: '12px 0' }}>
                {sportIcon(follow.sport)}
                <span>{follow.team_or_player}</span>
              </div>
            ))}
          </div>
        )}

        <section style={{ borderTop: '1px solid var(--border)', marginTop: '32px', paddingTop: '24px' }}>
          <h2 style={{ fontSize: '18px', fontWeight: 500, margin: '0 0 16px' }}>This week</h2>
          {loadingMatches ? (
            <p style={{ color: 'var(--text-muted)' }}>Loading matches...</p>
          ) : matches.length === 0 ? (
            <p style={{ color: 'var(--text-muted)' }}>No matches this week.</p>
          ) : (
            matches.map((match, index) => (
              <div key={`${match.sport}-${match.date}-${index}`} style={{ borderBottom: '1px solid var(--border)', padding: '12px 0' }}>
                <div style={{ fontSize: '14px' }}>
                  {match.sport === 'f1' ? match.race_name : `${match.followed_team} vs ${match.opponent}`}
                </div>
                <div style={{ color: 'var(--text-muted)', fontSize: '13px', marginTop: '4px' }}>
                  {formatDate(match.date)}
                </div>
              </div>
            ))
          )}
        </section>
      </main>
    </div>
  )
}

export default Home
