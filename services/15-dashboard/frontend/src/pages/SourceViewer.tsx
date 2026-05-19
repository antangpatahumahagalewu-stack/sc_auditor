import { useState } from 'react';
import { api } from '../lib/api';

function statCardClass(): string {
  return 'rounded-xl p-6 dark:bg-[#1a1a1e] dark:border dark:border-[#27272a] light:bg-white light:border light:border-[#e4e4e7] transition-all duration-200';
}

function inputFieldClass(): string {
  return 'w-full px-3 py-2 rounded-lg text-sm outline-none focus:border-vyper-500 focus:shadow-[0_0_0_2px_rgba(108,92,231,0.2)] dark:bg-[#18181b] dark:border dark:border-[#27272a] dark:text-[#f4f4f5] light:bg-white light:border light:border-[#d4d4d8] light:text-[#09090b] transition-all';
}

export default function SourceViewer() {
  const [auditId, setAuditId] = useState('');
  const [source, setSource] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  async function handleFetch() {
    if (!auditId.trim()) return;
    setLoading(true);
    setError('');
    setSource(null);
    try {
      const res = await api.getSourceCode(auditId.trim());
      setSource(res.data || null);
    } catch (err: any) {
      setError(err?.message || 'Failed to fetch source code');
    } finally {
      setLoading(false);
    }
  }

  const sourceCode = source?.source_code || source?.code || (typeof source === 'string' ? source : null);

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold">Source Viewer</h2>
        <p className="dark:text-[#a1a1aa] light:text-[#71717a] mt-1">
          View contract source code by audit ID
        </p>
      </div>

      <div className={statCardClass()}>
        <h3 className="font-semibold mb-4">Audit ID Lookup</h3>
        <div className="flex gap-3 mb-4">
          <input
            type="text"
            className={`${inputFieldClass()} font-mono text-xs flex-1`}
            placeholder="Enter audit ID..."
            value={auditId}
            onChange={(e) => setAuditId(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleFetch()}
          />
          <button
            onClick={handleFetch}
            disabled={loading || !auditId.trim()}
            className="bg-vyper-500 text-white px-4 py-2 rounded-lg font-medium hover:bg-vyper-600 transition-all disabled:opacity-50 disabled:cursor-not-allowed text-sm"
          >
            {loading ? 'Loading...' : 'Fetch Source'}
          </button>
        </div>

        {error && (
          <div className="text-sm text-red-400 mb-3">{error}</div>
        )}

        {source && (
          <div>
            {source.contract && (
              <div className="flex gap-4 mb-3 text-sm">
                <div>
                  <span className="dark:text-[#a1a1aa] light:text-[#71717a]">Contract: </span>
                  <span className="font-medium dark:text-[#f4f4f5] light:text-[#09090b]">{source.contract}</span>
                </div>
                {source.chain && (
                  <div>
                    <span className="dark:text-[#a1a1aa] light:text-[#71717a]">Chain: </span>
                    <span className="font-medium dark:text-[#f4f4f5] light:text-[#09090b]">{source.chain}</span>
                  </div>
                )}
                {source.line_count && (
                  <div>
                    <span className="dark:text-[#a1a1aa] light:text-[#71717a]">Lines: </span>
                    <span className="font-medium dark:text-[#f4f4f5] light:text-[#09090b]">{source.line_count}</span>
                  </div>
                )}
              </div>
            )}
            <pre className="p-4 rounded-lg dark:bg-[#18181b] light:bg-[#f4f4f5] dark:border dark:border-[#27272a] light:border light:border-[#e4e4e7] overflow-x-auto text-xs font-mono max-h-[65vh] whitespace-pre-wrap">
              <code>{sourceCode || JSON.stringify(source, null, 2)}</code>
            </pre>
          </div>
        )}

        {!source && !error && !loading && (
          <div className="text-center py-8 text-sm dark:text-[#a1a1aa] light:text-[#71717a]">
            Enter an audit ID above to view the contract source code.
          </div>
        )}
      </div>
    </div>
  );
}
