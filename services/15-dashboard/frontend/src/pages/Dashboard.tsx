import { useEffect, useState } from 'react';
import { api, type Audit, type DaemonState, type MetricsSummary, type PipelineStats } from '../lib/api';
import { useSSE } from '../hooks/useSSE';

type ModalState = { open: false } | { open: true; loading: boolean; error: string };

const CHAINS = [
  { value: 'ethereum', label: 'Ethereum' },
  { value: 'bsc', label: 'BSC' },
  { value: 'polygon', label: 'Polygon' },
  { value: 'arbitrum', label: 'Arbitrum' },
  { value: 'optimism', label: 'Optimism' },
  { value: 'avalanche', label: 'Avalanche' },
  { value: 'solana', label: 'Solana' },
];

function statusBadge(state: string) {
  const colors: Record<string, string> = {
    COMPLETED: 'bg-green-500/20 text-green-400',
    RUNNING: 'bg-blue-500/20 text-blue-400',
    PENDING: 'bg-yellow-500/20 text-yellow-400',
    FAILED: 'bg-red-500/20 text-red-400',
    SCANNING: 'bg-purple-500/20 text-purple-400',
  };
  const cls = colors[state] || 'bg-gray-500/20 text-gray-400';
  return (
    <span className={`px-2 py-0.5 rounded-full text-xs font-semibold ${cls}`}>
      {state}
    </span>
  );
}

function durationStr(seconds?: number): string {
  if (seconds == null) return '—';
  if (seconds < 60) return `${seconds}s`;
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  return `${m}m ${s}s`;
}

function shortId(id: string): string {
  return id.length > 8 ? `${id.slice(0, 8)}...` : id;
}

function statCardClass(): string {
  return 'rounded-xl p-6 dark:bg-[#1a1a1e] dark:border dark:border-[#27272a] light:bg-white light:border light:border-[#e4e4e7] hover:dark:border-vyper-500 hover:dark:shadow-[0_4px_20px_rgba(108,92,231,0.1)] hover:light:border-vyper-500 hover:light:shadow-[0_4px_20px_rgba(108,92,231,0.08)] transition-all duration-200';
}

function inputFieldClass(): string {
  return 'w-full px-3 py-2 rounded-lg text-sm outline-none focus:border-vyper-500 focus:shadow-[0_0_0_2px_rgba(108,92,231,0.2)] dark:bg-[#18181b] dark:border dark:border-[#27272a] dark:text-[#f4f4f5] light:bg-white light:border light:border-[#d4d4d8] light:text-[#09090b] transition-all';
}

export default function Dashboard() {
  const [audits, setAudits] = useState<Audit[]>([]);
  const [auditsLoading, setAuditsLoading] = useState(true);
  const [stats, setStats] = useState<PipelineStats | null>(null);
  const [metrics, setMetrics] = useState<MetricsSummary | null>(null);
  const [daemon, setDaemon] = useState<DaemonState | null>(null);
  const [daemonToggling, setDaemonToggling] = useState(false);
  const [syncing, setSyncing] = useState(false);
  const [modal, setModal] = useState<ModalState>({ open: false });
  const [clock, setClock] = useState('');
  const [actionError, setActionError] = useState('');

  // Real-time clock
  useEffect(() => {
    const update = () =>
      setClock(
        new Date().toLocaleString('en-US', {
          weekday: 'long',
          year: 'numeric',
          month: 'long',
          day: 'numeric',
          hour: '2-digit',
          minute: '2-digit',
        })
      );
    update();
    const id = setInterval(update, 1000);
    return () => clearInterval(id);
  }, []);

  // Fetch all dashboard data
  useEffect(() => {
    let cancelled = false;

    async function load() {
      try {
        const [auditsRes, statsRes, daemonRes, metricsRes] = await Promise.all([
          api.getAudits({ limit: 10 }),
          api.getStats(),
          api.getDaemonStatus(),
          api.getMetrics(),
        ]);

        if (cancelled) return;

        setAudits(auditsRes.data || []);
        setStats(statsRes.data || null);
        setDaemon(daemonRes.data || null);
        setMetrics(metricsRes.data || null);
      } catch {
        // leave defaults (loading states)
      } finally {
        if (!cancelled) setAuditsLoading(false);
      }
    }

    load();
    return () => { cancelled = true; };
  }, []);

  // SSE for live updates to daemon status
  useSSE((msg) => {
    if (msg.event === 'daemon_status' && msg.data) {
      setDaemon((prev) => prev ? { ...prev, status: msg.data.status } : prev);
    }
    if (msg.event === 'audit_complete' || msg.event === 'audit_progress') {
      // Refresh audit list on progress/complete events
      api.getAudits({ limit: 10 }).then((r) => setAudits(r.data || [])).catch(() => {});
    }
  });

  const daemonIsRunning = daemon?.status === 'running';
  const daemonIsPaused = daemon?.status === 'paused';
  const daemonBadgeColor = daemonIsRunning
    ? 'bg-green-500/10 text-green-400'
    : daemonIsPaused
      ? 'bg-yellow-500/10 text-yellow-400'
      : 'bg-red-500/10 text-red-400';
  const daemonBadgeLabel = daemonIsRunning ? 'Active' : daemonIsPaused ? 'Paused' : 'Offline';
  const daemonStatusLabel = daemonIsRunning ? 'Running' : daemonIsPaused ? 'Paused' : 'Stopped';
  const daemonDetail =
    daemonIsRunning && daemon?.last_run_at
      ? `Last run: ${new Date(daemon.last_run_at).toLocaleString()}`
      : daemonIsRunning
        ? 'Waiting for first run...'
        : 'Click "Toggle Daemon" to start';

  // ── Handlers ──────────────────────────────────────

  async function handleToggleDaemon() {
    setDaemonToggling(true);
    setActionError('');
    try {
      if (daemonIsRunning) {
        await api.daemonStop();
      } else {
        await api.daemonStart();
      }
      // Refresh daemon status
      const res = await api.getDaemonStatus();
      setDaemon(res.data || null);
    } catch (err: any) {
      setActionError(err?.message || 'Failed to toggle daemon');
    } finally {
      setDaemonToggling(false);
    }
  }

  async function handleRunSync() {
    setSyncing(true);
    setActionError('');
    try {
      await api.daemonSync();
      const res = await api.getDaemonStatus();
      setDaemon(res.data || null);
    } catch (err: any) {
      setActionError(err?.message || 'Failed to run sync');
    } finally {
      setSyncing(false);
    }
  }

  async function handleStartAudit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setModal({ open: true, loading: true, error: '' });

    const form = e.currentTarget;
    const data = new FormData(form);

    try {
      await api.startAudit({
        chain: String(data.get('chain') || 'ethereum'),
        address: String(data.get('address') || ''),
        program: String(data.get('program') || ''),
        priority: Number(data.get('priority')) || 5,
      });

      setModal({ open: false });
      setActionError('');

      // Refresh audits and stats
      const [auditsRes, statsRes] = await Promise.all([
        api.getAudits({ limit: 10 }),
        api.getStats(),
      ]);
      setAudits(auditsRes.data || []);
      setStats(statsRes.data || null);
    } catch (err: any) {
      setModal({ open: true, loading: false, error: err?.message || 'Failed to start audit' });
    }
  }

  const tpRate = metrics?.true_positive_rate ?? 0;

  return (
    <div className="space-y-6">
      {/* ── Welcome Header ─────────────────────────── */}
      <div>
        <h2 className="text-2xl font-bold">Welcome to Vyper</h2>
        <p className="dark:text-[#a1a1aa] light:text-[#71717a] mt-1">
          Smart contract bug hunting platform —{' '}
          <span className="font-mono text-sm">{clock}</span>
        </p>
      </div>

      {/* ── Error Banner ────────────────────────────── */}
      {actionError && (
        <div className="rounded-xl p-4 bg-red-500/10 border border-red-500/20 text-red-400 text-sm flex items-center gap-2">
          <svg className="w-4 h-4 flex-shrink-0" viewBox="0 0 20 20" fill="currentColor">
            <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
          </svg>
          <span>{actionError}</span>
          <button onClick={() => setActionError('')} className="ml-auto text-red-400/70 hover:text-red-400">✕</button>
        </div>
      )}

      {/* ── Stat Cards ──────────────────────────────── */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Total Audits */}
        <div className={statCardClass()}>
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm dark:text-[#a1a1aa] light:text-[#71717a]">Total Audits</span>
            <span className="text-xs px-2 py-0.5 rounded-full bg-vyper-500/10 text-vyper-400 font-medium">+12%</span>
          </div>
          <div className="text-3xl font-bold">{stats?.total_audits ?? '—'}</div>
          <div className="text-xs dark:text-[#a1a1aa] light:text-[#71717a] mt-1">Last 30 days</div>
        </div>

        {/* Critical Findings */}
        <div className={statCardClass()}>
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm dark:text-[#a1a1aa] light:text-[#71717a]">Critical Findings</span>
            <span className="text-xs px-2 py-0.5 rounded-full bg-red-500/10 text-red-400 font-medium">High Risk</span>
          </div>
          <div className="text-3xl font-bold text-red-400">{metrics?.critical_findings ?? '—'}</div>
          <div className="text-xs dark:text-[#a1a1aa] light:text-[#71717a] mt-1">Unresolved</div>
        </div>

        {/* TP Rate */}
        <div className={statCardClass()}>
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm dark:text-[#a1a1aa] light:text-[#71717a]">TP Rate</span>
            <span className="text-xs px-2 py-0.5 rounded-full bg-green-500/10 text-green-400 font-medium">Accuracy</span>
          </div>
          <div className="text-3xl font-bold text-green-400">
            {metrics != null ? `${(tpRate * 100).toFixed(1)}%` : '—'}
          </div>
          <div className="text-xs dark:text-[#a1a1aa] light:text-[#71717a] mt-1">True Positive Rate</div>
        </div>

        {/* Daemon Status */}
        <div className={statCardClass()}>
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm dark:text-[#a1a1aa] light:text-[#71717a]">Daemon Status</span>
            <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${daemonBadgeColor}`}>
              {daemon ? daemonBadgeLabel : 'Checking'}
            </span>
          </div>
          <div className="text-3xl font-bold">{daemon ? daemonStatusLabel : '—'}</div>
          <div className="text-xs dark:text-[#a1a1aa] light:text-[#71717a] mt-1">
            {daemon ? daemonDetail : 'Fetching...'}
          </div>
        </div>
      </div>

      {/* ── Quick Actions ──────────────────────────── */}
      <div className={statCardClass()}>
        <h3 className="font-semibold mb-4">Quick Actions</h3>
        <div className="flex flex-wrap gap-3">
          <button
            onClick={() => setModal({ open: true, loading: false, error: '' })}
            className="bg-vyper-500 text-white px-4 py-2 rounded-lg font-medium hover:bg-vyper-600 hover:-translate-y-0.5 transition-all disabled:opacity-50 disabled:cursor-not-allowed disabled:transform-none flex items-center gap-2"
          >
            <svg className="w-4 h-4" viewBox="0 0 20 20" fill="currentColor">
              <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm1-11a1 1 0 10-2 0v2H7a1 1 0 100 2h2v2a1 1 0 102 0v-2h2a1 1 0 100-2h-2V7z" clipRule="evenodd" />
            </svg>
            Start Audit
          </button>

          <button
            onClick={handleToggleDaemon}
            disabled={daemonToggling}
            className="bg-transparent border dark:border-[#27272a] dark:text-[#a1a1aa] light:border-[#e4e4e7] light:text-[#71717a] px-4 py-2 rounded-lg font-medium hover:border-vyper-500 hover:text-vyper-500 transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
          >
            <svg className="w-4 h-4" viewBox="0 0 20 20" fill="currentColor">
              <path fillRule="evenodd" d="M11.3 1.046A1 1 0 0112 2v5h4a1 1 0 01.82 1.573l-7 10A1 1 0 018 18v-5H4a1 1 0 01-.82-1.573l7-10a1 1 0 011.12-.38z" clipRule="evenodd" />
            </svg>
            <span>{daemonToggling ? 'Toggling...' : 'Toggle Daemon'}</span>
          </button>

          <button
            onClick={handleRunSync}
            disabled={syncing}
            className="bg-transparent border dark:border-[#27272a] dark:text-[#a1a1aa] light:border-[#e4e4e7] light:text-[#71717a] px-4 py-2 rounded-lg font-medium hover:border-vyper-500 hover:text-vyper-500 transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
          >
            <svg className="w-4 h-4" viewBox="0 0 20 20" fill="currentColor">
              <path fillRule="evenodd" d="M4 2a1 1 0 011 1v2.101a7.002 7.002 0 0111.601 2.566 1 1 0 11-1.885.666A5.002 5.002 0 005.999 7H9a1 1 0 010 2H4a1 1 0 01-1-1V3a1 1 0 011-1zm.008 9.057a1 1 0 011.276.61A5.002 5.002 0 0014.001 13H11a1 1 0 110-2h5a1 1 0 011 1v5a1 1 0 11-2 0v-2.101a7.002 7.002 0 01-11.601-2.566 1 1 0 01.61-1.276z" clipRule="evenodd" />
            </svg>
            {syncing ? 'Syncing...' : 'Run Sync'}
          </button>
        </div>
      </div>

      {/* ── Recent Audits ──────────────────────────── */}
      <div className={statCardClass()}>
        <div className="flex items-center justify-between mb-4">
          <h3 className="font-semibold">Recent Audits</h3>
          <a href="/audits" className="text-sm text-vyper-400 hover:text-vyper-300 transition-colors">
            View all →
          </a>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider dark:bg-[#18181b] dark:text-[#a1a1aa] dark:border-b dark:border-[#27272a] light:bg-[#f4f4f5] light:text-[#71717a] light:border-b light:border-[#e4e4e7]">
                  Audit ID
                </th>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider dark:bg-[#18181b] dark:text-[#a1a1aa] dark:border-b dark:border-[#27272a] light:bg-[#f4f4f5] light:text-[#71717a] light:border-b light:border-[#e4e4e7]">
                  Program
                </th>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider dark:bg-[#18181b] dark:text-[#a1a1aa] dark:border-b dark:border-[#27272a] light:bg-[#f4f4f5] light:text-[#71717a] light:border-b light:border-[#e4e4e7]">
                  Chain
                </th>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider dark:bg-[#18181b] dark:text-[#a1a1aa] dark:border-b dark:border-[#27272a] light:bg-[#f4f4f5] light:text-[#71717a] light:border-b light:border-[#e4e4e7]">
                  Status
                </th>
                <th className="px-4 py-3 text-right text-xs font-semibold uppercase tracking-wider dark:bg-[#18181b] dark:text-[#a1a1aa] dark:border-b dark:border-[#27272a] light:bg-[#f4f4f5] light:text-[#71717a] light:border-b light:border-[#e4e4e7]">
                  Findings
                </th>
                <th className="px-4 py-3 text-right text-xs font-semibold uppercase tracking-wider dark:bg-[#18181b] dark:text-[#a1a1aa] dark:border-b dark:border-[#27272a] light:bg-[#f4f4f5] light:text-[#71717a] light:border-b light:border-[#e4e4e7]">
                  Duration
                </th>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider dark:bg-[#18181b] dark:text-[#a1a1aa] dark:border-b dark:border-[#27272a] light:bg-[#f4f4f5] light:text-[#71717a] light:border-b light:border-[#e4e4e7]">
                  Date
                </th>
              </tr>
            </thead>
            <tbody>
              {auditsLoading ? (
                <tr className="dark:border-b dark:border-[#27272a] light:border-b light:border-[#e4e4e7]">
                  <td colSpan={7} className="px-4 py-8 text-center text-sm dark:text-[#a1a1aa] light:text-[#71717a]">
                    Loading audits...
                  </td>
                </tr>
              ) : audits.length === 0 ? (
                <tr className="dark:border-b dark:border-[#27272a] light:border-b light:border-[#e4e4e7]">
                  <td colSpan={7} className="px-4 py-8 text-center text-sm dark:text-[#a1a1aa] light:text-[#71717a]">
                    No audits yet. Start your first audit!
                  </td>
                </tr>
              ) : (
                audits.map((a) => (
                  <tr
                    key={a.audit_id}
                    onClick={() => window.location.href = `/audits/${a.audit_id}`}
                    className="dark:border-b dark:border-[#27272a] light:border-b light:border-[#e4e4e7] hover:dark:bg-vyper-500/5 hover:light:bg-vyper-500/3 transition-colors cursor-pointer"
                  >
                    <td className="px-4 py-3 text-sm font-mono text-xs dark:text-[#f4f4f5] light:text-[#09090b]">
                      {shortId(a.audit_id)}
                    </td>
                    <td className="px-4 py-3 text-sm dark:text-[#f4f4f5] light:text-[#09090b]">
                      {a.program || '—'}
                    </td>
                    <td className="px-4 py-3 text-sm dark:text-[#f4f4f5] light:text-[#09090b]">
                      {a.chain || '—'}
                    </td>
                    <td className="px-4 py-3 text-sm">
                      {statusBadge(a.state || 'PENDING')}
                    </td>
                    <td className="px-4 py-3 text-sm text-right dark:text-[#f4f4f5] light:text-[#09090b]">
                      {a.findings_count ?? '—'}
                    </td>
                    <td className="px-4 py-3 text-sm text-right font-mono text-xs dark:text-[#f4f4f5] light:text-[#09090b]">
                      {durationStr(a.duration_seconds)}
                    </td>
                    <td className="px-4 py-3 text-xs dark:text-[#f4f4f5] light:text-[#09090b]">
                      {a.created_at ? new Date(a.created_at).toLocaleDateString() : '—'}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* ── Start Audit Modal ──────────────────────── */}
      {modal.open && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/50"
          onClick={(e) => { if (e.target === e.currentTarget) setModal({ open: false }); }}
        >
          <div
            className="rounded-xl p-6 w-full max-w-md mx-4 dark:bg-[#1a1a1e] dark:border dark:border-[#27272a] light:bg-white light:border light:border-[#e4e4e7]"
            onClick={(e) => e.stopPropagation()}
          >
            <h3 className="font-semibold text-lg mb-4">Start New Audit</h3>

            <form onSubmit={handleStartAudit}>
              <div className="space-y-4">
                {/* Chain */}
                <div>
                  <label className="block text-sm font-medium mb-1 dark:text-[#f4f4f5] light:text-[#09090b]">
                    Chain
                  </label>
                  <select name="chain" className={inputFieldClass()} required>
                    {CHAINS.map((c) => (
                      <option key={c.value} value={c.value}>
                        {c.label}
                      </option>
                    ))}
                  </select>
                </div>

                {/* Contract Address */}
                <div>
                  <label className="block text-sm font-medium mb-1 dark:text-[#f4f4f5] light:text-[#09090b]">
                    Contract Address
                  </label>
                  <input
                    type="text"
                    name="address"
                    className={`${inputFieldClass()} font-mono text-xs`}
                    placeholder="0x..."
                    required
                  />
                </div>

                {/* Program */}
                <div>
                  <label className="block text-sm font-medium mb-1 dark:text-[#f4f4f5] light:text-[#09090b]">
                    Program (optional)
                  </label>
                  <input
                    type="text"
                    name="program"
                    className={inputFieldClass()}
                    placeholder="Immunefi program slug"
                  />
                </div>

                {/* Priority */}
                <div>
                  <label className="block text-sm font-medium mb-1 dark:text-[#f4f4f5] light:text-[#09090b]">
                    Priority (0-10)
                  </label>
                  <input
                    type="number"
                    name="priority"
                    className={inputFieldClass()}
                    defaultValue={5}
                    min={0}
                    max={10}
                  />
                </div>
              </div>

              {/* Error message */}
              {modal.open && 'error' in modal && modal.error && (
                <div className="mt-3 text-sm text-red-400">
                  {modal.error}
                </div>
              )}

              {/* Actions */}
              <div className="flex justify-end gap-3 mt-6">
                <button
                  type="button"
                  onClick={() => setModal({ open: false })}
                  disabled={'loading' in modal && modal.loading}
                  className="bg-transparent border dark:border-[#27272a] dark:text-[#a1a1aa] light:border-[#e4e4e7] light:text-[#71717a] px-4 py-2 rounded-lg font-medium hover:border-vyper-500 hover:text-vyper-500 transition-all disabled:opacity-50"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={'loading' in modal && modal.loading}
                  className="bg-vyper-500 text-white px-4 py-2 rounded-lg font-medium hover:bg-vyper-600 transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
                >
                  {'loading' in modal && modal.loading ? (
                    <>
                      <svg className="w-4 h-4 animate-spin" viewBox="0 0 24 24" fill="none">
                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                      </svg>
                      Starting...
                    </>
                  ) : (
                    'Start Audit'
                  )}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
