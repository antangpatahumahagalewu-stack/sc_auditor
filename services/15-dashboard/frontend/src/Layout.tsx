import { useState, useEffect } from 'react';
import { NavLink, Outlet, useLocation } from 'react-router-dom';
import { api } from './lib/api';

type NavItem = { to?: string; label: string; icon?: string; section?: boolean };

const NAV_ITEMS: NavItem[] = [
  { to: '/', label: 'Dashboard', icon: 'M10.707 2.293a1 1 0 00-1.414 0l-7 7a1 1 0 001.414 1.414L4 10.414V17a1 1 0 001 1h2a1 1 0 001-1v-2a1 1 0 011-1h2a1 1 0 011 1v2a1 1 0 001 1h2a1 1 0 001-1v-6.586l.293.293a1 1 0 001.414-1.414l-7-7z' },
  { to: '/agent', label: 'Agent', icon: 'M13 6a3 3 0 11-6 0 3 3 0 016 0zM18 8a2 2 0 11-4 0 2 2 0 014 0zM14 15a4 4 0 00-8 0v3h8v-3zM6 8a2 2 0 11-4 0 2 2 0 014 0zM16 18v-3a5.972 5.972 0 00-.75-2.906A3.005 3.005 0 0119 15v3h-3zM4.75 12.094A5.973 5.973 0 004 15v3H1v-3a3.005 3.005 0 013.75-2.906z' },
  { to: '/agent/intelligence', label: 'Intelligence', icon: 'M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z' },
  { to: '/audits', label: 'Audits', icon: 'M4 4a2 2 0 012-2h4.586A2 2 0 0112 2.586L15.414 6A2 2 0 0116 7.414V16a2 2 0 01-2 2H6a2 2 0 01-2-2V4z' },
  { to: '/programs', label: 'Programs', icon: 'M5 3a2 2 0 00-2 2v2a2 2 0 002 2h2a2 2 0 002-2V5a2 2 0 00-2-2H5zM5 11a2 2 0 00-2 2v2a2 2 0 002 2h2a2 2 0 002-2v-2a2 2 0 00-2-2H5zM11 5a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2V5zM11 13a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2v-2z' },
  { to: '/metrics', label: 'Metrics', icon: 'M2 11a1 1 0 011-1h2a1 1 0 011 1v5a1 1 0 01-1 1H3a1 1 0 01-1-1v-5zM8 7a1 1 0 011-1h2a1 1 0 011 1v9a1 1 0 01-1 1H9a1 1 0 01-1-1V7zM14 4a1 1 0 011-1h2a1 1 0 011 1v12a1 1 0 01-1 1h-2a1 1 0 01-1-1V4z' },
  { to: '/daemon', label: 'Daemon', icon: 'M11.3 1.046A1 1 0 0112 2v5h4a1 1 0 01.82 1.573l-7 10A1 1 0 018 18v-5H4a1 1 0 01-.82-1.573l7-10a1 1 0 011.12-.38z' },
  { to: '/settings', label: 'Settings', icon: 'M11.49 3.17c-.38-1.56-2.6-1.56-2.98 0a1.532 1.532 0 01-2.286.948c-1.372-.836-2.942.734-2.106 2.106.54.886.061 2.042-.947 2.287-1.561.379-1.561 2.6 0 2.978a1.532 1.532 0 01.947 2.287c-.836 1.372.734 2.942 2.106 2.106a1.532 1.532 0 012.287.947c.379 1.561 2.6 1.561 2.978 0a1.533 1.533 0 012.287-.947c1.372.836 2.942-.734 2.106-2.106a1.533 1.533 0 01.947-2.287c1.561-.379 1.561-2.6 0-2.978a1.532 1.532 0 01-.947-2.287c.836-1.372-.734-2.942-2.106-2.106a1.532 1.532 0 01-2.287-.947zM10 13a3 3 0 100-6 3 3 0 000 6z' },
  { to: '/updates', label: 'Updates', icon: 'M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-8-3a1 1 0 00-.867.5 1 1 0 11-1.731-1A3 3 0 0113 8a3.001 3.001 0 01-2 2.83V11a1 1 0 11-2 0v-1a1 1 0 011-1 1 1 0 100-2zm0 8a1 1 0 100-2 1 1 0 000 2z' },
  { to: '/services', label: 'Services', icon: 'M4 4a2 2 0 012-2h8a2 2 0 012 2v12a2 2 0 01-2 2H6a2 2 0 01-2-2V4zm2 0v12h8V4H6z' },
  { to: '/pipeline', label: 'Pipeline', icon: 'M5 3a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2V5a2 2 0 00-2-2H5zm0 2h10v10H5V5z' },
  { to: '/scanner', label: 'Scanner', icon: 'M10 2a8 8 0 100 16 8 8 0 000-16zM9 6a1 1 0 112 0v4a1 1 0 11-2 0V6zm0 8a1 1 0 112 0 1 1 0 01-2 0z' },
  { to: '/config', label: 'Config', icon: 'M11.49 3.17c-.38-1.56-2.6-1.56-2.98 0a1.532 1.532 0 01-2.286.948c-1.372-.836-2.942.734-2.106 2.106.54.886.061 2.042-.947 2.287-1.561.379-1.561 2.6 0 2.978a1.532 1.532 0 01.947 2.287c-.836 1.372.734 2.942 2.106 2.106a1.532 1.532 0 012.287.947c.379 1.561 2.6 1.561 2.978 0a1.533 1.533 0 012.287-.947c1.372.836 2.942-.734 2.106-2.106a1.533 1.533 0 01.947-2.287c1.561-.379 1.561-2.6 0-2.978a1.532 1.532 0 01-.947-2.287c.836-1.372-.734-2.942-2.106-2.106a1.532 1.532 0 01-2.287-.947zM10 13a3 3 0 100-6 3 3 0 000 6z' },
  { to: '/notifier', label: 'Notifier', icon: 'M2.003 5.884L10 9.882l7.997-3.998A2 2 0 0016 4H4a2 2 0 00-1.997 1.884zM18 8.118l-8 4-8-4V14a2 2 0 002 2h12a2 2 0 002-2V8.118z' },
  { to: '/webhooks', label: 'Webhooks', icon: 'M12.395 2.553a1 1 0 00-1.45-.385c-.345.23-.614.558-.822.88-.214.33-.403.713-.57 1.116-.334.804-.614 1.768-.84 2.734a31.365 31.365 0 00-.613 3.58 2.64 2.64 0 01-.945-1.067c-.328-.68-.398-1.534-.398-2.654A1 1 0 005.05 6.05 6.981 6.981 0 003 11a7 7 0 1011.95-4.95c-.592-.591-.98-.985-1.348-1.467-.363-.476-.724-1.063-1.207-2.03zM12.12 15.12A3 3 0 017 13s.879.5 2.5.5c0-1 .5-4 1.25-4.5.5 1 .786 1.293 1.371 1.879A2.99 2.99 0 0113 13a2.99 2.99 0 01-.879 2.121z' },
  { to: '/reports', label: 'Reports', icon: 'M9 2a1 1 0 000 2h2a1 1 0 100-2H9zM4 5a2 2 0 012-2 3 3 0 003 3h2a3 3 0 003-3 2 2 0 012 2v11a2 2 0 01-2 2H6a2 2 0 01-2-2V5zm3 4a1 1 0 000 2h.01a1 1 0 100-2H7zm3 0a1 1 0 000 2h3a1 1 0 100-2h-3zm-3 4a1 1 0 100 2h.01a1 1 0 100-2H7zm3 0a1 1 0 100 2h3a1 1 0 100-2h-3z' },
  { to: '/source/:auditId', label: 'Source', icon: 'M10 20l4-16h4l-4 16h-4zM2 10l4-4 4 4-4 4-4-4zM14 14l4 4-4 4 4-4-4-4z' },
  { to: '/scheduler', label: 'Scheduler', icon: 'M10 18a8 8 0 100-16 8 8 0 000 16zm1-12a1 1 0 10-2 0v4a1 1 0 00.293.707l2.828 2.829a1 1 0 101.415-1.415L11 9.586V6z' },
  { to: '/feedback', label: 'Feedback', icon: 'M18 13V5a2 2 0 00-2-2H4a2 2 0 00-2 2v8a2 2 0 002 2h3l3 3 3-3h3a2 2 0 002-2zM5 7a1 1 0 011-1h8a1 1 0 110 2H6a1 1 0 01-1-1zm1 3a1 1 0 100 2h4a1 1 0 100-2H6z' },

  // ── Case Management (Agenda 05) ─────────────────────
  { label: 'CASES', section: true },
  { to: '/cases', label: 'Cases', icon: 'M9 2a1 1 0 000 2h2a1 1 0 100-2H9zM4 5a2 2 0 012-2 3 3 0 003 3h2a3 3 0 003-3 2 2 0 012 2v11a2 2 0 01-2 2H6a2 2 0 01-2-2V5zm3 4a1 1 0 000 2h.01a1 1 0 100-2H7zm3 0a1 1 0 000 2h3a1 1 0 100-2h-3zm-3 4a1 1 0 100 2h.01a1 1 0 100-2H7zm3 0a1 1 0 100 2h3a1 1 0 100-2h-3z' },
  { to: '/archive', label: 'Archive', icon: 'M4 3a2 2 0 100 4h12a2 2 0 100-4H4zm0 6a2 2 0 100 4h12a2 2 0 100-4H4zm0 6a2 2 0 100 4h12a2 2 0 100-4H4z' },
];

export default function Layout() {
  const [daemonStatus, setDaemonStatus] = useState<string>('stopped');
  const [theme, setTheme] = useState<'dark' | 'light'>('dark');
  const location = useLocation();
  const currentTitle = NAV_ITEMS.find(i => i.to === location.pathname)?.label || 'Vyper';

  useEffect(() => {
    const saved = localStorage.getItem('vyper-theme');
    if (saved === 'light') setTheme('light');
    document.documentElement.className = theme;
  }, [theme]);

  useEffect(() => {
    api.getDaemonStatus().then(r => setDaemonStatus(r.data?.status || 'stopped')).catch(() => {});
    const es = new EventSource('/events');
    es.addEventListener('daemon_status', (e: MessageEvent) => {
      try { setDaemonStatus(JSON.parse(e.data).status); } catch {}
    });
    return () => es.close();
  }, []);

  const toggleTheme = () => setTheme(t => t === 'dark' ? 'light' : 'dark');

  const isOnline = daemonStatus === 'running';
  const isPaused = daemonStatus === 'paused';
  const statusDot = isOnline ? 'bg-green-500 shadow-[0_0_6px_rgba(34,197,94,0.5)]' : isPaused ? 'bg-yellow-500 shadow-[0_0_6px_rgba(245,158,11,0.5)]' : 'bg-red-500 shadow-[0_0_6px_rgba(239,68,68,0.5)]';
  const statusLabel = isOnline ? 'Daemon Running' : isPaused ? 'Daemon Paused' : 'Daemon Offline';

  return (
    <div className="flex h-screen overflow-hidden dark:bg-[#0f0f13] dark:text-[#f4f4f5] light:bg-[#f5f5f5] light:text-[#09090b]">
      {/* Sidebar */}
      <aside className="w-56 flex-shrink-0 dark:bg-[#18181b] light:bg-white border-r dark:border-[#27272a] light:border-[#e4e4e7] flex flex-col">
        <div className="h-14 flex items-center gap-2.5 px-5 border-b dark:border-[#27272a] light:border-[#e4e4e7]">
          <div className="w-8 h-8 rounded-lg bg-vyper-500 flex items-center justify-center text-white font-bold text-lg">V</div>
          <span className="font-semibold text-base">Vyper</span>
          <span className="text-[10px] dark:text-[#a1a1aa] light:text-[#71717a] ml-auto font-mono">v1.0.0</span>
        </div>

        <nav className="flex-1 overflow-y-auto py-3 px-2 space-y-0.5">
          {NAV_ITEMS.map((item) => {
            if (item.section) {
              return (
                <div key={item.label} className="px-3 pt-4 pb-1.5 text-[10px] font-semibold uppercase tracking-widest dark:text-[#52525b] light:text-[#a1a1aa]">
                  {item.label}
                </div>
              );
            }
            const { to, label, icon } = item as { to: string; label: string; icon: string };
            const active = location.pathname === to || (to !== '/' && location.pathname.startsWith(to));
            return (
              <NavLink key={to} to={to} end={to === '/'}
                className={`sidebar-link flex items-center gap-3 px-3 py-2 rounded-lg text-sm ${
                  active
                    ? 'dark:bg-vyper-500/10 light:bg-vyper-500/5 dark:text-vyper-300 light:text-vyper-600 font-medium'
                    : 'dark:text-[#a1a1aa] light:text-[#71717a]'
                }`}>
                <svg viewBox="0 0 20 20" fill="currentColor" className="w-4 h-4 flex-shrink-0">
                  <path d={icon!} />
                </svg>
                {label}
              </NavLink>
            );
          })}
        </nav>

        <div className="px-3 py-3 border-t dark:border-[#27272a] light:border-[#e4e4e7]">
          <div className="flex items-center gap-2 px-3 py-2 text-xs dark:text-[#a1a1aa] light:text-[#71717a]">
            <span className={`w-2 h-2 rounded-full ${statusDot}`} />
            <span>{statusLabel}</span>
          </div>
        </div>
      </aside>

      {/* Main */}
      <div className="flex-1 flex flex-col overflow-hidden">
        <header className="h-14 flex-shrink-0 flex items-center justify-between px-6 border-b dark:bg-[#18181b] light:bg-white dark:border-[#27272a] light:border-[#e4e4e7]">
          <h1 className="text-lg font-semibold">{currentTitle}</h1>
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2 text-sm">
              <span className={`w-2 h-2 rounded-full ${statusDot}`} />
              <span className="dark:text-[#a1a1aa] light:text-[#71717a]">Daemon</span>
            </div>
            <button onClick={toggleTheme} className="p-2 rounded-lg hover:dark:bg-[#27272a] hover:light:bg-[#f4f4f5] transition-colors" title="Toggle theme">
              {theme === 'dark' ? (
                <svg className="w-4 h-4" viewBox="0 0 20 20" fill="currentColor">
                  <path fillRule="evenodd" d="M10 2a1 1 0 011 1v1a1 1 0 11-2 0V3a1 1 0 011-1zm4 8a4 4 0 11-8 0 4 4 0 018 0zm-.464 4.95l.707.707a1 1 0 001.414-1.414l-.707-.707a1 1 0 00-1.414 1.414zm2.12-10.607a1 1 0 010 1.414l-.706.707a1 1 0 11-1.414-1.414l.707-.707a1 1 0 011.414 0zM17 11a1 1 0 100-2h-1a1 1 0 100 2h1zm-7 4a1 1 0 011 1v1a1 1 0 11-2 0v-1a1 1 0 011-1zM5.05 6.464A1 1 0 106.465 5.05l-.708-.707a1 1 0 00-1.414 1.414l.707.707zm1.414 8.486l-.707.707a1 1 0 01-1.414-1.414l.707-.707a1 1 0 011.414 1.414zM4 11a1 1 0 100-2H3a1 1 0 000 2h1z" clipRule="evenodd" />
                </svg>
              ) : (
                <svg className="w-4 h-4" viewBox="0 0 20 20" fill="currentColor">
                  <path d="M17.293 13.293A8 8 0 016.707 2.707a8.001 8.001 0 1010.586 10.586z" />
                </svg>
              )}
            </button>
          </div>
        </header>

        <main className="flex-1 overflow-y-auto p-6">
          <Outlet />
        </main>

        <footer className="flex-shrink-0 px-6 py-2 text-xs dark:text-[#a1a1aa] light:text-[#71717a] border-t dark:border-[#27272a] light:border-[#e4e4e7] flex items-center justify-between">
          <span>Vyper v1.0.0 — Smart Contract Bug Hunter</span>
          <FooterTime />
        </footer>
      </div>
    </div>
  );
}

function FooterTime() {
  const [time, setTime] = useState('');
  useEffect(() => {
    const update = () => setTime(new Date().toLocaleDateString('en-US', { weekday: 'short', year: 'numeric', month: 'short', day: 'numeric' }) + ' — ' + new Date().toLocaleTimeString('en-US'));
    update();
    const id = setInterval(update, 1000);
    return () => clearInterval(id);
  }, []);
  return <span>{time}</span>;
}
