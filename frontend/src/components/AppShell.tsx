import type { ReactNode } from 'react';
import { useState } from 'react';
import { Activity, AudioLines, ChevronRight, Heart, Home, LockKeyhole, LogOut, Mic, Moon, Plus, Settings, Shield, Sparkles, Sun, type LucideIcon } from 'lucide-react';

export type AppPage = 'Landing' | 'Dashboard' | 'Voice Journal' | 'Emotional Echo' | 'Trigger & Relief' | 'Coping Intelligence' | 'Journal History' | 'Settings & Privacy';

const navigation: { page: AppPage; icon: LucideIcon }[] = [
  { page: 'Dashboard', icon: Home },
  { page: 'Voice Journal', icon: Mic },
  { page: 'Emotional Echo', icon: AudioLines },
  { page: 'Trigger & Relief', icon: Activity },
  { page: 'Coping Intelligence', icon: Sparkles },
  { page: 'Journal History', icon: Heart },
  { page: 'Settings & Privacy', icon: Settings },
];

type Props = { page: AppPage; onNavigate: (page: AppPage) => void; children: ReactNode; currentUser: { name: string; email: string }; onLogout: () => void; theme: 'light' | 'dark'; onToggleTheme: () => void };

export function AppShell({ page, onNavigate, children, currentUser, onLogout, theme, onToggleTheme }: Props) {
  const [profileOpen, setProfileOpen] = useState(false);
  const title = page === 'Trigger & Relief' ? 'Trigger & Relief Mapper' : page;
  return (
    <div className="app-shell" data-theme={theme}>
      <aside className="app-sidebar" aria-label="Main navigation">
        <button className="brand" onClick={() => onNavigate('Dashboard')} aria-label="SentinelText dashboard">
          <span className="brand-mark"><AudioLines size={21} strokeWidth={2.2} /></span>
          <span className="brand-wordmark">sentinel<span>text</span><small>YOUR VOICE. YOUR WELL-BEING.</small></span>
        </button>
        <div className="sidebar-label">YOUR SPACE</div>
        <nav className="sidebar-nav">
          {navigation.map(({ page: item, icon: Icon }) => (
            <button key={item} className={`sidebar-link ${page === item ? 'is-active' : ''}`} aria-current={page === item ? 'page' : undefined} onClick={() => onNavigate(item)}>
              <Icon size={18} strokeWidth={1.9} /><span>{item}</span>{item === 'Voice Journal' && <Plus className="sidebar-link-plus" size={15} />}
            </button>
          ))}
        </nav>
        <div className="sidebar-footer">
          <div className="sidebar-reassurance"><Shield size={17} /><span><b>Your space, your pace.</b><small>Your journal is private to this profile.</small></span></div>
          <div className="sidebar-profile"><span className="profile-avatar">{currentUser.name.slice(0,1).toUpperCase()}</span><span><b>{currentUser.name}</b><small>{currentUser.email}</small></span><LockKeyhole size={15} /></div>
        </div>
      </aside>

      <div className="app-main-column">
        <header className="app-topbar">
          <div className="topbar-title"><span className="topbar-context">My space</span><ChevronRight size={14} /><b>{title}</b></div>
          <div className="topbar-actions">
            <span className="topbar-private"><i />Private space</span>
            <button className="topbar-icon-button theme-toggle" onClick={onToggleTheme} aria-label={`Switch to ${theme === 'light' ? 'dark' : 'light'} mode`} title={`Switch to ${theme === 'light' ? 'dark' : 'light'} mode`}>{theme === 'light' ? <Sun size={18} /> : <Moon size={18} />}<span>{theme === 'light' ? 'Dark' : 'Light'}</span></button>
            <button className="topbar-icon-button" onClick={() => onNavigate('Settings & Privacy')} aria-label="Open settings"><Settings size={18} /></button>
            <div className="profile-menu-wrap"><button className="profile-menu-trigger" onClick={() => setProfileOpen(!profileOpen)} aria-expanded={profileOpen} aria-label="Open profile menu"><span className="profile-avatar profile-avatar-small">{currentUser.name.slice(0,1).toUpperCase()}</span></button>{profileOpen&&<div className="profile-menu"><b>{currentUser.name}</b><small>{currentUser.email}</small><button onClick={() => {setProfileOpen(false);onLogout()}}><LogOut size={15}/>Sign out</button></div>}</div>
          </div>
        </header>
        <main className="app-content">{children}</main>
      </div>
    </div>
  );
}
