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
        <span><span className="status-dot" />Illustrative example</span>
        <span>Sample issue · 09:00 IST</span>
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
      <div className="chart-footnote">Sample values for the landing-page preview · Open the workspace for connected forecast data</div>
    </div>
  )
}

function Header({ onOpenWorkspace }: { onOpenWorkspace: (event: MouseEvent<HTMLAnchorElement>) => void }) {
  const [open, setOpen] = useState(false)
  return (
    <header className="site-header">
      <a className="brand" href="#top" aria-label="LoadIQ home">
        <span className="brand-mark"><span /><span /><span /></span>
        <span className="brand-word">LoadIQ<span className="brand-period">.</span></span>
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

function Hero({ onOpenWorkspace }: { onOpenWorkspace: (event: MouseEvent<HTMLAnchorElement>) => void }) {
  return (
    <section className="hero hero-flow" id="top">
      <div className="hero-copy">
        <div className="hero-kicker"><span className="kicker-rule" />DAY-AHEAD LOAD PLANNING <span className="kicker-city">DELHI, INDIA</span></div>
        <h1>See the peak<br /><em>before it arrives.</em></h1>
        <p className="hero-description">See a range of possible demand, spot the hours that may matter most, and compare schedule scenarios before making a plan.</p>
        <div className="hero-actions">
          <a className="button button-dark" href="/dashboard" onClick={onOpenWorkspace}>Explore the workspace <ArrowRight size={17} /></a>
          <a className="button button-quiet" href="#how-it-works">How it works <ArrowDownRight size={16} /></a>
        </div>
        <div className="hero-assurance"><ShieldCheck size={15} strokeWidth={1.7} /><span>Planning support for people who make the schedule.</span></div>
      </div>
      <div className="hero-product">
        <div className="product-window-bar">
          <div className="window-brand"><span className="window-brand-mark">L</span>LOADIQ <span className="window-separator">/</span> OPERATIONS</div>
          <div className="window-status"><span className="status-dot" /> PRODUCT PREVIEW</div>
          <button className="window-help" aria-label="About this preview"><CircleHelp size={15} /></button>
        </div>
        <div className="product-window-content">
          <div className="product-greeting">
            <div><span className="eyebrow">NEXT-DAY OUTLOOK · EXAMPLE</span><h2>Delhi system demand</h2></div>
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

function ForecastStory({ onOpenForecast }: { onOpenForecast: (event: MouseEvent<HTMLAnchorElement>) => void }) {
  return (
    <section className="forecast-story section-wrap" id="forecast-range">
      <div className="story-copy">
        <span className="eyebrow">A RANGE, NOT A GUESS</span>
        <h2>One forecast.<br /><em>Three useful views.</em></h2>
        <p>A middle estimate helps with everyday planning. Lower and higher estimates show how much demand could vary around it, so staff can consider the risk before choosing a schedule.</p>
        <a className="story-link" href="/dashboard/forecast" onClick={onOpenForecast}>Explore forecast details <ArrowRight size={15} /></a>
      </div>
      <div className="quantile-demo" aria-label="Illustrative demand forecast range">
        <div className="quantile-demo-head"><span>ILLUSTRATIVE EVENING PEAK</span><span>MW · LOCAL TIME</span></div>
        <div className="quantile-range-visual"><span className="range-track" /><span className="range-band" /><span className="range-marker marker-p10" /><span className="range-marker marker-p50" /><span className="range-marker marker-p90" /></div>
        <div className="quantile-values"><div><span>P10 · LOWER</span><b>7,140 <small>MW</small></b></div><div><span>P50 · MIDDLE</span><b>7,810 <small>MW</small></b></div><div><span>P90 · HIGHER</span><b>8,320 <small>MW</small></b></div></div>
        <div className="quantile-time"><Clock3 size={14} /><span>Possible peak window</span><b>17:00–19:00</b></div>
        <p className="quantile-disclaimer">Example values only. Forecast uncertainty is part of the planning picture.</p>
      </div>
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

function PlatformSection({ onOpenWorkspace }: { onOpenWorkspace: (event: MouseEvent<HTMLAnchorElement>) => void }) {
  return (
    <section className="platform-section" id="platform">
      <div className="platform-inner">
        <div className="platform-copy">
          <span className="eyebrow">BUILT AROUND REAL OPERATING QUESTIONS</span>
          <h2>Not just “how much?”<br /><em>“When, and how sure?”</em></h2>
          <p>LoadIQ puts demand forecasts, peak windows, and schedule scenarios in one place. Staff can see the range, review the assumptions, and keep control of the final decision.</p>
          <a className="light-link" href="/dashboard/procurement" onClick={onOpenWorkspace}>Compare schedule scenarios <ArrowRight size={16} /></a>
        </div>
        <div className="platform-details">
          <div className="detail-row"><span className="detail-label">01 / FORECAST</span><div><strong>Next 24 hours and beyond</strong><p>Review hourly demand ranges and a wider lookahead.</p></div><ArrowUpRight size={17} /></div>
          <div className="detail-row"><span className="detail-label">02 / PEAK</span><div><strong>Timing and likelihood</strong><p>Bring potential high-demand windows into view.</p></div><ArrowUpRight size={17} /></div>
          <div className="detail-row"><span className="detail-label">03 / SCENARIO</span><div><strong>Costs made visible</strong><p>Compare schedule choices against stated assumptions.</p></div><ArrowUpRight size={17} /></div>
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
        <div className="method-copy"><p>Forecasts are more useful when staff can inspect their data, uncertainty, and cost assumptions. LoadIQ is designed to make those details visible alongside the planning view.</p>
          <div className="method-points"><span><Check size={15} /> Time-ordered backtesting</span><span><Check size={15} /> Data freshness and gaps</span><span><Check size={15} /> Explicit scenario assumptions</span></div>
          <div className="prototype-note"><span className="note-mark">i</span><p>The landing-page chart is illustrative. The connected workspace uses project forecast and weather services; verify data freshness and cost assumptions before operational use.</p></div>
        </div>
      </div>
    </section>
  )
}

function QuestionsSection() {
  return <section className="questions-section section-wrap">
    <div className="questions-heading"><span className="eyebrow">LOADIQ, IN BRIEF</span><h2>Clear forecasts.<br /><em>Clear boundaries.</em></h2></div>
    <div className="questions-list">
      <details><summary>Does LoadIQ control the grid or buy power?</summary><p>No. It presents forecasts and planning scenarios. Utility staff make decisions through their existing processes.</p></details>
      <details><summary>What do P10, P50, and P90 mean?</summary><p>They are lower, middle, and higher points in the forecast range. The range helps show uncertainty around expected demand.</p></details>
      <details><summary>Are the numbers on this landing page live?</summary><p>No. The chart above is an illustrative example. Open the workspace to view connected project data and check its freshness label.</p></details>
    </div>
  </section>
}

function Footer() {
  return (
    <footer className="site-footer">
      <a className="brand footer-brand" href="#top"><span className="brand-mark"><span /><span /><span /></span><span className="brand-word">LoadIQ<span className="brand-period">.</span></span></a>
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
    const nextPath = event.currentTarget.getAttribute('href') || '/dashboard'
    window.history.pushState({}, '', nextPath)
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
      <div className="announcement"><span>LOADIQ PREVIEW</span> Forecasting and schedule scenarios for Delhi power planning. <a href="#methodology">About the data <ArrowRight size={13} /></a></div>
      <Header onOpenWorkspace={openDashboard} />
      <main>
        <Hero onOpenWorkspace={openDashboard} />
        <ProofStrip />
        <ForecastStory onOpenForecast={openDashboard} />
        <Workflow />
        <PlatformSection onOpenWorkspace={openDashboard} />
        <MethodologySection />
        <QuestionsSection />
        <section className="closing-cta">
          <span className="eyebrow">LOADIQ · DELHI LOAD OUTLOOK</span>
          <h2>Make room for<br /><em>the unexpected.</em></h2>
          <p>Review the forecast, peak outlook, and planning scenarios in the LoadIQ workspace.</p>
          <a className="button button-cream" href="/dashboard" onClick={openDashboard}>Open the workspace <ArrowRight size={16} /></a>
        </section>
      </main>
      <Footer />
    </>
  )
}
