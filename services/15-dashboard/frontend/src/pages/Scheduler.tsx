import { useEffect, useState } from 'react';
import { api } from '../lib/api';

function statCardClass(): string {
  return 'rounded-xl p-6 dark:bg-[#1a1a1e] dark:border dark:border-[#27272a] light:bg-white light:border light:border-[#e4e4e7] transition-all duration-200';
}

export default function Scheduler() {
  const [status, setStatus] = useState<any>(null);
  const [logs, setLogs] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        const [statRes, logRes] = await Promise.all([
          api.getUpkeepStatus(),
          api.getUpkeepLogs(50),
        ]);
        if (cancelled) return;
        setStatus(statRes.data || null);
        setLogs(logRes.data || []);
      } catch (err: any) {
        if (!cancelled) setError(err?.message || 'Failed to fetch scheduler data');
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    load();
    const interval = setInterval(load, 10000);
    return () => { cancelled = true; clearInterval(interval); };
  }, []);

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold">Scheduler</h2>
        <p className="dark:text-[#a1a1aa] light:text-[#71717a] mt-1">
          Upkeep scheduler status and logs — auto-refreshes every 10 seconds
        </p>
      </div>

      {error && (
        <div className="rounded-xl p-4 bg-red-500/10 border border-red-500/20 text-red-400 text-sm flex items-center gap-2">
          <svg className="w-4 h-4 flex-shrink-0" viewBox="0 0 20 20" fill="currentColor">
            <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
          </svg>
          <span>{error}</span>
          <button onClick={() => setError('')} className="ml-auto text-red-400/70 hover:text-red-400">✕</button>
        </div>
      )}

      {loading ? (
        <div className={statCardClass()}>
          <div className="text-center py-8 text-sm dark:text-[#a1a1aa] light:text-[#71717a]">Loading scheduler data...</div>
        </div>
      ) : (
        <>
          {/* Status Cards */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <div className={statCardClass()}>
              <div className="text-sm dark:text-[#a1a1aa] light:text-[#71717a] mb-1">Status</div>
              <div className="text-3xl font-bold flex items-center gap-2">
                <span className={`w-3 h-3 rounded-full ${status?.status === 'running' ? 'bg-green-500 shadow-[0_0_6px_rgba(34,197,94,0.5)]' : status?.status === 'idle' ? 'bg-yellow-500 shadow-[0_0_6px_rgba(245,158,11,0.5)]' : 'bg-red-500 shadow-[0_0_6px_rgba(239,68,68,0.5)]'}`} />
                <span>{status?.status === 'running' ? 'Running' : status?.status === 'idle' ? 'Idle' : 'Stopped'}</span>
              </div>
            </div>
            <div className={statCardClass()}>
              <div className="text-sm dark:text-[#a1a1aa] light:text-[#71717a] mb-1">Last Run</div>
              <div className="text-lg font-bold dark:text-[#f4f4f5] light:text-[#09090b]">
                {status?.last_run_at ? new Date(status.last_run_at).toLocaleString() : '—'}
              </div>
            </div>
            <div className={statCardClass()}>
              <div className="text-sm dark:text-[#a1a1aa] light:text-[#71717a] mb-1">Next Run</div>
              <div className="text-lg font-bold dark:text-[#f4f4f5] light:text-[#09090b]">
                {status?.next_run_at ? new Date(status.next_run_at).toLocaleString() : '—'}
              </div>
            </div>
            <div className={statCardClass()}>
              <div className="text-sm dark:text-[#a1a1aa] light:text-[#71717a] mb-1">Total Cycles</div>
              <div className="text-3xl font-bold">{status?.total_cycles_completed ?? '—'}</div>
            </div>
          </div>

          {/* Logs */}
          <div className={statCardClass()}>
            <h3 className="font-semibold mb-4">Upkeep Logs</h3>
            {logs.length === 0 ? (
              <div className="text-center py-6 text-sm dark:text-[#a1a1aa] light:text-[#71717a]">No upkeep logs yet.</div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead>
                    <tr>
                      <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider dark:bg-[#18181b] dark:text-[#a1a1aa] dark:border-b dark:border-[#27272a] light:bg-[#f4f4f5] light:text-[#71717a] light:border-b light:border-[#e4e4e7]">Timestamp</th>
                      <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider dark:bg-[#18181b] dark:text-[#a1a1aa] dark:border-b dark:border-[#27272a] light:bg-[#f4f4f5] light:text-[#71717a] light:border-b light:border-[#e4e4e7]">Action</th>
                      <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider dark:bg-[#18181b] dark:text-[#a1a1aa] dark:border-b dark:border-[#27272a] light:bg-[#f4f4f5] light:text-[#71717a] light:border-b light:border-[#e4e4e7]">Status</th>
                      <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider dark:bg-[#18181b] dark:text-[#a1a1aa] dark:border-b dark:border-[#27272a] light:bg-[#f4f4f5] light:text-[#71717a] light:border-b light:border-[#e4e4e7]">Detail</th>
                    </tr>
                  </thead>
                  <tbody>
                    {logs.map((log: any, i: number) => (
                      <tr key={log.id || i} className="dark:border-b dark:border-[#27272a] light:border-b light:border-[#e4e4e7] hover:dark:bg-vyper-500/5 hover:light:bg-vyper-500/3 transition-colors">
                        <td className="px-4 py-3 text-xs dark:text-[#a1a1aa] light:text-[#71717a]">{log.timestamp ? new Date(log.timestamp).toLocaleString() : '—'}</td>
                        <td className="px-4 py-3 text-sm dark:text-[#f4f4f5] light:text-[#09090b]">{log.action || '—'}</td>
                        <td className="px-4 py-3 text-sm">
                          <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${
                            log.status === 'completed' || log.status === 'success' ? 'bg-green-500/20 text-green-400' :
                            log.status === 'failed' || log.status === 'error' ? 'bg-red-500/20 text-red-400' :
                            log.status === 'running' ? 'bg-blue-500/20 text-blue-400' : 'bg-yellow-500/20 text-yellow-400'
                          }`}>{log.status || 'unknown'}</span>
                        </td>
                        <td className="px-4 py-3 text-xs dark:text-[#a1a1aa] light:text-[#71717a] max-w-md truncate">{log.detail || log.message || '—'}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </>
      )}
    </div>
  );
}
