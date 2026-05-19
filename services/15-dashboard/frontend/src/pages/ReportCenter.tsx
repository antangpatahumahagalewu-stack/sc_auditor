import { useEffect, useState } from 'react';
import { api } from '../lib/api';

function statCardClass(): string {
  return 'rounded-xl p-6 dark:bg-[#1a1a1e] dark:border dark:border-[#27272a] light:bg-white light:border light:border-[#e4e4e7] transition-all duration-200';
}

function inputFieldClass(): string {
  return 'w-full px-3 py-2 rounded-lg text-sm outline-none focus:border-vyper-500 focus:shadow-[0_0_0_2px_rgba(108,92,231,0.2)] dark:bg-[#18181b] dark:border dark:border-[#27272a] dark:text-[#f4f4f5] light:bg-white light:border light:border-[#d4d4d8] light:text-[#09090b] transition-all';
}

export default function ReportCenter() {
  const [reports, setReports] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [showGenerate, setShowGenerate] = useState(false);
  const [genAuditId, setGenAuditId] = useState('');
  const [genFormat, setGenFormat] = useState('immunefi');
  const [genLoading, setGenLoading] = useState(false);
  const [genError, setGenError] = useState('');

  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        const res = await api.getReports(50);
        if (!cancelled) setReports(res.data || []);
      } catch (err: any) {
        if (!cancelled) setError(err?.message || 'Failed to fetch reports');
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    load();
    return () => { cancelled = true; };
  }, []);

  async function handleGenerate() {
    if (!genAuditId.trim()) return;
    setGenLoading(true);
    setGenError('');
    try {
      await api.generateReport(genAuditId.trim(), genFormat);
      setShowGenerate(false);
      setGenAuditId('');
      // Refresh reports list
      const res = await api.getReports(50);
      setReports(res.data || []);
    } catch (err: any) {
      setGenError(err?.message || 'Failed to generate report');
    } finally {
      setGenLoading(false);
    }
  }

  const formats = ['immunefi', 'full', 'pdf', 'markdown'];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold">Report Center</h2>
          <p className="dark:text-[#a1a1aa] light:text-[#71717a] mt-1">
            Generated audit reports
          </p>
        </div>
        <button
          onClick={() => setShowGenerate(true)}
          className="bg-vyper-500 text-white px-4 py-2 rounded-lg font-medium hover:bg-vyper-600 transition-all text-sm flex items-center gap-2"
        >
          <svg className="w-4 h-4" viewBox="0 0 20 20" fill="currentColor">
            <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm1-11a1 1 0 10-2 0v2H7a1 1 0 100 2h2v2a1 1 0 102 0v-2h2a1 1 0 100-2h-2V7z" clipRule="evenodd" />
          </svg>
          Generate Report
        </button>
      </div>

      {error && (
        <div className="rounded-xl p-4 bg-red-500/10 border border-red-500/20 text-red-400 text-sm flex items-center gap-2">
          <svg className="w-4 h-4 flex-shrink-0" viewBox="0 0 20 20" fill="currentColor">
            <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
          </svg>
          <span>{error}</span>
        </div>
      )}

      <div className={statCardClass()}>
        <h3 className="font-semibold mb-4">Reports ({reports.length})</h3>
        {loading ? (
          <div className="text-center py-8 text-sm dark:text-[#a1a1aa] light:text-[#71717a]">Loading reports...</div>
        ) : reports.length === 0 ? (
          <div className="text-center py-8 text-sm dark:text-[#a1a1aa] light:text-[#71717a]">No reports generated yet.</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider dark:bg-[#18181b] dark:text-[#a1a1aa] dark:border-b dark:border-[#27272a] light:bg-[#f4f4f5] light:text-[#71717a] light:border-b light:border-[#e4e4e7]">Report ID</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider dark:bg-[#18181b] dark:text-[#a1a1aa] dark:border-b dark:border-[#27272a] light:bg-[#f4f4f5] light:text-[#71717a] light:border-b light:border-[#e4e4e7]">Audit ID</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider dark:bg-[#18181b] dark:text-[#a1a1aa] dark:border-b dark:border-[#27272a] light:bg-[#f4f4f5] light:text-[#71717a] light:border-b light:border-[#e4e4e7]">Format</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider dark:bg-[#18181b] dark:text-[#a1a1aa] dark:border-b dark:border-[#27272a] light:bg-[#f4f4f5] light:text-[#71717a] light:border-b light:border-[#e4e4e7]">Status</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider dark:bg-[#18181b] dark:text-[#a1a1aa] dark:border-b dark:border-[#27272a] light:bg-[#f4f4f5] light:text-[#71717a] light:border-b light:border-[#e4e4e7]">Date</th>
                  <th className="px-4 py-3 text-right text-xs font-semibold uppercase tracking-wider dark:bg-[#18181b] dark:text-[#a1a1aa] dark:border-b dark:border-[#27272a] light:bg-[#f4f4f5] light:text-[#71717a] light:border-b light:border-[#e4e4e7]">Actions</th>
                </tr>
              </thead>
              <tbody>
                {reports.map((r: any, i: number) => (
                  <tr key={r.report_id || r.id || i} className="dark:border-b dark:border-[#27272a] light:border-b light:border-[#e4e4e7] hover:dark:bg-vyper-500/5 hover:light:bg-vyper-500/3 transition-colors">
                    <td className="px-4 py-3 text-sm font-mono text-xs dark:text-[#f4f4f5] light:text-[#09090b]">{(r.report_id || r.id || '').slice(0, 12)}...</td>
                    <td className="px-4 py-3 text-sm font-mono text-xs dark:text-[#f4f4f5] light:text-[#09090b]">{(r.audit_id || '').slice(0, 12)}...</td>
                    <td className="px-4 py-3 text-sm dark:text-[#f4f4f5] light:text-[#09090b]">{r.format || '—'}</td>
                    <td className="px-4 py-3 text-sm">
                      <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${
                        r.status === 'completed' || r.status === 'ready' ? 'bg-green-500/20 text-green-400' :
                        r.status === 'failed' ? 'bg-red-500/20 text-red-400' : 'bg-yellow-500/20 text-yellow-400'
                      }`}>{r.status || 'unknown'}</span>
                    </td>
                    <td className="px-4 py-3 text-xs dark:text-[#a1a1aa] light:text-[#71717a]">{r.created_at ? new Date(r.created_at).toLocaleDateString() : '—'}</td>
                    <td className="px-4 py-3 text-right">
                      {r.download_url || r.url ? (
                        <a
                          href={r.download_url || r.url}
                          className="text-xs text-vyper-400 hover:text-vyper-300 font-medium"
                          target="_blank"
                          rel="noopener noreferrer"
                        >
                          Download
                        </a>
                      ) : (
                        <span className="text-xs dark:text-[#52525b] light:text-[#a1a1aa]">—</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Generate Modal */}
      {showGenerate && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/50"
          onClick={(e) => { if (e.target === e.currentTarget) setShowGenerate(false); }}
        >
          <div
            className="rounded-xl p-6 w-full max-w-md mx-4 dark:bg-[#1a1a1e] dark:border dark:border-[#27272a] light:bg-white light:border light:border-[#e4e4e7]"
            onClick={(e) => e.stopPropagation()}
          >
            <h3 className="font-semibold text-lg mb-4">Generate Report</h3>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium mb-1 dark:text-[#f4f4f5] light:text-[#09090b]">Audit ID</label>
                <input
                  type="text"
                  className={`${inputFieldClass()} font-mono text-xs`}
                  placeholder="Audit ID..."
                  value={genAuditId}
                  onChange={(e) => setGenAuditId(e.target.value)}
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-1 dark:text-[#f4f4f5] light:text-[#09090b]">Format</label>
                <select className={inputFieldClass()} value={genFormat} onChange={(e) => setGenFormat(e.target.value)}>
                  {formats.map((f) => (
                    <option key={f} value={f}>{f}</option>
                  ))}
                </select>
              </div>
              {genError && <div className="text-sm text-red-400">{genError}</div>}
            </div>
            <div className="flex justify-end gap-3 mt-6">
              <button
                onClick={() => setShowGenerate(false)}
                disabled={genLoading}
                className="bg-transparent border dark:border-[#27272a] dark:text-[#a1a1aa] light:border-[#e4e4e7] light:text-[#71717a] px-4 py-2 rounded-lg font-medium hover:border-vyper-500 hover:text-vyper-500 transition-all disabled:opacity-50"
              >
                Cancel
              </button>
              <button
                onClick={handleGenerate}
                disabled={genLoading || !genAuditId.trim()}
                className="bg-vyper-500 text-white px-4 py-2 rounded-lg font-medium hover:bg-vyper-600 transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
              >
                {genLoading ? (
                  <>
                    <svg className="w-4 h-4 animate-spin" viewBox="0 0 24 24" fill="none">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                    </svg>
                    Generating...
                  </>
                ) : 'Generate'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
