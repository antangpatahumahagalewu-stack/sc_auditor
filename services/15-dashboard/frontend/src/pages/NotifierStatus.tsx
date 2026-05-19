import { useEffect, useState } from 'react';
import { api } from '../lib/api';

function statCardClass(): string {
  return 'rounded-xl p-6 dark:bg-[#1a1a1e] dark:border dark:border-[#27272a] light:bg-white light:border light:border-[#e4e4e7] transition-all duration-200';
}

export default function NotifierStatus() {
  const [channels, setChannels] = useState<any>(null);
  const [logs, setLogs] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [testing, setTesting] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        const [chRes, logRes] = await Promise.all([
          api.getNotifierChannels(),
          api.getNotifierLogs(50),
        ]);
        if (cancelled) return;
        setChannels(chRes.data || null);
        setLogs(logRes.data || []);
      } catch (err: any) {
        if (!cancelled) setError(err?.message || 'Failed to fetch notifier data');
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    load();
    return () => { cancelled = true; };
  }, []);

  async function handleTest(channel: string) {
    setTesting(channel);
    try {
      await api.testNotification(channel);
      // Refresh logs
      const logRes = await api.getNotifierLogs(50);
      setLogs(logRes.data || []);
    } catch (err: any) {
      setError(err?.message || `Failed to test ${channel}`);
    } finally {
      setTesting(null);
    }
  }

  const channelIcons: Record<string, string> = {
    discord: 'M15.73 3.504a37.824 37.824 0 00-11.46 0 4.42 4.42 0 00-3.947 3.336 36.758 36.758 0 000 10.32 4.42 4.42 0 003.947 3.336 37.815 37.815 0 0011.46 0 4.42 4.42 0 003.947-3.336 36.758 36.758 0 000-10.32 4.42 4.42 0 00-3.947-3.336zM9.5 12.5V7.5l5 2.5-5 2.5z',
    telegram: 'M3.478 2.404a.75.75 0 00-.926.94l2.432 7.905H13.5a.75.75 0 010 1.5H4.984l-2.432 7.905a.75.75 0 00.926.94 60.519 60.519 0 0018.445-8.986.75.75 0 000-1.218A60.517 60.517 0 003.478 2.404z',
    email: 'M2.003 5.884L10 9.882l7.997-3.998A2 2 0 0016 4H4a2 2 0 00-1.997 1.884zM18 8.118l-8 4-8-4V14a2 2 0 002 2h12a2 2 0 002-2V8.118z',
    desktop: 'M3 5a2 2 0 012-2h10a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2V5zm0 8a1 1 0 011 1v1h2v-1a1 1 0 011-1h6a1 1 0 011 1v1h2v-1a1 1 0 011-1h1a2 2 0 002-2v-1H2v1a2 2 0 002 2h1z',
  };

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold">Notifier Status</h2>
        <p className="dark:text-[#a1a1aa] light:text-[#71717a] mt-1">
          Notification channels and delivery logs
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
          <div className="text-center py-8 text-sm dark:text-[#a1a1aa] light:text-[#71717a]">Loading notifier data...</div>
        </div>
      ) : (
        <>
          {/* Channels */}
          <div className={statCardClass()}>
            <h3 className="font-semibold mb-4">Channels</h3>
            {!channels || Object.keys(channels).length === 0 ? (
              <div className="text-center py-4 text-sm dark:text-[#a1a1aa] light:text-[#71717a]">No channels configured.</div>
            ) : (
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                {Object.entries(channels).map(([name, info]: [string, any]) => (
                  <div key={name} className="flex items-center gap-3 p-4 rounded-lg dark:bg-[#18181b] light:bg-[#f4f4f5] dark:border dark:border-[#27272a] light:border light:border-[#e4e4e7]">
                    <svg className="w-6 h-6 dark:text-[#a1a1aa] light:text-[#71717a]" viewBox="0 0 20 20" fill="currentColor">
                      <path d={channelIcons[name] || channelIcons.email} />
                    </svg>
                    <div className="flex-1">
                      <div className="font-medium text-sm capitalize">{name}</div>
                      <div className="text-xs dark:text-[#a1a1aa] light:text-[#71717a]">
                        {typeof info === 'object' ? (info.enabled ? 'Enabled' : 'Disabled') : String(info)}
                      </div>
                    </div>
                    <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${
                      typeof info === 'object' && info.enabled
                        ? 'bg-green-500/20 text-green-400'
                        : 'bg-gray-500/20 text-gray-400'
                    }`}>
                      {typeof info === 'object' && info.enabled ? 'Active' : 'Inactive'}
                    </span>
                    <button
                      onClick={() => handleTest(name)}
                      disabled={testing === name}
                      className="text-xs px-3 py-1.5 rounded-lg bg-vyper-500 text-white hover:bg-vyper-600 transition-all disabled:opacity-50 font-medium"
                    >
                      {testing === name ? 'Sending...' : 'Test'}
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Delivery Logs */}
          <div className={statCardClass()}>
            <h3 className="font-semibold mb-4">Delivery Logs (Last 50)</h3>
            {logs.length === 0 ? (
              <div className="text-center py-6 text-sm dark:text-[#a1a1aa] light:text-[#71717a]">No delivery logs yet.</div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead>
                    <tr>
                      <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider dark:bg-[#18181b] dark:text-[#a1a1aa] dark:border-b dark:border-[#27272a] light:bg-[#f4f4f5] light:text-[#71717a] light:border-b light:border-[#e4e4e7]">Timestamp</th>
                      <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider dark:bg-[#18181b] dark:text-[#a1a1aa] dark:border-b dark:border-[#27272a] light:bg-[#f4f4f5] light:text-[#71717a] light:border-b light:border-[#e4e4e7]">Channel</th>
                      <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider dark:bg-[#18181b] dark:text-[#a1a1aa] dark:border-b dark:border-[#27272a] light:bg-[#f4f4f5] light:text-[#71717a] light:border-b light:border-[#e4e4e7]">Status</th>
                      <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider dark:bg-[#18181b] dark:text-[#a1a1aa] dark:border-b dark:border-[#27272a] light:bg-[#f4f4f5] light:text-[#71717a] light:border-b light:border-[#e4e4e7]">Message</th>
                    </tr>
                  </thead>
                  <tbody>
                    {logs.map((log: any, i: number) => (
                      <tr key={log.id || i} className="dark:border-b dark:border-[#27272a] light:border-b light:border-[#e4e4e7] hover:dark:bg-vyper-500/5 hover:light:bg-vyper-500/3 transition-colors">
                        <td className="px-4 py-3 text-xs dark:text-[#a1a1aa] light:text-[#71717a]">{log.timestamp ? new Date(log.timestamp).toLocaleString() : '—'}</td>
                        <td className="px-4 py-3 text-sm capitalize dark:text-[#f4f4f5] light:text-[#09090b]">{log.channel || '—'}</td>
                        <td className="px-4 py-3 text-sm">
                          <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${
                            log.status === 'sent' || log.status === 'delivered' ? 'bg-green-500/20 text-green-400' :
                            log.status === 'failed' ? 'bg-red-500/20 text-red-400' : 'bg-yellow-500/20 text-yellow-400'
                          }`}>{log.status || 'unknown'}</span>
                        </td>
                        <td className="px-4 py-3 text-xs dark:text-[#a1a1aa] light:text-[#71717a] max-w-xs truncate">{log.message || '—'}</td>
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
