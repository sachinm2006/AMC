import { useMemo, useState, type CSSProperties, type ReactNode } from 'react'
import {
  Activity, ArrowDownRight, ArrowRight, ArrowUpRight, Bell, BookOpenCheck,
  ChartNoAxesCombined, ChevronDown, ChevronLeft, ChevronRight, CircleHelp,
  Clock3, CloudSun, Download, Gauge, LayoutDashboard, Menu, Settings2,
  ShieldCheck, Sun, TriangleAlert, X, Zap,
} from 'lucide-react'
import {
  Area, AreaChart, CartesianGrid, Line, ReferenceLine, ResponsiveContainer,
  Tooltip, XAxis, YAxis,
} from 'recharts'
import './dashboard.css'

type Tab = 'Overview' | 'Forecast' | 'Peak events' | 'Procurement' | 'Model health'

const series = [
  { hour: '00', low: 6260, mid: 6500, high: 6810 },
  { hour: '02', low: 6160, mid: 6380, high: 6700 },
  { hour: '04', low: 6180, mid: 6400, high: 6750 },
  { hour: '06', low: 6270, mid: 6580, high: 6970 },
  { hour: '08', low: 6500, mid: 6900, high: 7330 },
  { hour: '10', low: 6730, mid: 7210, high: 7670 },
  { hour: '12', low: 6900, mid: 7410, high: 7880 },
  { hour: '14', low: 7010, mid: 7570, high: 8090 },
  { hour: '16', low: 7100, mid: 7720, high: 8230 },
  { hour: '18', low: 7140, mid: 7810, high: 8320 },
  { hour: '20', low: 7020, mid: 7680, high: 8210 },
  { hour: '22', low: 6820, mid: 7390, high: 7930 },
  { hour: '24', low: 6540, mid: 7060, high: 7610 },
]

function TooltipCard({ active, payload, label }: { active?: boolean; payload?: Array<{ payload: typeof series[number] }>; label?: string }) {
  if (!active || !payload?.length) return null
  const point = payload[0].payload
  return <div className="dash-tooltip"><b>{label}:00 IST</b><span>Median <strong>{point.mid.toLocaleString()} MW</strong></span><span>Lower range <strong>{point.low.toLocaleString()} MW</strong></span><span>Upper range <strong>{point.high.toLocaleString()} MW</strong></span></div>
}

function MetricCard({ label, value, unit, note, icon, tone = 'normal' }: { label: string; value: string; unit?: string; note: string; icon: ReactNode; tone?: 'normal' | 'watch' }) {
  return <article className={`dash-metric ${tone === 'watch' ? 'metric-watch' : ''}`}>
    <div className="metric-top"><span>{label}</span><span className="metric-icon">{icon}</span></div>
    <div className="metric-value">{value}<small>{unit}</small></div>
    <div className="metric-foot"><span className="metric-foot-icon">{tone === 'watch' ? <ArrowUpRight size={13} /> : <ArrowDownRight size={13} />}</span>{note}</div>
  </article>
}

function Sidebar({ active, onSelect, mobileOpen, onMobileToggle, onBack }: { active: Tab; onSelect: (tab: Tab) => void; mobileOpen: boolean; onMobileToggle: () => void; onBack: () => void }) {
  const items: Array<{ label: Tab; icon: ReactNode; section: string }> = [
    { label: 'Overview', icon: <LayoutDashboard size={17} />, section: 'WORKSPACE' },
    { label: 'Forecast', icon: <ChartNoAxesCombined size={17} />, section: 'WORKSPACE' },
    { label: 'Peak events', icon: <TriangleAlert size={17} />, section: 'WORKSPACE' },
    { label: 'Procurement', icon: <Activity size={17} />, section: 'PLANNING' },
    { label: 'Model health', icon: <ShieldCheck size={17} />, section: 'PLANNING' },
  ]
  return <>
    {mobileOpen && <button aria-label="Close navigation" className="sidebar-scrim" onClick={onMobileToggle} />}
    <aside className={`dash-sidebar ${mobileOpen ? 'sidebar-open' : ''}`}>
      <div className="dash-brand-row">
        <a className="dash-brand" href="#top" onClick={(event) => { event.preventDefault(); onSelect('Overview') }}><span className="dash-brand-symbol"><span /><span /><span /></span><span>peakwise<span className="dash-brand-dot">.</span></span></a>
        <button className="sidebar-collapse" onClick={onMobileToggle} aria-label="Close navigation"><X size={17} /></button>
      </div>
      <div className="workspace-switcher"><span className="workspace-icon">D</span><span><b>Delhi system</b><small>Operations workspace</small></span><ChevronDown size={14} /></div>
      <div className="nav-group-label">WORKSPACE</div>
      <nav aria-label="Workspace navigation">
        {items.slice(0, 3).map((item) => <button key={item.label} className={`dash-nav-item ${active === item.label ? 'active' : ''}`} onClick={() => { onSelect(item.label); onMobileToggle() }}>{item.icon}<span>{item.label}</span>{item.label === 'Peak events' && <i className="nav-count">2</i>}</button>)}
      </nav>
      <div className="nav-group-label nav-gap">PLANNING</div>
      <nav aria-label="Planning navigation">
        {items.slice(3).map((item) => <button key={item.label} className={`dash-nav-item ${active === item.label ? 'active' : ''}`} onClick={() => { onSelect(item.label); onMobileToggle() }}>{item.icon}<span>{item.label}</span></button>)}
      </nav>
      <div className="sidebar-spacer" />
      <div className="sidebar-source"><span className="source-icon"><BookOpenCheck size={15} /></span><span><b>Demo environment</b><small>Illustrative data only</small></span></div>
      <button className="dash-nav-item sidebar-back" onClick={onBack}><ChevronLeft size={17} /><span>Back to Peakwise</span></button>
      <div className="sidebar-version">PEAKWISE OPERATIONS <span>0.1 PREVIEW</span></div>
    </aside>
  </>
}

function DashboardChart({ onReadMore }: { onReadMore: () => void }) {
  return <section className="dash-panel chart-panel" id="forecast">
    <div className="panel-heading">
      <div><span className="panel-kicker">DEMAND FORECAST</span><h2>Delhi system load</h2><p>Hourly demand outlook · Next 24 hours</p></div>
      <button className="panel-select" onClick={onReadMore}>Next 24 hours <ChevronDown size={14} /></button>
    </div>
    <div className="chart-meta-row"><span><i className="chart-status-dot" />Illustrative forecast</span><span>Issued 09:00 IST · 12 Nov 2026</span></div>
    <div className="dash-chart" role="img" aria-label="Illustrative forecast chart showing P10 to P90 demand range. Median demand peaks at 7,810 megawatts around 18:00.">
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={series.map((point) => ({ ...point, spread: point.high - point.low }))} margin={{ top: 12, right: 12, left: -14, bottom: 0 }}>
          <defs><linearGradient id="dashBand" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="#7f967b" stopOpacity={0.26} /><stop offset="100%" stopColor="#7f967b" stopOpacity={0.06} /></linearGradient></defs>
          <CartesianGrid vertical={false} stroke="#e8e9e1" strokeDasharray="3 5" />
          <XAxis dataKey="hour" axisLine={false} tickLine={false} tick={{ fill: '#858d85', fontSize: 10 }} tickMargin={12} />
          <YAxis domain={[6000, 8500]} axisLine={false} tickLine={false} tick={{ fill: '#858d85', fontSize: 10 }} tickFormatter={(value: number) => `${(value / 1000).toFixed(1)}k`} />
          <Tooltip content={<TooltipCard />} cursor={{ stroke: '#8d998a', strokeDasharray: '3 4' }} />
          <ReferenceLine x="18" stroke="#bd7050" strokeDasharray="4 4" />
          <Area type="monotone" dataKey="low" stackId="uncertainty" stroke="none" fill="transparent" isAnimationActive={false} />
          <Area type="monotone" dataKey="spread" stackId="uncertainty" stroke="none" fill="url(#dashBand)" isAnimationActive={false} />
          <Line type="monotone" dataKey="mid" stroke="#064e3b" strokeWidth={2.5} dot={false} activeDot={{ r: 4, fill: '#064e3b', stroke: '#fffdf7', strokeWidth: 2 }} isAnimationActive={false} />
          <Line dataKey="mid" stroke="transparent" dot={(props: { cx?: number; cy?: number; index?: number }) => props.index === 9 ? <g key="peak"><circle cx={props.cx} cy={props.cy} r="9" fill="#fffdf7" /><circle cx={props.cx} cy={props.cy} r="5" fill="#b65c3c" /></g> : <g key={`empty-${props.index}`} />} isAnimationActive={false} />
        </AreaChart>
      </ResponsiveContainer>
      <span className="peak-chart-label">Expected peak · 18:00</span>
    </div>
    <div className="chart-legend-row"><span><i className="range-key" />P10–P90 range</span><span><i className="median-key" />P50 median</span><span><i className="peak-key" />Peak watch</span><button onClick={onReadMore}>Forecast details <ArrowRight size={14} /></button></div>
    <div className="chart-disclaimer">Illustrative values for interface preview. Not an operational forecast.</div>
  </section>
}

function AppHeader({ onMenu, dark, onTheme }: { onMenu: () => void; dark: boolean; onTheme: () => void }) {
  return <header className="dash-topbar">
    <button className="mobile-menu-button" onClick={onMenu} aria-label="Open navigation"><Menu size={19} /></button>
    <div className="topbar-breadcrumb"><span>Delhi system</span><ChevronRight size={14} /><b>Overview</b></div>
    <div className="topbar-actions">
      <div className="topbar-data-status"><span className="chart-status-dot" />Demo data</div>
      <button className={`icon-action ${dark ? 'theme-on' : ''}`} onClick={onTheme} aria-label="Toggle dark mode"><Sun size={17} /></button>
      <button className="icon-action has-notice" aria-label="Notifications"><Bell size={17} /><i /></button>
      <button className="icon-action" aria-label="Help"><CircleHelp size={17} /></button>
      <button className="profile-chip" aria-label="Profile menu"><span>SK</span><ChevronDown size={13} /></button>
    </div>
  </header>
}

function PeakWatch() {
  return <section className="dash-panel peak-panel" id="peaks">
    <div className="panel-heading compact"><div><span className="panel-kicker">ATTENTION</span><h2>Peak watch</h2></div><button className="icon-panel-button" aria-label="More peak watch options"><ChevronRight size={17} /></button></div>
    <div className="peak-risk-banner"><span className="risk-symbol"><TriangleAlert size={17} /></span><span><b>Elevated load risk</b><small>Probability of exceeding 7,600 MW</small></span><strong>68<small>%</small></strong></div>
    <div className="peak-details">
      <div><span>Expected peak</span><b>7,810 MW</b></div>
      <div><span>Likely window</span><b>17:00–19:00</b></div>
      <div><span>Upper estimate</span><b>8,320 MW</b></div>
    </div>
    <button className="panel-link" onClick={() => document.getElementById('peak-events')?.scrollIntoView({ behavior: 'smooth' })}>Review peak windows <ArrowRight size={14} /></button>
  </section>
}

function ProcurementPanel() {
  const [policy, setPolicy] = useState<'Median' | 'Balanced' | 'Conservative'>('Balanced')
  const [buffer, setBuffer] = useState(3)
  const reserve = useMemo(() => Math.round(7810 * buffer / 100), [buffer])
  return <section className="dash-panel procurement-panel" id="procurement">
    <div className="panel-heading compact"><div><span className="panel-kicker">PLANNING SCENARIO</span><h2>Schedule comparison</h2></div><button className="panel-select small-select">Scenario only <ChevronDown size={13} /></button></div>
    <div className="policy-options" role="group" aria-label="Schedule policy">
      {(['Median', 'Balanced', 'Conservative'] as const).map((option) => <button key={option} className={policy === option ? 'policy-selected' : ''} onClick={() => setPolicy(option)} aria-pressed={policy === option}>{option}</button>)}
    </div>
    <div className="schedule-row"><span>Indicative schedule</span><strong>{(7810 + reserve).toLocaleString()} <small>MW</small></strong></div>
    <div className="buffer-control"><label htmlFor="buffer-slider">Planning buffer <b>{buffer}%</b></label><input id="buffer-slider" type="range" min="0" max="8" value={buffer} onChange={(e) => setBuffer(Number(e.target.value))} style={{ '--range-value': `${buffer / 8 * 100}%` } as CSSProperties} /><div className="buffer-scale"><span>0%</span><span>4%</span><span>8%</span></div></div>
    <div className="assumption-note"><CircleHelp size={14} /><span>{policy} policy · User-adjustable illustrative buffer; cost model not connected.</span></div>
    <button className="panel-link" onClick={() => setPolicy('Conservative')}>Review assumptions <ArrowRight size={14} /></button>
  </section>
}

function PeakEvents() {
  return <section className="dash-panel events-panel" id="peak-events">
    <div className="panel-heading compact"><div><span className="panel-kicker">NEXT 24 HOURS</span><h2>Upcoming peak windows</h2></div><button className="panel-link all-events">View all <ArrowRight size={14} /></button></div>
    <div className="event-table-wrap"><table className="event-table"><thead><tr><th>WINDOW</th><th>EXPECTED LOAD</th><th>PEAK LIKELIHOOD</th><th>STATUS</th></tr></thead><tbody>
      <tr><td><span className="event-time">17:00–19:00</span><small>Today · Evening</small></td><td>7,810 <small>MW</small></td><td><span className="probability-cell"><i style={{ width: '68%' }} />68%</span></td><td><span className="risk-status"><i />Elevated</span></td></tr>
      <tr><td><span className="event-time">10:00–12:00</span><small>Tomorrow · Morning</small></td><td>7,460 <small>MW</small></td><td><span className="probability-cell low"><i style={{ width: '34%' }} />34%</span></td><td><span className="risk-status watch"><i />Watch</span></td></tr>
    </tbody></table></div>
    <div className="table-footnote">Peak likelihood shown against an illustrative 7,600 MW threshold.</div>
  </section>
}

function HealthPanel() {
  return <section className="dash-panel health-panel" id="model-health">
    <div className="panel-heading compact"><div><span className="panel-kicker">MODEL & DATA</span><h2>Forecast status</h2></div><Settings2 size={17} className="health-settings" /></div>
    <div className="health-row"><span className="health-symbol"><Clock3 size={15} /></span><span><b>Forecast issued</b><small>12 Nov 2026 · 09:00 IST</small></span><span className="health-ok">Current</span></div>
    <div className="health-row"><span className="health-symbol"><Gauge size={15} /></span><span><b>Recent coverage</b><small>Nominal target: 80% · backtest view</small></span><span className="coverage-value">—</span></div>
    <div className="health-row"><span className="health-symbol"><Download size={15} /></span><span><b>Source series</b><small>Delhi system · hourly sample</small></span><span className="health-ok">Demo</span></div>
    <div className="health-notice"><ShieldCheck size={14} /> No live SLDC connection in this preview.</div>
  </section>
}

export default function Dashboard({ onBack }: { onBack: () => void }) {
  const [active, setActive] = useState<Tab>('Overview')
  const [mobileOpen, setMobileOpen] = useState(false)
  const [dark, setDark] = useState(false)
  const selectTab = (tab: Tab) => {
    setActive(tab)
    const target = tab === 'Overview' ? 'dash-content' : tab === 'Forecast' ? 'forecast' : tab === 'Peak events' ? 'peak-events' : tab === 'Procurement' ? 'procurement' : 'model-health'
    document.getElementById(target)?.scrollIntoView({ behavior: 'smooth', block: tab === 'Overview' ? 'start' : 'center' })
  }
  return <div className={`dashboard-app ${dark ? 'dashboard-dark' : ''}`}>
    <Sidebar active={active} onSelect={selectTab} mobileOpen={mobileOpen} onMobileToggle={() => setMobileOpen(!mobileOpen)} onBack={onBack} />
    <div className="dash-main">
      <AppHeader onMenu={() => setMobileOpen(true)} dark={dark} onTheme={() => setDark(!dark)} />
      <main className="dash-content" id="dash-content">
        <div className="dash-page-title"><div><div className="page-kicker"><span className="page-kicker-line" />WEDNESDAY, 12 NOVEMBER 2026</div><h1>Good morning, operations.</h1><p>Here’s the demand outlook for the Delhi system.</p></div><div className="title-actions"><button className="date-select"><Clock3 size={14} />Next 24 hours<ChevronDown size={13} /></button><button className="export-button" onClick={() => window.print()}><Download size={15} />Export brief</button></div></div>
        <div className="dashboard-context"><span className="context-badge"><i />DEMO ENVIRONMENT</span><span>Illustrative values · Not for operational use</span><span className="context-updated">Last updated 09:00 IST <ChevronRight size={13} /></span></div>
        <div className="metric-grid">
          <MetricCard label="FORECAST PEAK" value="7,810" unit="MW" note="Expected around 18:00 IST" icon={<Zap size={16} />} />
          <MetricCard label="PEAK LIKELIHOOD" value="68" unit="%" note="Above illustrative 7,600 MW threshold" icon={<TriangleAlert size={16} />} tone="watch" />
          <MetricCard label="UNCERTAINTY RANGE" value="1,180" unit="MW" note="P10 to P90 at the expected peak" icon={<ChartNoAxesCombined size={16} />} />
          <MetricCard label="WEATHER INPUT" value="38°" unit="C" note="Illustrative afternoon forecast" icon={<CloudSun size={16} />} />
        </div>
        <div className="dashboard-columns">
          <DashboardChart onReadMore={() => setActive('Forecast')} />
          <div className="right-stack"><PeakWatch /><ProcurementPanel /></div>
        </div>
        <div className="dashboard-lower-grid"><PeakEvents /><HealthPanel /></div>
        <footer className="dash-footer"><span>Peakwise operations preview</span><span>Forecast values are illustrative and not connected to live operations.</span><a href="#methodology" onClick={onBack}>Methodology <ArrowRight size={13} /></a></footer>
      </main>
    </div>
  </div>
}
