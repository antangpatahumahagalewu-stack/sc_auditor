import { useEffect, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { api, type VpCase, type CaseStatsData } from '../lib/api';

const SEVERITY_COLORS: Record<string, string> = {
  Critical: 'bg-red-500/20 text-red-400',
  High: 'bg-orange-500/20 text-orange-400',
  Medium: 'bg-yellow-500/20 text-yellow-400',
  Low: 'bg-green-500/20 text-green-400',
  Info: 'bg-blue-500/20 text-blue-400',
};

const SEVERITY_ORDER = ['Critical', 'High', 'Medium', 'Low', 'Info'];

function statCardClass() {
  return 'rounded-xl p-6 dark:bg-[#1a1a1e] dark:border dark:border-[#27272a] light:bg-white light:border light:border-[#e4e4e7] transition-all duration-200';
}

function inputFieldClass() {
  return 'w-full px-3 py-2 rounded-lg text-sm outline-none focus:border-vyper-500 focus:shadow-[0_0_0_2px_rgba(108,92,231,0.2)] dark:bg-[#18181b] dark:border dark:border-[#27272a] dark:text-[#f4f4f5] light:bg-white light:border light:border-[#d4d4d8] light:text-[#09090b] transition-all';
}

export default function Cases() {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();

  const [cases, setCases] = useState<VpCase[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [stats, setStats] = useState<CaseStatsData | null>(null);

  // Filters
  const [search, setSearch] = useState(searchParams.get('search') || '');
  const [severityFilter, setSeverityFilter] = useState(searchParams.get('severity') || '');
  const [sort, setSort] = useState(searchParams.get('sort') || 'created_at');
  const [order, setOrder] = useState(searchParams.get('order') || 'desc');

  // Fetch cases
  useEffect(() => {
    let cancelled = false;
    async function load() {
      setLoading(true);
      try {
        const params: any = { status: 'OPEN', limit: 100 };
        if (search) params.search = search;
        if (severityFilter) params.severity = severityFilter;
        params.sort = sort;
        params.order = order;

        const [casesRes, statsRes] = await Promise.all([
          api.getCases(params),
          api.getCaseStats(),
        ]);
        if (!cancelled) {
          setCases(casesRes.data || []);
          setStats(statsRes.data || null);
          setError('');
        }
      } catch (err: any) {
        if (!cancelled) setError(err?.message || 'Failed to load cases');
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    load();
    return () => { cancelled = true; };
  }, [search, severityFilter, sort, order]);

  // Sync URL params
  useEffect(() => {
    const params = new URLSearchParams();
    if (search) params.set('search', search);
    if (severityFilter) params.set('severity', severityFilter);
    if (sort !== 'created_at') params.set('sort', sort);
    if (order !== 'desc') params.set('order', order);
    setSearchParams(params, { replace: true });
  }, [search, severityFilter, sort, order, setSearchParams]);

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

  function severityBadge(sev: string) {
    const cls = SEVERITY_COLORS[sev] || 'bg-gray-500/20 text-gray-400';
    return <span className={`px-2 py-0.5 rounded-full text-xs font-semibold ${cls}`}>{sev}</span>;
  }

  function confidenceBar(conf: number) {
    const pct = Math.round(conf * 100);
    const color = pct >= 80 ? 'bg-green-500' : pct >= 60 ? 'bg-yellow-500' : 'bg-red-500';
    return (
      <div className="flex items-center gap-2">
        <div className="w-16 h-1.5 rounded-full dark:bg-[#27272a] light:bg-[#e4e4e7] overflow-hidden">
          <div className={`h-full rounded-full ${color}`} style={{ width: `${pct}%` }} />
        </div>
        <span className="text-xs font-mono">{pct}%</span>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h2 className="text-2xl font-bold">Open Cases</h2>
        <p className="dark:text-[#a1a1aa] light:text-[#71717a] mt-1">
          Active bug findings that need your review
        </p>
      </div>

      {/* Stats summary */}
      {stats && (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
          <div className={statCardClass()}>
            <div className="text-sm dark:text-[#a1a1aa] light:text-[#71717a]">Open Cases</div>
            <div className="text-2xl font-bold mt-1">{stats.open_cases}</div>
          </div>
          <div className={statCardClass()}>
            <div className="text-sm dark:text-[#a1a1aa] light:text-[#71717a]">Avg Confidence</div>
            <div className="text-2xl font-bold mt-1">{(stats.avg_confidence * 100).toFixed(0)}%</div>
          </div>
          <div className={statCardClass()}>
            <div className="text-sm dark:text-[#a1a1aa] light:text-[#71717a]">Total Bounty</div>
            <div className="text-2xl font-bold mt-1 text-green-400">
              ${stats.total_bounty.toLocaleString()}
            </div>
          </div>
          <div className={statCardClass()}>
            <div className="text-sm dark:text-[#a1a1aa] light:text-[#71717a]">Closed Cases</div>
            <div className="text-2xl font-bold mt-1">{stats.closed_cases}</div>
          </div>
        </div>
      )}

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

      {/* Filters */}
      <div className="flex flex-wrap gap-4 items-center">
        <div className="flex-1 min-w-[200px]">
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search cases by title, contract, ID..."
            className={inputFieldClass()}
          />
        </div>
        <select
          value={severityFilter}
          onChange={(e) => setSeverityFilter(e.target.value)}
          className={`${inputFieldClass()} w-auto`}
        >
          <option value="">All Severities</option>
          {SEVERITY_ORDER.map((s) => (
            <option key={s} value={s}>{s}</option>
          ))}
        </select>
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
                <th
                  className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider cursor-pointer select-none dark:bg-[#18181b] dark:text-[#a1a1aa] dark:border-b dark:border-[#27272a] light:bg-[#f4f4f5] light:text-[#71717a] light:border-b light:border-[#e4e4e7]"
                  onClick={() => handleSort('severity')}
                >
                  Severity {sortIcon('severity')}
                </th>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider dark:bg-[#18181b] dark:text-[#a1a1aa] dark:border-b dark:border-[#27272a] light:bg-[#f4f4f5] light:text-[#71717a] light:border-b light:border-[#e4e4e7]">
                  Scanners
                </th>
                <th
                  className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider cursor-pointer select-none dark:bg-[#18181b] dark:text-[#a1a1aa] dark:border-b dark:border-[#27272a] light:bg-[#f4f4f5] light:text-[#71717a] light:border-b light:border-[#e4e4e7]"
                  onClick={() => handleSort('confidence')}
                >
                  Confidence {sortIcon('confidence')}
                </th>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider dark:bg-[#18181b] dark:text-[#a1a1aa] dark:border-b dark:border-[#27272a] light:bg-[#f4f4f5] light:text-[#71717a] light:border-b light:border-[#e4e4e7]">
                  Contract
                </th>
                <th
                  className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider cursor-pointer select-none dark:bg-[#18181b] dark:text-[#a1a1aa] dark:border-b dark:border-[#27272a] light:bg-[#f4f4f5] light:text-[#71717a] light:border-b light:border-[#e4e4e7]"
                  onClick={() => handleSort('created_at')}
                >
                  Created {sortIcon('created_at')}
                </th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr>
                  <td colSpan={6} className="px-4 py-8 text-center text-sm dark:text-[#a1a1aa] light:text-[#71717a]">
                    Loading cases...
                  </td>
                </tr>
              ) : cases.length === 0 ? (
                <tr>
                  <td colSpan={6} className="px-4 py-8 text-center text-sm dark:text-[#a1a1aa] light:text-[#71717a]">
                    No open cases. Run a scan to find bugs!
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
                    <td className="px-4 py-3">{severityBadge(c.severity)}</td>
                    <td className="px-4 py-3">
                      <div className="flex flex-wrap gap-1">
                        {c.scanners.map((s, i) => (
                          <span key={i} className="text-xs px-1.5 py-0.5 rounded dark:bg-[#27272a] light:bg-[#e4e4e7] font-mono">
                            {s.name}
                          </span>
                        ))}
                      </div>
                    </td>
                    <td className="px-4 py-3">{confidenceBar(c.confidence)}</td>
                    <td className="px-4 py-3">
                      <span className="text-sm font-mono text-xs">{c.contract || '—'}</span>
                    </td>
                    <td className="px-4 py-3 text-xs dark:text-[#a1a1aa] light:text-[#71717a]">
                      {new Date(c.created_at).toLocaleDateString()}
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
