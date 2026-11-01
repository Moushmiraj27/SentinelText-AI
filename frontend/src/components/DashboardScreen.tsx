import { Activity, AudioLines, BookHeart, CalendarDays, ChevronRight, Clock3, Heart, LoaderCircle, Mic, PenLine, RefreshCw, Sparkles } from 'lucide-react';
import type { AppPage } from './AppShell';
import type { JournalCardData } from './JournalCard';

type Period = 'week' | 'month' | 'quarter';
type TrendDay = { date: string; count: number; emotions: Record<string, number> };
type DashboardData = { period: Period; entry_count: number; total_entry_count: number; emotion_counts: Record<string, number>; trend: TrendDay[]; recent?: JournalCardData[]; latest_emotion: string | null };
type Props = {
  name: string; dashboard: DashboardData | null; journals: JournalCardData[]; echo: any; recommendations: any;
  loading: boolean; loadError: string; period: Period; onPeriodChange: (period: Period) => void;
  onRetry: () => void; onNavigate: (page: AppPage) => void; onTextJournal: () => void;
};
const nice = (value: string) => value.split(/[ /_-]+/).map(word => word ? word[0].toUpperCase() + word.slice(1) : '').join(' ');
const dateLabel = (value: string, options: Intl.DateTimeFormatOptions = { month: 'short', day: 'numeric' }) => new Date(value + (value.length === 10 ? 'T12:00:00' : '')).toLocaleDateString(undefined, options);

export default function DashboardScreen({ name, dashboard, journals, echo, recommendations, loading, loadError, period, onPeriodChange, onRetry, onNavigate, onTextJournal }: Props) {
  if (loading && !dashboard) return <section className="dashboard-loading" aria-label="Loading your dashboard"><div className="dashboard-skeleton hero"/><div className="dashboard-skeleton stats"/><div className="dashboard-skeleton chart"/><span><LoaderCircle size={16} className="spin"/> Loading your reflections…</span></section>;
  if (loadError && !dashboard) return <section className="dashboard-load-error"><div className="dashboard-empty-icon"><RefreshCw size={21}/></div><h2>Your dashboard couldn’t load</h2><p>{loadError}</p><button className="primary" onClick={onRetry}><RefreshCw size={15}/> Try again</button></section>;

  const emotionCounts = dashboard?.emotion_counts || {};
  const emotions = Object.entries(emotionCounts).sort((a, b) => b[1] - a[1]);
  const peak = Math.max(1, ...Object.values(emotionCounts));
  const total = dashboard?.entry_count || 0;
  const hasAnyHistory = (dashboard?.total_entry_count || 0) > 0;
  const firstName = name.trim().split(/\s+/)[0] || 'there';
  const periodLabel = period === 'week' ? 'Past 7 days' : period === 'month' ? 'Past 30 days' : 'Past 90 days';
  const recent = (dashboard?.recent?.length ? dashboard.recent : journals).slice(0, 3);
  const trend = dashboard?.trend || [];
  const chartMax = Math.max(1, ...trend.map(day => day.count));
  const tickEvery = period === 'week' ? 1 : period === 'month' ? 5 : 15;
  const themes = (echo?.themes || []).filter((theme: any) => theme.status !== 'dismissed').slice(0, 4);
  const suggestions = (recommendations?.items || []).slice(0, 2);

  return <div className="dashboard-page">
    {loadError && <div className="dashboard-inline-error" role="alert"><span>{loadError}</span><button className="secondary" onClick={onRetry}>Retry</button></div>}
    <section className="dashboard-hero">
      <div className="dashboard-hero-copy"><div className="eyebrow">YOUR PERSONAL REFLECTION SPACE</div><h1>Good {new Date().getHours() < 12 ? 'morning' : new Date().getHours() < 18 ? 'afternoon' : 'evening'}, {firstName}.</h1><p>Your check-ins are yours. Here’s what you’ve shared and noticed lately.</p>
        <div className="dashboard-quick-actions"><button className="primary" onClick={() => onNavigate('Voice Journal')}><Mic size={17}/> Record a voice journal</button><button className="secondary" onClick={onTextJournal}><PenLine size={16}/> Write a reflection</button></div>
      </div><div className="dashboard-hero-art" aria-hidden="true"><div className="dashboard-hero-orbit"/><div className="dashboard-hero-core"><AudioLines size={28}/></div><span><Heart size={13}/> one moment at a time</span></div>
    </section>

    <section className="dashboard-section dashboard-overview-section">
      <div className="dashboard-section-heading"><div><div className="eyebrow">A LOOK AT YOUR CHECK-INS</div><h2>Emotional overview</h2></div><label className="dashboard-period"><CalendarDays size={15}/><select aria-label="Filter dashboard by date" value={period} onChange={event => onPeriodChange(event.target.value as Period)}><option value="week">Past 7 days</option><option value="month">Past 30 days</option><option value="quarter">Past 90 days</option></select></label></div>
      {total === 0 ? <div className="dashboard-empty-panel"><div className="dashboard-empty-icon"><Heart size={20}/></div><div><h3>{hasAnyHistory ? `No reflections in the ${periodLabel.toLowerCase()}` : 'Your overview will grow with your reflections'}</h3><p>{hasAnyHistory ? 'Choose a wider date range or add a new check-in to see its patterns here.' : 'Once you save an entry, you’ll see its emotion patterns and trends here.'}</p></div><button className="text-button" onClick={onTextJournal}>Write a reflection <ChevronRight size={15}/></button></div> : <div className="dashboard-stat-grid">
        <article className="dashboard-stat-card"><span>REFLECTIONS · {periodLabel.toUpperCase()}</span><b>{total}</b><small>{dashboard?.total_entry_count || total} saved in total</small></article>
        <article className="dashboard-stat-card"><span>EMOTIONAL PATTERNS</span><b>{emotions.length}</b><small>Distinct language labels in this period</small></article>
        <article className="dashboard-stat-card dashboard-stat-feature"><span>MOST COMMON LABEL</span><b>{emotions[0] ? nice(emotions[0][0]) : '—'}</b><small>{emotions[0] ? `${emotions[0][1]} of ${total} reflections` : 'No label available for this period'}</small></article>
        {emotions.length > 0 && <article className="dashboard-emotion-card"><div className="dashboard-subheading"><div><span className="eyebrow">FROM YOUR SAVED ENTRIES</span><h3>Emotion breakdown</h3></div><small>{periodLabel}</small></div><div className="dashboard-emotion-list">{emotions.slice(0, 5).map(([emotion, count]) => <div className="dashboard-emotion-row" key={emotion}><span className={`emotion-pill ${emotion.split(' ')[0]}`}>{nice(emotion)}</span><div className="dashboard-emotion-track"><i className={`dashboard-emotion-fill ${emotion.split(' ')[0]}`} style={{ width: `${Math.max(5, count / peak * 100)}%` }}/></div><b>{count}</b></div>)}</div></article>}
      </div>}
    </section>

    <section className="dashboard-section dashboard-trends-section">
      <div className="dashboard-section-heading"><div><div className="eyebrow">YOUR EMOTIONAL TRENDS</div><h2>How your check-ins have changed</h2></div><span className="dashboard-period-note"><CalendarDays size={14}/>{periodLabel}</span></div>
      {total === 0 ? <div className="dashboard-chart-empty">{hasAnyHistory ? `No trend data for the ${periodLabel.toLowerCase()}. Try a wider date range.` : 'Your trend chart will appear after you save a reflection.'}</div> : <div className="dashboard-chart-card"><div className="dashboard-chart-meta"><span><b>{total}</b> reflections in this period</span><span>Daily entries · based on your saved words</span></div><div className="dashboard-chart-scroll"><div className={`dashboard-bar-chart period-${period}`} role="img" aria-label={`Daily reflection and emotion counts for the ${periodLabel.toLowerCase()}`}>
        {trend.map((day, index) => <div className="dashboard-chart-day" key={day.date} title={`${dateLabel(day.date, { weekday: 'long', month: 'long', day: 'numeric' })}: ${day.count} ${day.count === 1 ? 'reflection' : 'reflections'}`}><div className="dashboard-bar-track">{day.count > 0 && Object.entries(day.emotions).map(([emotion, count]) => <i key={emotion} className={`dashboard-bar-segment ${emotion.split(' ')[0]}`} style={{ height: `${count / chartMax * 100}%` }} title={`${nice(emotion)}: ${count}`}/>)}</div>{index % tickEvery === 0 && <small>{dateLabel(day.date, period === 'week' ? { weekday: 'short' } : { month: 'numeric', day: 'numeric' })}</small>}</div>)}
      </div></div><div className="dashboard-chart-legend">{emotions.slice(0, 5).map(([emotion]) => <span key={emotion}><i className={emotion.split(' ')[0]}/>{nice(emotion)}</span>)}</div></div>}
    </section>

    <div className="dashboard-content-grid">
      <section className="dashboard-section dashboard-recent-section"><div className="dashboard-section-heading"><div><div className="eyebrow">RECENT JOURNAL ENTRIES</div><h2>Your latest reflections</h2></div><button className="text-button" onClick={() => onNavigate('Journal History')}>View history <ChevronRight size={15}/></button></div>
        {recent.length === 0 ? <div className="dashboard-empty-panel compact"><div className="dashboard-empty-icon"><BookHeart size={19}/></div><div><h3>{hasAnyHistory ? 'No recent entries in this range' : 'No journal entries yet'}</h3><p>{hasAnyHistory ? 'Your older reflections are still available in Journal History.' : 'Your saved voice and text entries will show up here.'}</p></div><button className="text-button" onClick={() => onNavigate('Journal History')}>Open journal history <ChevronRight size={15}/></button></div> : <div className="dashboard-recent-list">{recent.map((entry: JournalCardData) => <article className="dashboard-journal-item" key={entry.id}><span className="dashboard-entry-icon"><BookHeart size={17}/></span><div className="dashboard-entry-copy"><div className="dashboard-entry-meta"><b><Clock3 size={13}/>{new Date(entry.created_at).toLocaleString(undefined, { month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit' })}</b><span className={`emotion-pill ${entry.emotion.split(' ')[0]}`}>{nice(entry.emotion)}</span></div><p>{entry.transcript}</p><button className="plain-link" onClick={() => onNavigate('Journal History')}>Open in journal history <ChevronRight size={13}/></button></div></article>)}</div>}
      </section>

      <div className="dashboard-side-stack">
        <section className="dashboard-mini-panel"><div className="dashboard-section-heading"><div><div className="eyebrow">EMOTIONAL ECHO</div><h2>Recurring themes</h2></div><AudioLines size={18}/></div>
          {themes.length ? <div className="dashboard-theme-list">{themes.map((theme: any) => <div className="dashboard-theme-item" key={theme.topic}><span>{nice(theme.topic)}</span><b>{theme.count} entries</b></div>)}</div> : <div className="dashboard-mini-empty"><p>{total ? 'No recurring themes have been identified in your saved entries yet.' : 'Recurring themes will appear when you have saved reflections.'}</p></div>}
          <button className="plain-link" onClick={() => onNavigate('Emotional Echo')}>Open Emotional Echo <ChevronRight size={14}/></button>
        </section>
        <section className="dashboard-mini-panel"><div className="dashboard-section-heading"><div><div className="eyebrow">COPING INTELLIGENCE</div><h2>Gentle suggestions</h2></div><Sparkles size={18}/></div>
          {suggestions.length ? <div className="dashboard-suggestion-list">{suggestions.map((item: any) => <article className="dashboard-suggestion" key={item.id}><span><Activity size={16}/></span><div><b>{nice(item.activity)}</b><p>{item.description}</p></div></article>)}</div> : <div className="dashboard-mini-empty"><p>{total ? 'No suggestions are available right now.' : 'Suggestions will be shown here when available from Coping Intelligence.'}</p></div>}
          <button className="plain-link" onClick={() => onNavigate('Coping Intelligence')}>Explore suggestions <ChevronRight size={14}/></button>
        </section>
      </div>
    </div>
  </div>;
}
