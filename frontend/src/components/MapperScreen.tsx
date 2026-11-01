import { FormEvent, useCallback, useEffect, useState } from 'react';
import { ArrowRight, Check, ChevronDown, ChevronRight, CircleHelp, LoaderCircle, Plus, RefreshCw, Shield, X } from 'lucide-react';
import { api } from '../services/api';
import type { JournalCardData } from './JournalCard';
import { PageIntro, PanelHeading } from './ui';

type SourceEntry = { id: number; date: string; transcript: string; emotion_explicitly_reported: boolean };
type Pattern = { id: string | number; relation_ids: number[]; situation: string; emotion: string; emotion_label: string; activity: string | null; status: 'suggested' | 'confirmed' | 'rejected'; frequency: number; entries: SourceEntry[]; manual?: boolean };
type JournalOption = { id: number; transcript: string; emotion: string; confidence: number; sentiment: string; topics: string[]; phrases: string[]; reflection?: string | null; created_at: string; has_audio?: boolean; audio_data?: string };
type Props = { onOpenEntry: (entry: JournalCardData) => void };
const dateLabel = (value: string) => new Date(value).toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' });
const pretty = (value: string) => value.replace(/\b\w/g, letter => letter.toUpperCase());

export default function MapperScreen({ onOpenEntry }: Props) {
  const [patterns, setPatterns] = useState<Pattern[]>([]);
  const [journals, setJournals] = useState<JournalOption[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [saving, setSaving] = useState(false);
  const [expanded, setExpanded] = useState<string | number | null>(null);
  const [editing, setEditing] = useState<string | number | null>(null);
  const [manualOpen, setManualOpen] = useState(false);
  const [draft, setDraft] = useState({ journal_id: '', situation: '', emotion: '', activity: '' });
  const [editDraft, setEditDraft] = useState({ situation: '', emotion: '', activity: '' });

  const load = useCallback(async () => {
    setLoading(true); setError('');
    try {
      const [patternRows, journalRows] = await Promise.all([api<Pattern[]>('/mapper/patterns'), api<JournalOption[]>('/journals')]);
      setPatterns(patternRows); setJournals(journalRows);
    } catch (reason) { setError(reason instanceof Error ? reason.message : 'Your patterns could not be loaded.'); }
    finally { setLoading(false); }
  }, []);
  useEffect(() => { void load(); }, [load]);

  const savePattern = async (pattern: Pattern, status: Pattern['status'], fields = { situation: pattern.situation, emotion: pattern.emotion, activity: pattern.activity || '' }) => {
    setSaving(true); setError('');
    try {
      await api(`/mapper/patterns/${pattern.id}`, { method: 'PUT', body: JSON.stringify({ ...fields, status }) });
      setEditing(null); await load();
    } catch (reason) { setError(reason instanceof Error ? reason.message : 'Your pattern update could not be saved.'); }
    finally { setSaving(false); }
  };

  const addManual = async (event: FormEvent) => {
    event.preventDefault(); setSaving(true); setError('');
    try {
      await api('/mapper/patterns', { method: 'POST', body: JSON.stringify({ ...draft, journal_id: draft.journal_id ? Number(draft.journal_id) : null }) });
      setDraft({ journal_id: '', situation: '', emotion: '', activity: '' }); setManualOpen(false); await load();
    } catch (reason) { setError(reason instanceof Error ? reason.message : 'Your pattern could not be added.'); }
    finally { setSaving(false); }
  };

  const openEntry = (entry: SourceEntry) => {
    const journal = journals.find(item => item.id === entry.id);
    onOpenEntry(journal || { id: entry.id, transcript: entry.transcript, emotion: entry.emotion_explicitly_reported ? 'user-reported' : 'language label', confidence: 0, sentiment: 'mixed / unclear', topics: [], phrases: [], reflection: null, created_at: entry.date, has_audio: false });
  };

  return <>
    <PageIntro eyebrow="TRIGGER & RELIEF MAPPER" title="Patterns you can review." sub="Explore situations, emotion language, and helpful activities mentioned in your own entries." />
    <div className="mapper-notice"><Shield size={16}/><span>Connections show that things appeared in the same entry; they do not mean one caused another. Emotion labels may come from the language analysis unless the entry explicitly states them.</span></div>
    <div className="mapper-toolbar"><span>{patterns.length} {patterns.length === 1 ? 'pattern' : 'patterns'} in your mapper</span><button className="primary" onClick={() => setManualOpen(value => !value)}><Plus size={16}/>{manualOpen ? 'Close form' : 'Add a pattern'}</button></div>

    {error && <div className="mapper-error" role="alert"><span>{error}</span><button className="secondary" onClick={() => void load()}><RefreshCw size={15}/> Retry</button></div>}
    {manualOpen && <form className="panel mapper-manual-form" onSubmit={addManual}><PanelHeading icon={<Plus size={17}/>} title="Add a pattern you recognize"/><p className="muted">This is your own pattern, marked confirmed because you added it. You can optionally connect one of your journal entries.</p><div className="mapper-form-grid"><label>Source journal entry (optional)<select value={draft.journal_id} onChange={event => setDraft({ ...draft, journal_id: event.target.value })}><option value="">No source entry</option>{journals.map(journal => <option key={journal.id} value={journal.id}>{dateLabel(journal.created_at)} · {journal.transcript.slice(0, 70)}</option>)}</select></label><label>Situation<input required minLength={2} maxLength={180} value={draft.situation} onChange={event => setDraft({ ...draft, situation: event.target.value })} placeholder="For example, a busy workday"/></label><label>Emotion<input required minLength={2} maxLength={40} value={draft.emotion} onChange={event => setDraft({ ...draft, emotion: event.target.value })} placeholder="What you felt or noticed"/></label><label>Helpful activity<input required minLength={2} maxLength={120} value={draft.activity} onChange={event => setDraft({ ...draft, activity: event.target.value })} placeholder="What you found helpful"/></label></div><button className="primary" disabled={saving}>{saving ? <LoaderCircle className="spin" size={16}/> : <Check size={16}/>} Save confirmed pattern</button></form>}

    {loading && !patterns.length ? <div className="mapper-loading" role="status"><LoaderCircle className="spin" size={19}/> Looking through your reported patterns…</div> : !patterns.length ? <div className="panel mapper-empty"><div><CircleHelp size={22}/></div><h2>{journals.length ? 'No patterns to review yet' : 'Start with a journal entry'}</h2><p>{journals.length ? 'As you write about situations and activities that helped, they will appear here with their source entries.' : 'Save a voice or written reflection first. The mapper only uses entries you choose to save.'}</p></div> : <div className="mapper-pattern-list">
      {patterns.map(pattern => <article className={`panel mapper-pattern ${pattern.status}`} key={pattern.id}>
        <div className="mapper-pattern-top"><div><span className={`mapper-status ${pattern.status}`}>{pattern.status === 'rejected' ? 'Dismissed' : pretty(pattern.status)}</span><span className="mapper-frequency">{pattern.manual && !pattern.entries.length ? 'User-added pattern' : `${pattern.frequency} ${pattern.frequency === 1 ? 'source entry' : 'source entries'}`}</span></div>{pattern.entries.length > 0 && <button className="mapper-source-toggle" aria-expanded={expanded === pattern.id} onClick={() => setExpanded(expanded === pattern.id ? null : pattern.id)}>{expanded === pattern.id ? 'Hide entries' : 'View source entries'} <ChevronDown size={15}/></button>}</div>
        {editing === pattern.id ? <div className="mapper-edit-grid"><label>Situation<input value={editDraft.situation} maxLength={180} onChange={event => setEditDraft({ ...editDraft, situation: event.target.value })}/></label><label>Emotion<input value={editDraft.emotion} maxLength={40} onChange={event => setEditDraft({ ...editDraft, emotion: event.target.value })}/></label><label>Helpful activity<input value={editDraft.activity} maxLength={120} onChange={event => setEditDraft({ ...editDraft, activity: event.target.value })}/></label><div><button className="mini-action" disabled={saving} onClick={() => void savePattern(pattern, pattern.status, editDraft)}>Save changes</button><button className="mini-action" onClick={() => setEditing(null)}>Cancel</button></div></div> : <div className="mapper-flow" aria-label="Situation associated with reported emotion language and helpful activity">
          <button className="mapper-node situation-node" onClick={() => setExpanded(expanded === pattern.id ? null : pattern.id)}><small>SITUATION MENTIONED</small><b>{pattern.situation}</b></button><ArrowRight className="mapper-arrow" size={17}/><button className="mapper-node emotion-node" onClick={() => setExpanded(expanded === pattern.id ? null : pattern.id)}><small>{pattern.emotion_label.toUpperCase()}</small><b>{pattern.emotion}</b></button><ArrowRight className="mapper-arrow" size={17}/><button className="mapper-node activity-node" onClick={() => setExpanded(expanded === pattern.id ? null : pattern.id)}><small>ACTIVITY MENTIONED</small><b>{pattern.activity || 'No activity recorded'}</b></button>
        </div>}
        {expanded === pattern.id && <div className="mapper-sources"><b>Source entries</b>{pattern.entries.map(entry => <button className="mapper-source-entry" key={entry.id} onClick={() => openEntry(entry)}><span><b>{dateLabel(entry.date)}</b><small>{entry.emotion_explicitly_reported ? 'Emotion directly described · ' : 'Emotion label inferred from wording · '}{entry.transcript.slice(0, 240)}</small></span><ChevronRight size={15}/></button>)}</div>}
        <div className="mapper-card-footer"><span>{pattern.status === 'confirmed' ? 'You confirmed this pattern.' : pattern.status === 'rejected' ? 'You dismissed this pattern; it will remain in your review history.' : 'Suggested association from words in the same entry.'}</span><div>{pattern.status !== 'confirmed' && <button className="mini-action mapper-confirm" disabled={saving} onClick={() => void savePattern(pattern, 'confirmed')}><Check size={13}/> Confirm</button>}<button className="mini-action" disabled={saving} onClick={() => { setEditing(pattern.id); setEditDraft({ situation: pattern.situation, emotion: pattern.emotion, activity: pattern.activity || '' }); }}>Edit</button>{pattern.status !== 'rejected' ? <button className="mini-action mapper-reject" disabled={saving} onClick={() => void savePattern(pattern, 'rejected')}><X size={13}/> Dismiss</button> : <button className="mini-action" disabled={saving} onClick={() => void savePattern(pattern, 'suggested')}>Restore suggestion</button>}</div></div>
      </article>)}
    </div>}
  </>;
}
