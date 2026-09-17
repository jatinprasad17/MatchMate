import { useEffect } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'

function AuthSuccess() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const userId = searchParams.get('user_id') || ''
  const isNewUser = searchParams.get('is_new_user') || ''

  useEffect(() => {
    if (userId) {
      localStorage.setItem('matchmate_user_id', userId)
    }

    navigate(isNewUser === 'true' ? '/onboarding' : '/home', { replace: true })
  }, [isNewUser, navigate, userId])

  return (
    <div>
      <p>Setting things up...</p>
    </div>
  )
}

export default AuthSuccess
