import { useCallback, useEffect, useState } from 'react';
import { Activity, ChevronRight, Clock3, Heart, LoaderCircle, RefreshCw, Shield } from 'lucide-react';
import { api } from '../services/api';
import type { JournalCardData } from './JournalCard';
import { PageIntro, PanelHeading } from './ui';

type CopingItem = { id: number; activity: string; description: string; helpful_count: number; explanation: string; source_entry_ids: number[]; source_situation: string | null };
type CopingData = { items: CopingItem[]; history: { id: number; activity: string; feedback: string | null; created_at: string }[]; has_journals: boolean; safety_alert: boolean; safety_message: string | null };
type Props = { onOpenEntry: (entry: JournalCardData) => void; onStartActivity: (activity: CopingItem) => void };
const pretty = (value: string) => value.replace(/\b\w/g, letter => letter.toUpperCase());
const dateLabel = (value: string) => new Date(value).toLocaleDateString(undefined, { month: 'short', day: 'numeric' });

export default function CopingScreen({ onOpenEntry, onStartActivity }: Props) {
  const [data, setData] = useState<CopingData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [saving, setSaving] = useState<number | null>(null);

  const load = useCallback(async () => {
    setLoading(true); setError('');
    try { setData(await api('/recommendations')); }
    catch (reason) { setError(reason instanceof Error ? reason.message : 'Coping Intelligence could not be loaded.'); }
    finally { setLoading(false); }
  }, []);
  useEffect(() => {
    void load();
    const refresh = () => void load();
    window.addEventListener('sentinel:recommendations-updated', refresh);
    return () => window.removeEventListener('sentinel:recommendations-updated', refresh);
  }, [load]);

  const sendFeedback = async (item: CopingItem, feedback: 'helpful' | 'somewhat_helpful' | 'not_helpful') => {
    setSaving(item.id); setError('');
    try { await api(`/recommendations/${item.id}/feedback`, { method: 'POST', body: JSON.stringify({ feedback }) }); await load(); }
    catch (reason) { setError(reason instanceof Error ? reason.message : 'Your feedback could not be saved.'); }
    finally { setSaving(null); }
  };

  const openEntry = async (id: number) => {
    try {
      const entries = await api<JournalCardData[]>('/journals');
      const entry = entries.find(row => row.id === id);
      if (entry) onOpenEntry(entry);
      else setError('That source entry is no longer available.');
    } catch (reason) { setError(reason instanceof Error ? reason.message : 'The source journal entry could not be opened.'); }
  };

  return <>
    <PageIntro eyebrow="COPING INTELLIGENCE" title="Small options, shaped by your words." sub="Explore practical ideas connected to what you have written and the feedback you have shared. You decide what fits." />
    <div className="mapper-notice"><Shield size={16}/><span>These are optional self-reflection ideas, not treatment or medical advice. Recommendations are generated locally from your saved entries and feedback; journal text is not sent to an AI provider for this feature.</span></div>
    {error && <div className="mapper-error" role="alert"><span>{error}</span><button className="secondary" onClick={() => void load()}><RefreshCw size={15}/> Retry</button></div>}
    {loading && !data ? <div className="mapper-loading" role="status"><LoaderCircle className="spin" size={19}/> Reviewing your preferences…</div> : data && <>
      {data.safety_alert && <div className="coping-safety" role="alert"><Shield size={20}/><p>{data.safety_message}</p></div>}
      {!data.has_journals && !data.items.length && <div className="panel coping-empty"><div className="coping-empty-icon"><Heart size={21}/></div><h2>Suggestions will start with your entries</h2><p>Save a voice or written reflection first, or add a confirmed mapper pattern. SentinelText does not use sample history.</p></div>}
      {(data.has_journals || data.items.length > 0) && !data.safety_alert && <>
        <section className="coping-section"><div className="coping-section-heading"><div><span className="eyebrow">YOUR CURRENT OPTIONS</span><h2>Ideas to consider</h2></div><span className="coping-note">Based on your own entries and feedback</span></div>
          {!data.items.length ? <div className="panel coping-empty compact"><div className="coping-empty-icon"><Activity size={20}/></div><h3>No new suggestions right now</h3><p>We avoid repeating activities you recently saw or marked as not helpful. Your feedback history remains below.</p></div> : <div className="recommend-grid coping-grid">{data.items.map((item, index) => <article className="recommend-card coping-card" key={item.id}>
            <div className={`recommend-icon hue-${index}`}><Activity size={20}/></div><span className="eyebrow">OPTIONAL ACTIVITY</span><h3>{pretty(item.activity)}</h3><p>{item.description}</p>
            <div className="coping-explanation"><b>Why this is shown</b><p>{item.explanation}</p>{item.source_situation && <small>Confirmed association · “{item.source_situation}”</small>}</div>
            {item.source_entry_ids.length > 0 && <div className="coping-sources"><span>Related entries</span>{item.source_entry_ids.slice(0, 4).map(id => <button key={id} onClick={() => void openEntry(id)}>Open entry <ChevronRight size={12}/></button>)}</div>}
            <button className="secondary coping-start" onClick={() => onStartActivity(item)}>Explore this activity <ChevronRight size={15}/></button>
            <div className="feedback"><span>Did this feel helpful?</span>{([['helpful', 'Helpful'], ['somewhat_helpful', 'Somewhat helpful'], ['not_helpful', 'Not helpful']] as const).map(([value, label]) => <button key={value} disabled={saving === item.id} aria-pressed={false} onClick={() => void sendFeedback(item, value)}>{saving === item.id ? <LoaderCircle className="spin" size={12}/> : label}</button>)}</div>
          </article>)}</div>}
        </section>
      </>}
      <section className="panel coping-history"><PanelHeading icon={<Clock3 size={17}/>} title="Recommendation history"/><p className="muted">Your feedback changes future suggestions. Activities marked not helpful are removed from future options, and recently shown options are not repeated.</p>
        {!data.history.length ? <p className="muted">Recommendations and feedback will appear here when available.</p> : data.history.map(item => <div className="history-row" key={item.id}><span>{pretty(item.activity)}</span><span className="feedback-state">{item.feedback ? pretty(item.feedback.replaceAll('_', ' ')) : 'Awaiting your feedback'}</span><small>{dateLabel(item.created_at)}</small></div>)}
      </section>
    </>}
  </>;
}
