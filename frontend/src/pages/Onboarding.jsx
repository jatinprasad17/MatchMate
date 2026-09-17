import { useEffect, useState } from 'react'
import { X } from 'lucide-react'
import { useNavigate, useSearchParams } from 'react-router-dom'

const API_URL = 'http://localhost:8000'

function Onboarding() {
  const userId = localStorage.getItem('matchmate_user_id') || ''
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const isAddMode = searchParams.get('mode') === 'add'
  const [geminiKey, setGeminiKey] = useState('')
  const [sport, setSport] = useState('')
  const [selectedTeam, setSelectedTeam] = useState('')
  const [teams, setTeams] = useState([])
  const [existingFollows, setExistingFollows] = useState([])
  const [addedTeams, setAddedTeams] = useState([])
  const [loadingTeams, setLoadingTeams] = useState(false)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const [geminiKeyError, setGeminiKeyError] = useState('')
  const [teamsError, setTeamsError] = useState('')

  useEffect(() => {
    if (!isAddMode || !userId) return

    const loadExistingFollows = async () => {
      try {
        const response = await fetch(`${API_URL}/follows/${userId}`)
        if (!response.ok) throw new Error('Unable to load your existing teams.')
        setExistingFollows(await response.json())
      } catch (fetchError) {
        setError(fetchError.message)
      }
    }

    loadExistingFollows()
  }, [isAddMode, userId])

  useEffect(() => {
    if (!sport) {
      setTeams([])
      setSelectedTeam('')
      return
    }

    const loadTeams = async () => {
      setLoadingTeams(true)
      setError('')
      setSelectedTeam('')

      try {
        const response = await fetch(`${API_URL}/teams?sport=${sport}`)
        if (!response.ok) throw new Error('Unable to load teams.')
        const data = await response.json()
        setTeams(data.teams || [])
      } catch (fetchError) {
        setTeams([])
        setError(fetchError.message)
      } finally {
        setLoadingTeams(false)
      }
    }

    loadTeams()
  }, [sport])

  const isAdded = (team) => addedTeams.some((item) => item.sport === sport && item.team === team)
  const isAlreadyFollowed = (team) => existingFollows.some(
    (follow) => follow.sport === sport && follow.team_or_player === team,
  )

  const addTeam = () => {
    if (selectedTeam && !isAdded(selectedTeam)) {
      setAddedTeams((current) => [...current, { sport, team: selectedTeam }])
      setSelectedTeam('')
    }
  }

  const removeTeam = (teamToRemove) => {
    setAddedTeams((current) => current.filter(
      (item) => item.sport !== teamToRemove.sport || item.team !== teamToRemove.team,
    ))
  }

  const handleDone = async () => {
    if (!isAddMode && !geminiKey.trim()) {
      setGeminiKeyError('Enter your Gemini API key to continue.')
      return
    }

    if (addedTeams.length === 0) {
      setTeamsError('Add at least one team.')
      return
    }

    setSaving(true)
    setError('')
    setTeamsError('')

    try {
      if (!isAddMode) {
        const geminiResponse = await fetch(`${API_URL}/users/${userId}/gemini-key`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ api_key: geminiKey }),
        })
        if (!geminiResponse.ok) throw new Error("Couldn't save your API key.")
      }

      for (const team of addedTeams) {
        const followResponse = await fetch(`${API_URL}/follows`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            user_id: userId,
            sport: team.sport,
            team_or_player: team.team,
          }),
        })
        if (!followResponse.ok) throw new Error(`Couldn't save ${team.team}.`)
      }

      const syncResponse = await fetch(`${API_URL}/sync-calendar/${userId}`, {
        method: 'POST',
      })
      if (!syncResponse.ok) throw new Error("Couldn't sync your calendar.")

      navigate('/onboarding/success')
    } catch (submitError) {
      setError(submitError.message)
    } finally {
      setSaving(false)
    }
  }

  const inputStyle = {
    background: 'var(--bg)',
    border: '1px solid var(--border)',
    borderRadius: '6px',
    boxSizing: 'border-box',
    color: 'var(--text)',
    display: 'block',
    font: 'inherit',
    marginTop: '8px',
    padding: '11px 12px',
    width: '100%',
  }

  return (
    <main style={{ background: 'var(--bg)', boxSizing: 'border-box', color: 'var(--text)', minHeight: '100vh', padding: '40px 20px' }}>
      <section style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: '8px', boxSizing: 'border-box', margin: '0 auto', maxWidth: '620px', padding: '32px' }}>
        <h1 style={{ fontSize: '28px', fontWeight: 500, margin: '0 0 8px' }}>Set up your weekly digest</h1>
        <p style={{ color: 'var(--text-muted)', margin: '0 0 28px' }}>Choose the teams and drivers you want to follow.</p>

        {!isAddMode && (
          <label style={{ display: 'block', fontSize: '14px', fontWeight: 600 }}>
            Your Gemini API key
            <span style={{ color: 'var(--text-muted)', display: 'block', fontSize: '12px', fontWeight: 400, marginTop: '4px' }}>
              Used to generate your weekly digest.
            </span>
            <input type="password" value={geminiKey} onChange={(event) => { setGeminiKey(event.target.value); setGeminiKeyError('') }} placeholder="Paste your API key" style={inputStyle} />
            {geminiKeyError && <span style={{ color: 'var(--accent)', display: 'block', fontSize: '13px', marginTop: '6px' }}>{geminiKeyError}</span>}
          </label>
        )}

        <label style={{ display: 'block', fontSize: '14px', fontWeight: 600, marginTop: '24px' }}>
          Sport
          <select value={sport} onChange={(event) => setSport(event.target.value)} style={inputStyle}>
            <option value="">Choose a sport</option>
            <option value="football">Football</option>
            <option value="f1">F1</option>
          </select>
        </label>

        {sport && (
          <div style={{ marginTop: '24px' }}>
            <label style={{ display: 'block', fontSize: '14px', fontWeight: 600 }}>
              Team
              <select value={selectedTeam} onChange={(event) => setSelectedTeam(event.target.value)} style={inputStyle}>
                <option value="">Choose a team</option>
                {teams
                  .filter((team) => !isAlreadyFollowed(team))
                  .map((team) => (
                  <option key={team} value={team} disabled={isAdded(team)}>
                    {team}{isAdded(team) ? ' (added)' : ''}
                  </option>
                ))}
              </select>
            </label>
            <div style={{ alignItems: 'center', display: 'flex', gap: '10px', marginTop: '12px' }}>
              {loadingTeams && <span style={{ color: 'var(--text-muted)', fontSize: '13px' }}>Loading teams...</span>}
              {error && <span style={{ color: 'var(--accent)', fontSize: '13px' }}>{error}</span>}
              {!loadingTeams && !error && (
                <button type="button" onClick={addTeam} disabled={!selectedTeam || isAdded(selectedTeam)} style={{ background: 'var(--accent)', border: 'none', borderRadius: '6px', color: 'var(--accent-text)', cursor: selectedTeam ? 'pointer' : 'not-allowed', padding: '9px 16px' }}>
                  Add
                </button>
              )}
            </div>
          </div>
        )}

        <div style={{ borderTop: '1px solid var(--border)', marginTop: '28px', paddingTop: '24px' }}>
          <h2 style={{ fontSize: '18px', fontWeight: 500, margin: '0 0 12px' }}>Your teams</h2>
          {addedTeams.length === 0 ? (
            <p style={{ color: 'var(--text-muted)', margin: 0 }}>No teams added yet.</p>
          ) : addedTeams.map((item) => (
            <div key={`${item.sport}-${item.team}`} style={{ alignItems: 'center', display: 'flex', justifyContent: 'space-between', padding: '8px 0' }}>
              <span>{item.team} <small style={{ color: 'var(--text-muted)' }}>({item.sport})</small></span>
              <button type="button" onClick={() => removeTeam(item)} aria-label={`Remove ${item.team}`} style={{ background: 'transparent', border: 'none', color: 'var(--text-muted)', cursor: 'pointer', padding: '4px' }}>
                <X size={18} />
              </button>
            </div>
          ))}
          {teamsError && <p style={{ color: 'var(--accent)', fontSize: '14px', margin: '12px 0 0' }}>{teamsError}</p>}
        </div>

        {error && <p style={{ color: 'var(--accent)', fontSize: '14px', margin: '20px 0 0' }}>{error}</p>}
        <button type="button" onClick={handleDone} disabled={saving} style={{ background: 'var(--accent)', border: 'none', borderRadius: '8px', color: 'var(--accent-text)', cursor: saving ? 'not-allowed' : 'pointer', font: 'inherit', marginTop: '28px', opacity: saving ? 0.7 : 1, padding: '12px 20px', width: '100%' }}>
          {saving ? 'Setting things up...' : isAddMode ? 'Add teams' : 'Done, sync my calendar'}
        </button>
      </section>
    </main>
  )
}

export default Onboarding
