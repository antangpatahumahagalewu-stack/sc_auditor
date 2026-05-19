import { useEffect, useState } from 'react';
import { api } from '../lib/api';

const PIPELINE_STAGES = [
  'PENDING', 'FETCHING_PROGRAM', 'FETCHING_SOURCE', 'SCANNING',
  'AI_ANALYSIS', 'CLASSIFYING', 'EXPLOITING', 'REPORTING', 'NOTIFYING', 'COMPLETED',
];

function statCardClass(): string {
  return 'rounded-xl p-6 dark:bg-[#1a1a1e] dark:border dark:border-[#27272a] light:bg-white light:border light:border-[#e4e4e7] transition-all duration-200';
}

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

export default function Pipeline() {
  const [pipeline, setPipeline] = useState<any>(null);
  const [steps, setSteps] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        const [pipeRes, stepsRes] = await Promise.all([
          api.getPipelineStatus(),
          api.getPipelineSteps(),
        ]);
        if (cancelled) return;
        setPipeline(pipeRes.data || null);
        setSteps(stepsRes.data || []);
      } catch (err: any) {
        if (!cancelled) setError(err?.message || 'Failed to fetch pipeline data');
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    load();
    const interval = setInterval(load, 10000);
    return () => { cancelled = true; clearInterval(interval); };
  }, []);

  const currentState = pipeline?.state || 'PENDING';
  const currentIdx = PIPELINE_STAGES.indexOf(currentState);

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold">Pipeline</h2>
        <p className="dark:text-[#a1a1aa] light:text-[#71717a] mt-1">
          Audit pipeline state machine — {pipeline?.total_audits ?? 0} total audits
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
          <div className="text-center py-8 text-sm dark:text-[#a1a1aa] light:text-[#71717a]">Loading pipeline...</div>
        </div>
      ) : (
        <>
          {/* Pipeline Stages */}
          <div className={statCardClass()}>
            <h3 className="font-semibold mb-4">Pipeline Stages</h3>
            <div className="flex flex-wrap items-center gap-2">
              {PIPELINE_STAGES.map((stage, i) => {
                const isActive = i === currentIdx;
                const isPast = i < currentIdx;
                const isFuture = i > currentIdx;
                const stageColor = isPast
                  ? 'bg-green-500/20 text-green-400 border-green-500/30'
                  : isActive
                    ? 'bg-vyper-500/20 text-vyper-400 border-vyper-500/30 animate-pulse'
                    : 'dark:bg-[#18181b] dark:text-[#52525b] dark:border-[#27272a] light:bg-[#f4f4f5] light:text-[#a1a1aa] light:border-[#e4e4e7]';
                return (
                  <div key={stage} className="flex items-center gap-2">
                    <span className={`px-3 py-1.5 rounded-lg text-xs font-semibold border transition-all ${stageColor}`}>
                      {stage}
                    </span>
                    {i < PIPELINE_STAGES.length - 1 && (
                      <svg className={`w-4 h-4 ${isPast ? 'text-green-400' : isActive ? 'text-vyper-400' : 'dark:text-[#52525b] light:text-[#a1a1aa]'}`} viewBox="0 0 20 20" fill="currentColor">
                        <path fillRule="evenodd" d="M7.293 14.707a1 1 0 010-1.414L10.586 10 7.293 6.707a1 1 0 011.414-1.414l4 4a1 1 0 010 1.414l-4 4a1 1 0 01-1.414 0z" clipRule="evenodd" />
                      </svg>
                    )}
                  </div>
                );
              })}
            </div>
          </div>

          {/* Pipeline Stats */}
          {pipeline && (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
              <div className={statCardClass()}>
                <div className="text-sm dark:text-[#a1a1aa] light:text-[#71717a] mb-1">Total Audits</div>
                <div className="text-3xl font-bold">{pipeline.total_audits ?? '—'}</div>
              </div>
              <div className={statCardClass()}>
                <div className="text-sm dark:text-[#a1a1aa] light:text-[#71717a] mb-1">Completed</div>
                <div className="text-3xl font-bold text-green-400">{pipeline.completed ?? '—'}</div>
              </div>
              <div className={statCardClass()}>
                <div className="text-sm dark:text-[#a1a1aa] light:text-[#71717a] mb-1">Failed</div>
                <div className="text-3xl font-bold text-red-400">{pipeline.failed ?? '—'}</div>
              </div>
              <div className={statCardClass()}>
                <div className="text-sm dark:text-[#a1a1aa] light:text-[#71717a] mb-1">In Progress</div>
                <div className="text-3xl font-bold text-blue-400">{pipeline.in_progress ?? '—'}</div>
              </div>
            </div>
          )}

          {/* Recent Steps */}
          <div className={statCardClass()}>
            <h3 className="font-semibold mb-4">Recent Pipeline Steps</h3>
            {steps.length === 0 ? (
              <div className="text-center py-6 text-sm dark:text-[#a1a1aa] light:text-[#71717a]">No pipeline steps recorded yet.</div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead>
                    <tr>
                      <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider dark:bg-[#18181b] dark:text-[#a1a1aa] dark:border-b dark:border-[#27272a] light:bg-[#f4f4f5] light:text-[#71717a] light:border-b light:border-[#e4e4e7]">Audit ID</th>
                      <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider dark:bg-[#18181b] dark:text-[#a1a1aa] dark:border-b dark:border-[#27272a] light:bg-[#f4f4f5] light:text-[#71717a] light:border-b light:border-[#e4e4e7]">Stage</th>
                      <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider dark:bg-[#18181b] dark:text-[#a1a1aa] dark:border-b dark:border-[#27272a] light:bg-[#f4f4f5] light:text-[#71717a] light:border-b light:border-[#e4e4e7]">Status</th>
                      <th className="px-4 py-3 text-right text-xs font-semibold uppercase tracking-wider dark:bg-[#18181b] dark:text-[#a1a1aa] dark:border-b dark:border-[#27272a] light:bg-[#f4f4f5] light:text-[#71717a] light:border-b light:border-[#e4e4e7]">Duration</th>
                      <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider dark:bg-[#18181b] dark:text-[#a1a1aa] dark:border-b dark:border-[#27272a] light:bg-[#f4f4f5] light:text-[#71717a] light:border-b light:border-[#e4e4e7]">Timestamp</th>
                    </tr>
                  </thead>
                  <tbody>
                    {steps.map((s: any, i: number) => (
                      <tr key={s.id || i} className="dark:border-b dark:border-[#27272a] light:border-b light:border-[#e4e4e7] hover:dark:bg-vyper-500/5 hover:light:bg-vyper-500/3 transition-colors">
                        <td className="px-4 py-3 text-sm font-mono text-xs dark:text-[#f4f4f5] light:text-[#09090b]">{s.audit_id || '—'}</td>
                        <td className="px-4 py-3 text-sm dark:text-[#f4f4f5] light:text-[#09090b]">{s.stage || '—'}</td>
                        <td className="px-4 py-3 text-sm">{statusBadge(s.status || 'PENDING')}</td>
                        <td className="px-4 py-3 text-sm text-right font-mono text-xs dark:text-[#f4f4f5] light:text-[#09090b]">{s.duration_seconds != null ? `${s.duration_seconds}s` : '—'}</td>
                        <td className="px-4 py-3 text-xs dark:text-[#a1a1aa] light:text-[#71717a]">{s.timestamp ? new Date(s.timestamp).toLocaleString() : '—'}</td>
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
