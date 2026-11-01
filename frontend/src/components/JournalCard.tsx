import { useState } from 'react';
import { BookHeart, Sparkles, Trash2 } from 'lucide-react';

export type JournalCardData = {
  id: number; transcript: string; emotion: string; confidence: number; sentiment: string;
  topics: string[]; phrases: string[]; reflection?: string | null; created_at: string;
  has_audio?: boolean; audio_data?: string;
};
type Props = { j: JournalCardData; onOpen?: () => void; expanded?: boolean; onDelete?: () => void };
const pretty = (s: string) => s.charAt(0).toUpperCase() + s.slice(1);

export function JournalCard({ j, onOpen, expanded = false, onDelete }: Props) {
  const [open, setOpen] = useState(expanded);
  return (
    <article className="journal-card">
      <button className="journal-card-head" onClick={() => expanded ? setOpen(!open) : onOpen?.()}>
        <span className="journal-date"><i className="date-icon"><BookHeart size={16} /></i><span><b>{new Date(j.created_at).toLocaleString(undefined, { month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit' })}</b><small>{j.topics.length ? j.topics.map(pretty).join(' · ') : 'Personal reflection'}</small></span></span>
        <span className={`emotion-pill ${j.emotion.split(' ')[0]}`}>{pretty(j.emotion)}</span>
      </button>
      {(open || !expanded) && <div className="journal-card-body">
        <p>{j.transcript}</p>
        {j.phrases?.length > 0 && <div className="phrase-list">{j.phrases.map((phrase, i) => <span key={i}>“{phrase}”</span>)}</div>}
        <div className="analysis-foot"><span>{j.sentiment} · {j.confidence ? `${Math.round(j.confidence * 100)}% language match` : 'unclear language pattern'}</span>{j.has_audio && j.audio_data && <audio controls src={j.audio_data} />}{onDelete && <button className="delete-link" onClick={onDelete}><Trash2 size={14} /> Delete entry</button>}</div>
        {j.reflection && <div className="ai-reflection"><Sparkles size={14} /><span><small>AI-GENERATED REFLECTION</small>{j.reflection}</span></div>}
      </div>}
    </article>
  );
}
