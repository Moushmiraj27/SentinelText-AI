import { useCallback, useEffect, useState } from 'react';
import { Activity, AudioLines, BookHeart, Check, ChevronRight, Clock3, LoaderCircle, RefreshCw, Sparkles, X } from 'lucide-react';
import { api } from '../services/api';
import type { JournalCardData } from './JournalCard';
import { InlineNotice, PageIntro, PanelHeading } from './ui';

type EchoEntry = { id: number; date: string; emotion: string; excerpt: string; transcript: string };
type EchoTheme = { key: string; topic: string; title: string; count: number; explanation: string; status: 'suggested' | 'confirmed' | 'dismissed'; entries: EchoEntry[] };
type EchoData = {
  total_entries: number; all_time_entries: number; days: 7 | 30 | 90; themes: EchoTheme[];
  emotion_counts: Record<string, number>; daily_trend: { date: string; emotions: Record<string, number>; count: number }[];
  reflections: { text: string; source_entry_ids: number[]; kind: string }[];
  ai_provider_available: boolean; ai_consent: boolean; reflection_configured: boolean; reflection_generated: boolean; ai_fallback: boolean;
  feedback_history: { key: string; title: string; status: string; updated_at: string }[];
};
type Props = { journals: JournalCardData[]; onOpenEntry: (entry: JournalCardData) => void };

const formatDate = (value: string) => new Date(value).toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
const titleCase = (value: string) => value.replace(/\b\w/g, letter => letter.toUpperCase());
const emotionColors: Record<string, string> = { stress: 'orange', anxiety: 'orange', sadness: 'blue', frustration: 'rose', happiness: 'teal', calm: 'teal', 'mixed / unclear': 'muted' };

export default function EchoScreen({ journals, onOpenEntry }: Props) {
  const [days, setDays] = useState<7 | 30 | 90>(30);
  const [data, setData] = useState<EchoData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [saving, setSaving] = useState('');
  const [editing, setEditing] = useState<string | null>(null);
  const [editTitle, setEditTitle] = useState('');

  const load = useCallback(async () => {
    setLoading(true); setError('');
    try { setData(await api(`/echo?days=${days}`)); }
    catch (err) { setError(err instanceof Error ? err.message : 'Emotional Echo could not be loaded.'); }
    finally { setLoading(false); }
  }, [days]);
  useEffect(() => { void load(); }, [load]);

  const updateTheme = async (theme: EchoTheme, status: EchoTheme['status'], title = theme.title) => {
    setSaving(theme.key); setError('');
    try {
      await api(`/echo/themes/${theme.key}`, { method: 'PUT', body: JSON.stringify({ title: title.trim() || theme.title, status }) });
      setEditing(null); await load();
    } catch (err) { setError(err instanceof Error ? err.message : 'Your theme feedback could not be saved.'); }
    finally { setSaving(''); }
  };

  const updateAiConsent = async (external_ai_consent: boolean) => {
    setSaving('consent'); setError('');
    try { await api('/echo/preferences', { method: 'PUT', body: JSON.stringify({ external_ai_consent }) }); await load(); }
    catch (err) { setError(err instanceof Error ? err.message : 'Your privacy preference could not be saved.'); }
    finally { setSaving(''); }
  };

  const openEntry = (entry: EchoEntry) => onOpenEntry({
    id: entry.id, transcript: entry.transcript, emotion: entry.emotion, confidence: 0,
    sentiment: 'mixed / unclear', topics: [], phrases: [], reflection: null, created_at: entry.date, has_audio: false,
  });

  const maxDaily = Math.max(1, ...((data?.daily_trend || []).map(point => point.count)));
  const maxEmotion = Math.max(1, ...Object.values(data?.emotion_counts || {}));

  return <>
    <PageIntro eyebrow="EMOTIONAL ECHO" title="Patterns, gently noticed." sub="Explore recurring language in your own journal entries, in a way that leaves the meaning with you." />
    <InlineNotice>These patterns describe words and labels in your saved entries. They are not diagnoses or validated psychological measurements.</InlineNotice>
    <div className="echo-toolbar">
      <div><span className="echo-eyebrow">DATE RANGE</span><p>Showing your saved entries from the selected period.</p></div>
      <div className="echo-period" role="group" aria-label="Emotional Echo date range">
        {([7, 30, 90] as const).map(period => <button key={period} aria-pressed={days === period} className={days === period ? 'selected' : ''} onClick={() => setDays(period)}>{period} days</button>)}
      </div>
    </div>
    {error && <div className="echo-error" role="alert"><span>{error}</span><button className="secondary" onClick={() => void load()}><RefreshCw size={15}/> Retry</button></div>}

    {loading && !data ? <div className="echo-loading" role="status"><LoaderCircle className="spin" size={20}/> Gathering your journal patterns…</div> : data && <>
      <div className="stats-row echo-stats">
        <div className="stat-card"><span>ENTRIES IN THIS PERIOD</span><b>{data.total_entries}</b></div>
        <div className="stat-card"><span>RECURRING THEMES</span><b>{data.themes.filter(theme => theme.status !== 'dismissed').length}</b></div>
        <div className="stat-card"><span>EMOTION LABELS RECORDED</span><b>{Object.values(data.emotion_counts).reduce((sum, count) => sum + count, 0)}</b></div>
      </div>

      {!data.total_entries ? <div className="panel echo-empty"><div className="echo-empty-icon"><AudioLines size={22}/></div><h2>No entries in this period</h2><p>When you save reflections, this space will show patterns drawn from your own words. Nothing is inferred from sample data.</p><small>{data.all_time_entries ? `You have entries outside the past ${days} days. Try a longer date range.` : 'Your journal entries remain private to your account.'}</small></div> : <>
        <div className="echo-grid">
          <section className="panel echo-themes-panel">
            <PanelHeading icon={<AudioLines size={17}/>} title="Recurring themes" />
            <p className="muted">Themes are grouped from similar wording in at least two entries.</p>
            {!data.themes.length ? <div className="echo-inline-empty"><BookHeart size={19}/><span>There are not yet enough similar entries in this period to identify a recurring theme. One or two entries can still appear in your trend below.</span></div> : <div className="echo-theme-list">
              {data.themes.map(theme => <article className={`echo-theme-card status-${theme.status}`} key={theme.key}>
                <div className="echo-theme-head"><div className="echo-theme-title"><span className="echo-eyebrow">{theme.status === 'confirmed' ? 'YOU CONFIRMED' : theme.status === 'dismissed' ? 'YOU DISMISSED THIS THEME' : 'SUGGESTED LANGUAGE PATTERN'}</span>
                  {editing === theme.key ? <form className="echo-edit-form" onSubmit={event => { event.preventDefault(); void updateTheme(theme, theme.status, editTitle); }}><input aria-label="Edit theme title" value={editTitle} maxLength={120} onChange={event => setEditTitle(event.target.value)}/><button className="mini-action" disabled={saving === theme.key}>Save</button><button type="button" className="mini-action" onClick={() => setEditing(null)}>Cancel</button></form> : <h3>{theme.title}</h3>}
                  <p>{theme.explanation}</p></div><div className="echo-count"><b>{theme.count}</b><small>{theme.count === 1 ? 'entry' : 'entries'}</small></div></div>
                <div className="echo-entry-list">{theme.entries.map(entry => <button className="echo-entry" key={entry.id} onClick={() => openEntry(entry)}><span className={`echo-emotion-dot ${emotionColors[entry.emotion] || 'muted'}`}/><span className="echo-entry-copy"><b>{formatDate(entry.date)} · {titleCase(entry.emotion)}</b><small>{entry.excerpt}</small></span><ChevronRight size={15}/></button>)}</div>
                <div className="echo-theme-actions">{saving === theme.key ? <LoaderCircle className="spin" size={16}/> : <>
                  {theme.status !== 'confirmed' && <button className="mini-action echo-confirm" onClick={() => void updateTheme(theme, 'confirmed')}><Check size={13}/> Confirm</button>}
                  <button className="mini-action" onClick={() => { setEditing(theme.key); setEditTitle(theme.title); }}>Edit title</button>
                  {theme.status !== 'dismissed' ? <button className="mini-action echo-dismiss" onClick={() => void updateTheme(theme, 'dismissed')}><X size={13}/> Dismiss</button> : <button className="mini-action" onClick={() => void updateTheme(theme, 'suggested')}>Restore suggestion</button>}
                </>}</div>
              </article>)}
            </div>}
          </section>

          <div className="echo-side-column">
            <section className="panel echo-chart-panel"><PanelHeading icon={<Activity size={17}/>} title="Emotion labels over time"/><p className="muted">Daily counts from the emotion labels saved with your entries.</p>
              <div className="echo-daily-chart" role="img" aria-label={`Daily journal entry counts for the past ${days} days`}>
                {data.daily_trend.map(point => <div className="echo-day" key={point.date} title={`${formatDate(point.date)}: ${point.count} ${point.count === 1 ? 'entry' : 'entries'}`}><div className="echo-bar-track">{Object.entries(point.emotions).map(([emotion, count]) => <i key={emotion} aria-label={`${emotion}: ${count}`} className={emotionColors[emotion] || 'muted'} style={{ height: `${count / maxDaily * 100}%` }}/>)}</div><small>{new Date(`${point.date}T00:00:00`).getDate()}</small></div>)}
              </div><div className="echo-chart-caption"><span>Daily entries · recent days at right</span><span>{data.total_entries} total</span></div>
              <div className="echo-emotion-frequency">{Object.entries(data.emotion_counts).sort((a,b) => b[1] - a[1]).map(([emotion, count]) => <div className="echo-frequency-row" key={emotion}><span>{titleCase(emotion)}</span><div className="echo-frequency-track"><i className={emotionColors[emotion] || 'muted'} style={{ width: `${count / maxEmotion * 100}%` }}/></div><b>{count}</b></div>)}</div>
              {!Object.keys(data.emotion_counts).length && <p className="muted">No emotion labels were recorded in these entries.</p>}
            </section>

            <section className="panel echo-reflections"><PanelHeading icon={<Sparkles size={17}/>} title="Personal reflections"/><span className="echo-reflection-label">{data.reflection_generated ? 'AI-GENERATED INTERPRETATION' : 'GROUNDED PATTERN SUMMARY'}</span>
              {data.reflections.length ? data.reflections.map((reflection, index) => <article className="echo-reflection" key={`${reflection.kind}-${index}`}><p>{reflection.text}</p>{reflection.kind === 'ai_interpretation' && <small>AI interpretation · not a fact or diagnosis</small>}{reflection.source_entry_ids.length > 0 && <div className="echo-sources"><span>Based on your entries:</span>{reflection.source_entry_ids.map(id => { const entry = journals.find(item => item.id === id); return entry ? <button key={id} onClick={() => onOpenEntry(entry)}>{formatDate(entry.created_at)} <ChevronRight size={12}/></button> : null; })}</div>}</article>) : <p className="muted">A few more journal entries may help reveal language patterns to reflect on.</p>}
              <label className="echo-ai-consent"><input type="checkbox" checked={data.ai_consent} disabled={saving === 'consent' || !data.ai_provider_available} onChange={event => void updateAiConsent(event.target.checked)}/><span><b>Allow optional AI reflections</b><small>{data.ai_provider_available ? 'When enabled, excerpts from this period and new journal entries are sent to the configured Groq provider to draft reflections. Off by default; you can switch it off at any time.' : 'Optional AI is unavailable because no Groq API key is configured. Your local pattern summaries continue to work.'}</small></span></label>
              {data.ai_fallback && <p className="echo-ai-fallback">The AI provider did not return a reflection this time. Showing summaries generated from your recorded entries instead.</p>}
            </section>
          </div>
        </div>

        <section className="panel echo-history"><PanelHeading icon={<Clock3 size={17}/>} title="Your theme feedback"/><p className="muted">Review how you have responded to themes. Feedback is saved only to your account.</p>
          {!data.feedback_history.length ? <p className="muted">Themes you confirm, edit, or dismiss will appear here.</p> : data.feedback_history.map(item => <div className="echo-history-row" key={item.key}><div><b>{item.title}</b><small>Updated {formatDate(item.updated_at)}</small></div><span className={`echo-status-pill ${item.status}`}>{titleCase(item.status)}</span></div>)}
        </section>
      </>}
    </>}
  </>;
}
