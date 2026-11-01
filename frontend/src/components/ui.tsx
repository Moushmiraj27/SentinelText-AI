import type { ReactNode } from 'react';
import { CircleHelp, Moon } from 'lucide-react';

export function PageIntro({ eyebrow, title, sub }: { eyebrow: string; title: string; sub: string }) {
  return <div className="page-intro"><div className="eyebrow">{eyebrow}</div><h1>{title}</h1><p>{sub}</p></div>;
}

export function EmptyState({ text, action }: { text: string; action?: () => void }) {
  return <div className="empty-card"><div className="empty-icon"><Moon size={21} /></div><h3>Your story starts whenever you’re ready</h3><p>{text}</p>{action && <button className="secondary" onClick={action}>Create your first entry <span aria-hidden="true">›</span></button>}</div>;
}

export function InlineNotice({ children }: { children: ReactNode }) {
  return <div className="notice-line"><CircleHelp size={16} />{children}</div>;
}

export function StatCard({ label, value }: { label: string; value: ReactNode }) {
  return <div className="stat-card"><span>{label}</span><b>{value}</b></div>;
}

export function PanelHeading({ icon, title }: { icon: ReactNode; title: string }) {
  return <div className="panel-heading"><span>{icon}{title}</span></div>;
}
