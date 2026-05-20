import { useEffect, useState } from 'react';
import { api } from '../lib/api';

function statCardClass(): string {
  return 'rounded-xl p-6 dark:bg-[#1a1a1e] dark:border dark:border-[#27272a] light:bg-white light:border light:border-[#e4e4e7] transition-all duration-200';
}

function inputFieldClass(): string {
  return 'w-full px-3 py-2 rounded-lg text-sm outline-none focus:border-vyper-500 focus:shadow-[0_0_0_2px_rgba(108,92,231,0.2)] dark:bg-[#18181b] dark:border dark:border-[#27272a] dark:text-[#f4f4f5] light:bg-white light:border light:border-[#d4d4d8] light:text-[#09090b] transition-all';
}

export default function ScannerDetail() {
  const [tools, setTools] = useState<Record<string, { status: string }> | null>(null);
  const [toolsLoading, setToolsLoading] = useState(true);
  const [auditId, setAuditId] = useState('');
  const [results, setResults] = useState<any>(null);
  const [resultsLoading, setResultsLoading] = useState(false);
  const [resultsError, setResultsError] = useState('');
  const [error, setError] = useState('');

  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        const res = await api.getScannerTools();
        if (!cancelled) setTools(res.data || null);
      } catch (err: any) {
        if (!cancelled) setError(err?.message || 'Failed to fetch scanner tools');
      } finally {
        if (!cancelled) setToolsLoading(false);
      }
    }
    load();
    return () => { cancelled = true; };
  }, []);

  async function handleFetchResults() {
    if (!auditId.trim()) return;
    setResultsLoading(true);
    setResultsError('');
    setResults(null);
    try {
      const res = await api.getScannerResults(auditId.trim());
      setResults(res.data || null);
    } catch (err: any) {
      setResultsError(err?.message || 'Failed to fetch scanner results');
    } finally {
      setResultsLoading(false);
    }
  }

  const toolTypes: Record<string, string> = {
    slither: 'static',
    mythril: 'symbolic',
    echidna: 'fuzzer',
    forge: 'compiler',
    halmos: 'formal verification',
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
        <h2 className="text-2xl font-bold">Scanner Detail</h2>
        <p className="dark:text-[#a1a1aa] light:text-[#71717a] mt-1">
          Scanner tool health and audit results
        </p>
      </div>

      {error && (
        <div className="rounded-xl p-4 bg-red-500/10 border border-red-500/20 text-red-400 text-sm">{error}</div>
      )}

      {/* Tools Status */}
      <div className={statCardClass()}>
        <h3 className="font-semibold mb-4">Scanner Tools</h3>
        {toolsLoading ? (
          <div className="text-center py-4 text-sm dark:text-[#a1a1aa] light:text-[#71717a]">Loading tools...</div>
        ) : !tools || Object.keys(tools).length === 0 ? (
          <div className="text-center py-4 text-sm dark:text-[#a1a1aa] light:text-[#71717a]">No tools available.</div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
            {Object.entries(tools).map(([name, info]) => (
              <div key={name} className="flex items-center gap-3 p-3 rounded-lg dark:bg-[#18181b] light:bg-[#f4f4f5] dark:border dark:border-[#27272a] light:border light:border-[#e4e4e7]">
                <span className={`w-2.5 h-2.5 rounded-full ${statusDot(info.status)}`} />
                <div className="flex items-center gap-2 flex-1 min-w-0">
                  <span className="font-medium text-sm truncate">{name}</span>
                  {toolTypes[name] && (
                    <span className="text-xs dark:text-[#a1a1aa] italic">{toolTypes[name]}</span>
                  )}
                </div>
                <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${
                  info.status === 'healthy' ? 'bg-green-500/20 text-green-400' : 'bg-red-500/20 text-red-400'
                }`}>{info.status}</span>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Halmos Info */}
      {tools && 'halmos' in tools && (
        <div className={statCardClass()}>
          <div className="flex items-start gap-3">
            <div className="w-8 h-8 rounded-lg flex items-center justify-center shrink-0 dark:bg-[#18181b] light:bg-[#f4f4f5] dark:border dark:border-[#27272a] light:border light:border-[#e4e4e7]">
              <svg className="w-4 h-4 dark:text-[#a1a1aa] light:text-[#71717a]" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M13 10V3L4 14h7v7l9-11h-7z" />
              </svg>
            </div>
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2 flex-wrap">
                <h4 className="font-medium text-sm">Halmos — Formal Verification Engine</h4>
                <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${
                  tools.halmos?.status === 'healthy'
                    ? 'bg-green-500/20 text-green-400'
                    : 'bg-gray-500/20 text-gray-400'
                }`}>{tools.halmos?.status || 'unreachable'}</span>
              </div>
              <p className="text-xs dark:text-[#a1a1aa] light:text-[#71717a] mt-1">
                Mathematically proves contract correctness — beyond static analysis
              </p>
              {tools.halmos?.status !== 'healthy' && (
                <p className="text-xs text-gray-500 mt-1 italic">Halmos service not running</p>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Fetch Results */}
      <div className={statCardClass()}>
        <h3 className="font-semibold mb-4">Scan Results</h3>
        <div className="flex gap-3 mb-4">
          <input
            type="text"
            className={`${inputFieldClass()} font-mono text-xs flex-1`}
            placeholder="Enter audit ID..."
            value={auditId}
            onChange={(e) => setAuditId(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleFetchResults()}
          />
          <button
            onClick={handleFetchResults}
            disabled={resultsLoading || !auditId.trim()}
            className="bg-vyper-500 text-white px-4 py-2 rounded-lg font-medium hover:bg-vyper-600 transition-all disabled:opacity-50 disabled:cursor-not-allowed text-sm"
          >
            {resultsLoading ? 'Fetching...' : 'Fetch Results'}
          </button>
        </div>
        {resultsError && (
          <div className="text-sm text-red-400 mb-3">{resultsError}</div>
        )}
        {results && (
          <pre className="p-4 rounded-lg dark:bg-[#18181b] light:bg-[#f4f4f5] dark:border dark:border-[#27272a] light:border light:border-[#e4e4e7] overflow-x-auto text-xs font-mono max-h-96">
            {JSON.stringify(results, null, 2)}
          </pre>
        )}
        {!results && !resultsError && !resultsLoading && (
          <div className="text-center py-4 text-sm dark:text-[#a1a1aa] light:text-[#71717a]">
            Enter an audit ID above to fetch scanner results.
          </div>
        )}
      </div>
    </div>
  );
}
