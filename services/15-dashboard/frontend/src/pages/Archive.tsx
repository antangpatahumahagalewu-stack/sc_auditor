import { useEffect, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { api, type VpCase } from '../lib/api';

const REASON_LABELS: Record<string, string> = {
  confirmed: '✅ Confirmed',
  rejected: '❌ Rejected',
  duplicate: '🔁 Duplicate',
  false_positive: '⚠️ False Positive',
};

function statCardClass() {
  return 'rounded-xl p-6 dark:bg-[#1a1a1e] dark:border dark:border-[#27272a] light:bg-white light:border light:border-[#e4e4e7]';
}

function inputFieldClass() {
  return 'w-full px-3 py-2 rounded-lg text-sm outline-none focus:border-vyper-500 focus:shadow-[0_0_0_2px_rgba(108,92,231,0.2)] dark:bg-[#18181b] dark:border dark:border-[#27272a] dark:text-[#f4f4f5] light:bg-white light:border light:border-[#d4d4d8] light:text-[#09090b] transition-all';
}

export default function Archive() {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();

  const [cases, setCases] = useState<VpCase[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [search, setSearch] = useState(searchParams.get('search') || '');
  const [sort, setSort] = useState(searchParams.get('sort') || 'closed_at');
  const [order, setOrder] = useState(searchParams.get('order') || 'desc');

  useEffect(() => {
    let cancelled = false;
    async function load() {
      setLoading(true);
      try {
        const params: any = { limit: 100 };
        if (search) params.search = search;
        params.sort = sort;
        params.order = order;

        const res = await api.getArchive(params);
        if (!cancelled) {
          setCases(res.data || []);
          setError('');
        }
      } catch (err: any) {
        if (!cancelled) setError(err?.message || 'Failed to load archive');
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    load();
    return () => { cancelled = true; };
  }, [search, sort, order]);

  useEffect(() => {
    const params = new URLSearchParams();
    if (search) params.set('search', search);
    if (sort !== 'closed_at') params.set('sort', sort);
    if (order !== 'desc') params.set('order', order);
    setSearchParams(params, { replace: true });
  }, [search, sort, order, setSearchParams]);

  function handleSort(col: string) {
    if (sort === col) {
      setOrder(order === 'asc' ? 'desc' : 'asc');
    } else {
      setSort(col);
      setOrder('desc');
    }
  }

  function sortIcon(col: string) {
    if (sort !== col) return '↕';
    return order === 'asc' ? '↑' : '↓';
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h2 className="text-2xl font-bold">Archive</h2>
        <p className="dark:text-[#a1a1aa] light:text-[#71717a] mt-1">
          Closed cases — historical bug findings
        </p>
      </div>

      {/* Error Banner */}
      {error && (
        <div className="rounded-xl p-4 bg-red-500/10 border border-red-500/20 text-red-400 text-sm flex items-center gap-2">
          <svg className="w-4 h-4 flex-shrink-0" viewBox="0 0 20 20" fill="currentColor">
            <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
          </svg>
          <span>{error}</span>
          <button onClick={() => setError('')} className="ml-auto text-red-400/70 hover:text-red-400">✕</button>
        </div>
      )}

      {/* Search */}
      <div className="flex flex-wrap gap-4 items-center">
        <div className="flex-1 min-w-[200px]">
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search archived cases..."
            className={inputFieldClass()}
          />
        </div>
      </div>

      {/* Table */}
      <div className={statCardClass()}>
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr>
                <th
                  className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider cursor-pointer select-none dark:bg-[#18181b] dark:text-[#a1a1aa] dark:border-b dark:border-[#27272a] light:bg-[#f4f4f5] light:text-[#71717a] light:border-b light:border-[#e4e4e7]"
                  onClick={() => handleSort('title')}
                >
                  Case {sortIcon('title')}
                </th>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider dark:bg-[#18181b] dark:text-[#a1a1aa] dark:border-b dark:border-[#27272a] light:bg-[#f4f4f5] light:text-[#71717a] light:border-b light:border-[#e4e4e7]">
                  Reason
                </th>
                <th className="px-4 py-3 text-right text-xs font-semibold uppercase tracking-wider dark:bg-[#18181b] dark:text-[#a1a1aa] dark:border-b dark:border-[#27272a] light:bg-[#f4f4f5] light:text-[#71717a] light:border-b light:border-[#e4e4e7]">
                  Bounty
                </th>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider dark:bg-[#18181b] dark:text-[#a1a1aa] dark:border-b dark:border-[#27272a] light:bg-[#f4f4f5] light:text-[#71717a] light:border-b light:border-[#e4e4e7]">
                  Severity
                </th>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider dark:bg-[#18181b] dark:text-[#a1a1aa] dark:border-b dark:border-[#27272a] light:bg-[#f4f4f5] light:text-[#71717a] light:border-b light:border-[#e4e4e7]">
                  Contract
                </th>
                <th
                  className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider cursor-pointer select-none dark:bg-[#18181b] dark:text-[#a1a1aa] dark:border-b dark:border-[#27272a] light:bg-[#f4f4f5] light:text-[#71717a] light:border-b light:border-[#e4e4e7]"
                  onClick={() => handleSort('closed_at')}
                >
                  Closed {sortIcon('closed_at')}
                </th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr>
                  <td colSpan={6} className="px-4 py-8 text-center text-sm dark:text-[#a1a1aa] light:text-[#71717a]">
                    Loading archive...
                  </td>
                </tr>
              ) : cases.length === 0 ? (
                <tr>
                  <td colSpan={6} className="px-4 py-8 text-center text-sm dark:text-[#a1a1aa] light:text-[#71717a]">
                    No closed cases yet.
                  </td>
                </tr>
              ) : (
                cases.map((c) => (
                  <tr
                    key={c.case_id}
                    onClick={() => navigate(`/cases/${c.case_id}`)}
                    className="dark:border-b dark:border-[#27272a] light:border-b light:border-[#e4e4e7] hover:dark:bg-vyper-500/5 hover:light:bg-vyper-500/3 transition-colors cursor-pointer"
                  >
                    <td className="px-4 py-3">
                      <div className="text-sm font-medium">{c.title}</div>
                      <div className="text-xs font-mono dark:text-[#a1a1aa] light:text-[#71717a] mt-0.5">{c.case_id}</div>
                    </td>
                    <td className="px-4 py-3 text-sm">
                      {REASON_LABELS[c.closed_reason || ''] || c.closed_reason || '—'}
                    </td>
                    <td className="px-4 py-3 text-sm text-right font-mono">
                      {c.bounty_amount != null ? (
                        <span className="text-green-400">${c.bounty_amount.toLocaleString()}</span>
                      ) : (
                        <span className="dark:text-[#a1a1aa] light:text-[#71717a]">—</span>
                      )}
                    </td>
                    <td className="px-4 py-3 text-sm">{c.severity}</td>
                    <td className="px-4 py-3 text-sm font-mono text-xs">{c.contract || '—'}</td>
                    <td className="px-4 py-3 text-xs dark:text-[#a1a1aa] light:text-[#71717a]">
                      {c.closed_at ? new Date(c.closed_at).toLocaleDateString() : '—'}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
