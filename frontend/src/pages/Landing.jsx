import { useNavigate } from 'react-router-dom'
import Nav from '../components/Nav'
import Hero from '../components/Hero'
import TrackerMarquee from '../components/TrackerMarquee'
import StatsCounter from '../components/StatsCounter'
import Problem from '../components/Problem'
import HowItWorks from '../components/HowItWorks'
import SpeedCompare from '../components/SpeedCompare'
import Coverage from '../components/Coverage'
import Pricing from '../components/Pricing'
import FinalCTA from '../components/FinalCTA'
import Footer from '../components/Footer'

export default function Landing() {
  const navigate = useNavigate()
  const goSignup = () => navigate('/signup')
  const goHome = () => window.scrollTo({ top: 0, behavior: 'smooth' })

  return (
    <>
      <Nav onLogoClick={goHome} onSignIn={() => navigate('/login')} onGetStarted={goSignup} />
      <Hero onGetStarted={goSignup} />
      <TrackerMarquee />
      <StatsCounter />
      <Problem />
      <HowItWorks />
      <SpeedCompare />
      <Coverage />
      <Pricing onGetStarted={goSignup} />
      <FinalCTA onGetStarted={goSignup} />
      <Footer />
    </>
  )
}
