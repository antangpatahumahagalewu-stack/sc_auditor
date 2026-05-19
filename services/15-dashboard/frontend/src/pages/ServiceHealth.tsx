import { useEffect, useState } from 'react';
import { api } from '../lib/api';

function statCardClass(): string {
  return 'rounded-xl p-6 dark:bg-[#1a1a1e] dark:border dark:border-[#27272a] light:bg-white light:border light:border-[#e4e4e7] transition-all duration-200';
}

export default function ServiceHealth() {
  const [services, setServices] = useState<Record<string, { status: string; code?: number; error?: string }> | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        const res = await api.getHealthAll();
        if (!cancelled) setServices(res.data || null);
      } catch (err: any) {
        if (!cancelled) setError(err?.message || 'Failed to fetch service health');
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    load();
    const interval = setInterval(load, 30000);
    return () => { cancelled = true; clearInterval(interval); };
  }, []);

  const statusColor = (status: string) => {
    switch (status) {
      case 'healthy': return 'bg-green-500/20 text-green-400 border-green-500/30';
      case 'unhealthy': return 'bg-red-500/20 text-red-400 border-red-500/30';
      default: return 'bg-gray-500/20 text-gray-400 border-gray-500/30';
    }
  };

  const statusDot = (status: string) => {
    switch (status) {
      case 'healthy': return 'bg-green-500 shadow-[0_0_6px_rgba(34,197,94,0.5)]';
      case 'unhealthy': return 'bg-red-500 shadow-[0_0_6px_rgba(239,68,68,0.5)]';
      default: return 'bg-gray-500 shadow-[0_0_6px_rgba(161,161,170,0.5)]';
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold">Service Health</h2>
        <p className="dark:text-[#a1a1aa] light:text-[#71717a] mt-1">
          Real-time health status for all Vyper microservices
        </p>
      </div>

      {error && (
        <div className="rounded-xl p-4 bg-red-500/10 border border-red-500/20 text-red-400 text-sm flex items-center gap-2">
          <svg className="w-4 h-4 flex-shrink-0" viewBox="0 0 20 20" fill="currentColor">
            <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
          </svg>
          <span>{error}</span>
        </div>
      )}

      {loading ? (
        <div className={statCardClass()}>
          <div className="text-center py-8 text-sm dark:text-[#a1a1aa] light:text-[#71717a]">
            Loading service health...
          </div>
        </div>
      ) : !services || Object.keys(services).length === 0 ? (
        <div className={statCardClass()}>
          <div className="text-center py-8 text-sm dark:text-[#a1a1aa] light:text-[#71717a]">
            No services found.
          </div>
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {Object.entries(services).map(([name, svc]) => (
            <div key={name} className={`${statCardClass()} hover:dark:border-vyper-500 hover:light:border-vyper-500 transition-all`}>
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-2">
                  <span className={`w-2.5 h-2.5 rounded-full ${statusDot(svc.status)}`} />
                  <span className="font-semibold text-sm">{name}</span>
                </div>
                <span className={`text-xs px-2 py-0.5 rounded-full border font-medium ${statusColor(svc.status)}`}>
                  {svc.status}
                </span>
              </div>
              {svc.code != null && (
                <div className="text-xs dark:text-[#a1a1aa] light:text-[#71717a]">
                  HTTP {svc.code}
                </div>
              )}
              {svc.error && (
                <div className="text-xs text-red-400 mt-1 truncate" title={svc.error}>
                  {svc.error}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
