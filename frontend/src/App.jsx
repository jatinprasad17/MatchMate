import { Route, Routes } from 'react-router-dom'
import AuthSuccess from './pages/AuthSuccess.jsx'
import Dashboard from './pages/Dashboard.jsx'
import Home from './pages/Home.jsx'
import Login from './pages/Login.jsx'
import Onboarding from './pages/Onboarding.jsx'
import OnboardingSuccess from './pages/OnboardingSuccess.jsx'

function App() {
  return (
    <Routes>
      <Route path="/" element={<Login />} />
      <Route path="/onboarding" element={<Onboarding />} />
      <Route path="/onboarding/success" element={<OnboardingSuccess />} />
      <Route path="/dashboard" element={<Dashboard />} />
      <Route path="/home" element={<Home />} />
      <Route path="/auth/success" element={<AuthSuccess />} />
    </Routes>
  )
}

export default App
