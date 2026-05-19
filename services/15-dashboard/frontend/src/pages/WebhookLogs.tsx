import { useEffect, useState } from 'react';
import { api } from '../lib/api';

function statCardClass(): string {
  return 'rounded-xl p-6 dark:bg-[#1a1a1e] dark:border dark:border-[#27272a] light:bg-white light:border light:border-[#e4e4e7] transition-all duration-200';
}

export default function WebhookLogs() {
  const [logs, setLogs] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [expandedRow, setExpandedRow] = useState<number | null>(null);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        const res = await api.getWebhookLogs(50);
        if (!cancelled) setLogs(res.data || []);
      } catch (err: any) {
        if (!cancelled) setError(err?.message || 'Failed to fetch webhook logs');
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    load();
    const interval = setInterval(load, 15000);
    return () => { cancelled = true; clearInterval(interval); };
  }, []);

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold">Webhook Logs</h2>
        <p className="dark:text-[#a1a1aa] light:text-[#71717a] mt-1">
          Incoming webhook events — auto-refreshes every 15 seconds
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

      <div className={statCardClass()}>
        <h3 className="font-semibold mb-4">Webhook Events</h3>
        {loading ? (
          <div className="text-center py-8 text-sm dark:text-[#a1a1aa] light:text-[#71717a]">Loading webhook logs...</div>
        ) : logs.length === 0 ? (
          <div className="text-center py-8 text-sm dark:text-[#a1a1aa] light:text-[#71717a]">No webhook events received yet.</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider dark:bg-[#18181b] dark:text-[#a1a1aa] dark:border-b dark:border-[#27272a] light:bg-[#f4f4f5] light:text-[#71717a] light:border-b light:border-[#e4e4e7]">Timestamp</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider dark:bg-[#18181b] dark:text-[#a1a1aa] dark:border-b dark:border-[#27272a] light:bg-[#f4f4f5] light:text-[#71717a] light:border-b light:border-[#e4e4e7]">Event Type</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider dark:bg-[#18181b] dark:text-[#a1a1aa] dark:border-b dark:border-[#27272a] light:bg-[#f4f4f5] light:text-[#71717a] light:border-b light:border-[#e4e4e7]">Status</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider dark:bg-[#18181b] dark:text-[#a1a1aa] dark:border-b dark:border-[#27272a] light:bg-[#f4f4f5] light:text-[#71717a] light:border-b light:border-[#e4e4e7]">Payload Preview</th>
                </tr>
              </thead>
              <tbody>
                {logs.map((log: any, i: number) => (
                  <tr key={log.id || i}>
                    <td colSpan={4} className="p-0">
                      <div
                        className={`dark:border-b dark:border-[#27272a] light:border-b light:border-[#e4e4e7] hover:dark:bg-vyper-500/5 hover:light:bg-vyper-500/3 transition-colors cursor-pointer ${expandedRow === i ? 'dark:bg-vyper-500/10 light:bg-vyper-500/5' : ''}`}
                        onClick={() => setExpandedRow(expandedRow === i ? null : i)}
                      >
                        <div className="flex items-center px-4 py-3">
                          <div className="flex-1 grid grid-cols-4 gap-4 text-sm items-center">
                            <span className="text-xs dark:text-[#a1a1aa] light:text-[#71717a]">{log.timestamp ? new Date(log.timestamp).toLocaleString() : '—'}</span>
                            <span className="dark:text-[#f4f4f5] light:text-[#09090b]">{log.event_type || log.event || '—'}</span>
                            <span>
                              <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${
                                log.status === 'received' || log.status === 'processed' ? 'bg-green-500/20 text-green-400' :
                                log.status === 'failed' ? 'bg-red-500/20 text-red-400' : 'bg-yellow-500/20 text-yellow-400'
                              }`}>{log.status || 'unknown'}</span>
                            </span>
                            <span className="text-xs dark:text-[#a1a1aa] light:text-[#71717a] font-mono truncate">
                              {log.payload ? JSON.stringify(log.payload).slice(0, 60) + (JSON.stringify(log.payload).length > 60 ? '...' : '') : '—'}
                            </span>
                          </div>
                          <svg className={`w-4 h-4 dark:text-[#a1a1aa] light:text-[#71717a] transition-transform ${expandedRow === i ? 'rotate-90' : ''}`} viewBox="0 0 20 20" fill="currentColor">
                            <path fillRule="evenodd" d="M7.293 14.707a1 1 0 010-1.414L10.586 10 7.293 6.707a1 1 0 011.414-1.414l4 4a1 1 0 010 1.414l-4 4a1 1 0 01-1.414 0z" clipRule="evenodd" />
                          </svg>
                        </div>
                        {expandedRow === i && log.payload && (
                          <div className="px-4 pb-3">
                            <pre className="p-3 rounded-lg dark:bg-[#18181b] light:bg-[#f4f4f5] dark:border dark:border-[#27272a] light:border light:border-[#e4e4e7] overflow-x-auto text-xs font-mono max-h-60">
                              {JSON.stringify(log.payload, null, 2)}
                            </pre>
                          </div>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
