import { lazy, Suspense, useEffect, useState, type MouseEvent } from 'react'
import {
  ArrowDownRight,
  ArrowRight,
  ArrowUpRight,
  BarChart3,
  Check,
  ChevronDown,
  CircleHelp,
  Clock3,
  Menu,
  ShieldCheck,
  Sun,
  Wind,
  X,
  Zap,
} from 'lucide-react'
const Dashboard = lazy(() => import('./Dashboard'))

type ForecastPoint = { time: string; p10: number; p50: number; p90: number }

const dayData: ForecastPoint[] = [
  { time: '00', p10: 6280, p50: 6500, p90: 6790 },
  { time: '03', p10: 6140, p50: 6380, p90: 6700 },
  { time: '06', p10: 6250, p50: 6570, p90: 6930 },
  { time: '09', p10: 6680, p50: 7120, p90: 7540 },
  { time: '12', p10: 6900, p50: 7410, p90: 7850 },
  { time: '15', p10: 7010, p50: 7580, p90: 8060 },
  { time: '18', p10: 7140, p50: 7810, p90: 8290 },
  { time: '21', p10: 6820, p50: 7440, p90: 7980 },
  { time: '24', p10: 6510, p50: 7050, p90: 7620 },
]

const weekData: ForecastPoint[] = [
  { time: 'Mon', p10: 6100, p50: 6550, p90: 7120 },
  { time: 'Tue', p10: 6230, p50: 6710, p90: 7260 },
  { time: 'Wed', p10: 6300, p50: 6900, p90: 7510 },
  { time: 'Thu', p10: 6480, p50: 7160, p90: 7830 },
  { time: 'Fri', p10: 6550, p50: 7280, p90: 7980 },
  { time: 'Sat', p10: 6350, p50: 7050, p90: 7740 },
  { time: 'Sun', p10: 6200, p50: 6800, p90: 7480 },
]

function makeLinePath(rows: ForecastPoint[], key: 'p10' | 'p50' | 'p90') {
  const left = 45, right = 558, top = 12, bottom = 172, min = 6000, max = 8500
  return rows.map((row, index) => {
    const x = left + (index / Math.max(1, rows.length - 1)) * (right - left)
    const y = bottom - ((row[key] - min) / (max - min)) * (bottom - top)
    return `${index === 0 ? 'M' : 'L'}${x.toFixed(1)},${y.toFixed(1)}`
  }).join(' ')
}

function makeBandPath(rows: ForecastPoint[]) {
  const left = 45, right = 558, top = 12, bottom = 172, min = 6000, max = 8500
  const points = rows.map((row, index) => {
    const x = left + (index / Math.max(1, rows.length - 1)) * (right - left)
    const y90 = bottom - ((row.p90 - min) / (max - min)) * (bottom - top)
    const y10 = bottom - ((row.p10 - min) / (max - min)) * (bottom - top)
    return { x, y90, y10 }
  })
  return `${points.map((point, index) => `${index === 0 ? 'M' : 'L'}${point.x.toFixed(1)},${point.y90.toFixed(1)}`).join(' ')} ${points.reverse().map((point) => `L${point.x.toFixed(1)},${point.y10.toFixed(1)}`).join(' ')} Z`
}

function ForecastCard() {
  const [range, setRange] = useState<'24h' | '7d'>('24h')
  const rows = range === '24h' ? dayData : weekData
  const labels = range === '24h' ? ['00', '03', '06', '09', '12', '15', '18', '21', '24'] : ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
  const peakIndex = range === '24h' ? 6 : 4

  return (
    <div className="forecast-card" id="forecast-preview">
      <div className="forecast-card-head">
        <div>
          <span className="eyebrow">DEMAND OUTLOOK</span>
          <h2>Delhi system load</h2>
        </div>
        <div className="range-toggle" aria-label="Forecast range">
          <button className={range === '24h' ? 'selected' : ''} onClick={() => setRange('24h')} aria-pressed={range === '24h'}>24 hours</button>
          <button className={range === '7d' ? 'selected' : ''} onClick={() => setRange('7d')} aria-pressed={range === '7d'}>7 days</button>
        </div>
      </div>
      <div className="forecast-meta">
        <span><span className="status-dot" />Illustrative forecast</span>
        <span>Issued 09:00 IST</span>
      </div>
      <div className="chart-wrap" role="img" aria-label={`${range} probabilistic load forecast. Median demand peaks near 7,810 megawatts around 18:00; shaded area shows P10 to P90 uncertainty.`}>
        <svg viewBox="0 0 590 210" preserveAspectRatio="none" aria-hidden="true">
          <defs><linearGradient id="previewBand" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="#8a9270" stopOpacity=".28" /><stop offset="100%" stopColor="#8a9270" stopOpacity=".08" /></linearGradient></defs>
          {[6200, 6800, 7400, 8000, 8400].map((value) => {
            const y = 172 - ((value - 6000) / 2500) * 160
            return <g key={value}><line x1="45" x2="558" y1={y} y2={y} stroke="#e7dfd1" strokeDasharray="3 4" /><text x="38" y={y + 3} textAnchor="end" fill="#858477" fontSize="9">{(value / 1000).toFixed(1)}k</text></g>
          })}
          <path d={makeBandPath(rows)} fill="url(#previewBand)" />
          <path d={makeLinePath(rows, 'p50')} fill="none" stroke="#064e3b" strokeWidth="2.6" vectorEffect="non-scaling-stroke" />
          {rows.map((row, index) => {
            const x = 45 + (index / Math.max(1, rows.length - 1)) * 513
            const y = 172 - ((row.p50 - 6000) / 2500) * 160
            return <g key={labels[index]}><circle cx={x} cy={y} r={index === peakIndex ? 5 : 2.2} fill={index === peakIndex ? '#b65c3c' : '#064e3b'} stroke="#fffdf7" strokeWidth="1.5" /><text x={x} y="197" textAnchor="middle" fill="#858477" fontSize="8">{labels[index]}</text></g>
          })}
        </svg>
      </div>
      <div className="chart-legend">
        <span><i className="legend-band" />P10–P90 range</span>
        <span><i className="legend-line" />P50 median</span>
        <span><i className="legend-peak" />Peak watch</span>
        <button className="text-button" onClick={() => document.getElementById('how-it-works')?.scrollIntoView({ behavior: 'smooth' })}>How to read this <ArrowRight size={14} /></button>
      </div>
      <div className="chart-footnote">Illustrative data for product preview · Not an operational forecast</div>
    </div>
  )
}

function Header({ onOpenWorkspace }: { onOpenWorkspace: (event: MouseEvent<HTMLAnchorElement>) => void }) {
  const [open, setOpen] = useState(false)
  return (
    <header className="site-header">
      <a className="brand" href="#top" aria-label="Peakwise home">
        <span className="brand-mark"><span /><span /><span /></span>
        <span className="brand-word">peakwise<span className="brand-period">.</span></span>
      </a>
      <button className="menu-toggle" onClick={() => setOpen(!open)} aria-label={open ? 'Close menu' : 'Open menu'} aria-expanded={open}>{open ? <X /> : <Menu />}</button>
      <nav className={open ? 'main-nav nav-open' : 'main-nav'} aria-label="Main navigation">
        <a href="#platform" onClick={() => setOpen(false)}>Platform</a>
        <a href="#how-it-works" onClick={() => setOpen(false)}>How it works</a>
        <a href="#methodology" onClick={() => setOpen(false)}>Methodology</a>
        <a className="nav-cta" href="/dashboard" onClick={(event) => { setOpen(false); onOpenWorkspace(event) }}>Open workspace <ArrowRight size={15} /></a>
      </nav>
    </header>
  )
}

function Hero() {
  return (
    <section className="hero" id="top">
      <div className="hero-copy">
        <div className="hero-kicker"><span className="kicker-rule" />POWER SYSTEM INTELLIGENCE <span className="kicker-city">DELHI, INDIA</span></div>
        <h1>Plan for the<br /><em>hours that matter.</em></h1>
        <p className="hero-description">A clearer view of tomorrow’s demand. Probabilistic forecasts help power teams see peak risk earlier and compare decisions with the assumptions in plain sight.</p>
        <div className="hero-actions">
          <a className="button button-dark" href="#forecast-preview">Explore the forecast <ArrowRight size={17} /></a>
          <a className="button button-quiet" href="#how-it-works">See how it works <ArrowDownRight size={16} /></a>
        </div>
        <div className="hero-assurance"><ShieldCheck size={15} strokeWidth={1.7} /><span>Decision support, with uncertainty made visible.</span></div>
      </div>
      <div className="hero-product">
        <div className="product-window-bar">
          <div className="window-brand"><span className="window-brand-mark">P</span>PEAKWISE <span className="window-separator">/</span> OPERATIONS</div>
          <div className="window-status"><span className="status-dot" /> DEMO VIEW</div>
          <button className="window-help" aria-label="About this preview"><CircleHelp size={15} /></button>
        </div>
        <div className="product-window-content">
          <div className="product-greeting">
            <div><span className="eyebrow">WEDNESDAY, 12 NOVEMBER</span><h2>Good morning.</h2></div>
            <div className="region-chip"><span className="region-pulse" />Delhi system <ChevronDown size={13} /></div>
          </div>
          <div className="preview-metrics">
            <div className="preview-metric"><span>Forecast peak</span><strong>7,810 <small>MW</small></strong><span className="metric-note"><Clock3 size={12} /> Around 18:00 IST</span></div>
            <div className="preview-metric"><span>Peak watch</span><strong className="metric-risk">68<small>%</small></strong><span className="metric-note"><ArrowUpRight size={12} /> Above 7,600 MW</span></div>
            <div className="preview-weather"><div className="weather-icon"><Sun size={18} /></div><div><span>Afternoon outlook</span><strong>Warm · 38°</strong><span className="metric-note"><Wind size={12} /> Weather input preview</span></div></div>
          </div>
          <ForecastCard />
          <div className="product-window-footer"><span><i className="legend-line" />Median estimate</span><span>MW · hourly · local time</span></div>
        </div>
      </div>
      <div className="hero-aside"><span className="aside-index">01 / 03</span><span className="aside-line" /><span>FROM FORECAST<br />TO DECISION</span></div>
    </section>
  )
}

function ProofStrip() {
  return (
    <section className="proof-strip" aria-label="Product capabilities">
      <div className="proof-intro"><span className="eyebrow">BUILT FOR OPERATIONAL CLARITY</span><span>One view of the range,<br />the risk, and the choice.</span></div>
      <div className="proof-item"><span className="proof-number">01</span><div><strong>Probabilistic outlook</strong><span>P10 · P50 · P90</span></div></div>
      <div className="proof-item"><span className="proof-number">02</span><div><strong>Peak awareness</strong><span>Timing · magnitude · likelihood</span></div></div>
      <div className="proof-item"><span className="proof-number">03</span><div><strong>Scenario comparison</strong><span>Assumptions shown up front</span></div></div>
    </section>
  )
}

function Workflow() {
  const steps = [
    { number: '01', icon: <BarChart3 size={20} />, title: 'Read the range', body: 'See a median forecast alongside a lower and upper demand estimate. The uncertainty is part of the picture, not hidden behind one number.' },
    { number: '02', icon: <Zap size={20} />, title: 'Find the peak window', body: 'Bring likely high-load hours forward with timing, magnitude, and threshold context your team can inspect.' },
    { number: '03', icon: <Check size={20} />, title: 'Compare the choices', body: 'Explore schedule scenarios against explicit shortfall and surplus assumptions before taking a planning decision.' },
  ]
  return (
    <section className="workflow-section section-wrap" id="how-it-works">
      <div className="section-heading">
        <div><span className="eyebrow">A PRACTICAL WORKFLOW</span><h2>From uncertainty<br />to a better-informed plan.</h2></div>
        <p>Designed to support the people already balancing demand, schedules, and risk—without hiding the reasoning behind a recommendation.</p>
      </div>
      <div className="workflow-grid">
        {steps.map((step) => <article className="workflow-step" key={step.number}>
          <div className="step-top"><span className="step-number">{step.number}</span><span className="step-icon">{step.icon}</span></div>
          <h3>{step.title}</h3><p>{step.body}</p>
        </article>)}
      </div>
    </section>
  )
}

function PlatformSection() {
  return (
    <section className="platform-section" id="platform">
      <div className="platform-inner">
        <div className="platform-copy">
          <span className="eyebrow">BUILT AROUND REAL OPERATING QUESTIONS</span>
          <h2>Not just “how much?”<br /><em>“When, and how sure?”</em></h2>
          <p>Peakwise brings load forecasts, peak-event context, and procurement scenarios into one focused workspace. Each view is designed to answer a different planning question.</p>
          <a className="light-link" href="#forecast-preview">Explore the forecast view <ArrowRight size={16} /></a>
        </div>
        <div className="platform-details">
          <div className="detail-row"><span className="detail-label">01 / HORIZON</span><div><strong>Day-ahead to week-ahead</strong><p>Move between the next 24 hours and a broader seven-day outlook.</p></div><ArrowUpRight size={17} /></div>
          <div className="detail-row"><span className="detail-label">02 / EVENT</span><div><strong>Peak timing and scale</strong><p>Put likely high-demand periods in context with the expected range.</p></div><ArrowUpRight size={17} /></div>
          <div className="detail-row"><span className="detail-label">03 / DECISION</span><div><strong>Transparent scenarios</strong><p>Compare planning choices with editable, clearly labeled assumptions.</p></div><ArrowUpRight size={17} /></div>
        </div>
      </div>
    </section>
  )
}

function MethodologySection() {
  return (
    <section className="method-section section-wrap" id="methodology">
      <div className="method-topline"><span className="eyebrow">TRUST IS PART OF THE INTERFACE</span><span className="method-rule" /></div>
      <div className="method-content">
        <h2>Every forecast<br />needs its context.</h2>
        <div className="method-copy"><p>Forecasts are useful when teams can see what went into them and how they behaved on data they had not seen before. Peakwise is designed to put freshness, coverage, and cost assumptions within reach.</p>
          <div className="method-points"><span><Check size={15} /> Time-ordered backtesting</span><span><Check size={15} /> Data freshness and gaps</span><span><Check size={15} /> Explicit scenario assumptions</span></div>
          <div className="prototype-note"><span className="note-mark">i</span><p>This early product preview uses illustrative values. It is not connected to live SLDC feeds or an approved procurement tariff model.</p></div>
        </div>
      </div>
    </section>
  )
}

function Footer() {
  return (
    <footer className="site-footer">
      <a className="brand footer-brand" href="#top"><span className="brand-mark"><span /><span /><span /></span><span className="brand-word">peakwise<span className="brand-period">.</span></span></a>
      <span className="footer-caption">Probabilistic load forecasting · Delhi</span>
      <a href="#top" className="back-top">Back to top <ArrowUpRight size={14} /></a>
    </footer>
  )
}

export default function App() {
  const [dashboardOpen, setDashboardOpen] = useState(window.location.pathname.startsWith('/dashboard'))
  useEffect(() => {
    const syncPath = () => setDashboardOpen(window.location.pathname.startsWith('/dashboard'))
    window.addEventListener('popstate', syncPath)
    return () => window.removeEventListener('popstate', syncPath)
  }, [])
  const openDashboard = (event: MouseEvent<HTMLAnchorElement>) => {
    event.preventDefault()
    window.history.pushState({}, '', '/dashboard')
    setDashboardOpen(true)
    window.scrollTo(0, 0)
  }
  const backToLanding = () => {
    window.history.pushState({}, '', '/')
    setDashboardOpen(false)
    window.scrollTo(0, 0)
  }
  if (dashboardOpen) return <Suspense fallback={<div className="page-loading">Loading operations workspace…</div>}><Dashboard onBack={backToLanding} /></Suspense>
  return (
    <>
      <div className="announcement"><span>PRODUCT PREVIEW</span> Forecast and scenario values shown are illustrative. <a href="#methodology">About this demo <ArrowRight size={13} /></a></div>
      <Header onOpenWorkspace={openDashboard} />
      <main>
        <Hero />
        <ProofStrip />
        <Workflow />
        <PlatformSection />
        <MethodologySection />
        <section className="closing-cta">
          <span className="eyebrow">PEAKWISE · DELHI LOAD OUTLOOK</span>
          <h2>Make room for<br /><em>the unexpected.</em></h2>
          <p>Explore the forecast range and see how a peak-aware view can support tomorrow’s planning.</p>
          <a className="button button-cream" href="#forecast-preview">View the product preview <ArrowRight size={16} /></a>
        </section>
      </main>
      <Footer />
    </>
  )
}
