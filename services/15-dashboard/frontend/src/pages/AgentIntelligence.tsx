import { useState, useEffect } from 'react';
import { api } from '../lib/api';

interface DaemonStatus {
  running: boolean;
  interval: number;
  total_cycles: number;
  total_errors: number;
  auto_hunts_done: number;
  last_program_sync: number | null;
  last_self_assessment: number | null;
  uptime_seconds: number;
  avg_cycle_duration_ms: number;
  uptime: string;
}

interface SkillMetrics {
  skill_name: string;
  call_count: number;
  success_count: number;
  error_count: number;
  success_rate: number;
  avg_duration_ms: number;
  last_called: number;
  last_error: string | null;
}

interface MemStats {
  working: { entries: number };
  episodic_legacy: { entries: number };
  semantic: { entries: number };
  vector_store: { total_entries: number; total_searches: number; avg_search_ms: number };
  episodic_store: { total_entries: number };
  graph_memory: { total_entries: number };
}

interface LearningStats {
  total_sessions_analyzed: number;
  patterns_found: number;
  last_analysis: number;
  task_type_performance: Record<string, any>;
  top_error_patterns: Record<string, number>;
  skill_effectiveness: Record<string, any>;
}

interface MemorySearchResult {
  entry_id?: string;
  key: string;
  score?: number;
  content_preview?: string;
  label?: string;
  node_type?: string;
}

export default function AgentIntelligence() {
  const [daemon, setDaemon] = useState<DaemonStatus | null>(null);
  const [skills, setSkills] = useState<SkillMetrics[]>([]);
  const [memStats, setMemStats] = useState<MemStats | null>(null);
  const [learning, setLearning] = useState<LearningStats | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [searchStore, setSearchStore] = useState<'vector' | 'episodic' | 'graph'>('vector');
  const [searchResults, setSearchResults] = useState<MemorySearchResult[]>([]);
  const [searching, setSearching] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      api.getAgentDaemonStatus().then(r => r.data).catch(() => null),
      api.getAgentSkillMetrics().then(r => r.data).catch(() => null),
      api.getMemoryStats().then(r => r.data).catch(() => null),
      api.getLearningStats().then(r => r.data).catch(() => null),
    ]).then(([d, s, m, l]) => {
      if (d) setDaemon(d as DaemonStatus);
      if (s) setSkills(s as SkillMetrics[]);
      if (m) setMemStats(m as MemStats);
      if (l) setLearning(l as LearningStats);
      setLoading(false);
    });
  }, []);

  const handleSearch = async () => {
    if (!searchQuery.trim()) return;
    setSearching(true);
    try {
      const res = await api.memorySearch(searchQuery, searchStore);
      setSearchResults(res.data?.results || []);
    } catch {
      setSearchResults([]);
    }
    setSearching(false);
  };

  const handleDaemonToggle = async () => {
    try {
      if (daemon?.running) {
        await api.daemonStop();
      } else {
        await api.daemonStart();
      }
      const res = await api.getAgentDaemonStatus();
      setDaemon(res.data as DaemonStatus);
    } catch {}
  };

  if (loading) {
    return (
      <div className="p-8 text-center text-gray-400">
        <div className="animate-spin h-8 w-8 border-2 border-cyan-400 border-t-transparent rounded-full mx-auto mb-4" />
        Loading Agent Intelligence...
      </div>
    );
  }

  return (
    <div className="p-6 space-y-6">
      <h1 className="text-2xl font-bold text-white">Agent Intelligence</h1>

      {/* Daemon Control */}
      <div className="bg-gray-800/50 border border-gray-700 rounded-lg p-5">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-white">Autonomous Daemon</h2>
          <button
            onClick={handleDaemonToggle}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
              daemon?.running
                ? 'bg-red-600/20 text-red-400 hover:bg-red-600/30 border border-red-500/30'
                : 'bg-green-600/20 text-green-400 hover:bg-green-600/30 border border-green-500/30'
            }`}
          >
            {daemon?.running ? 'Stop Daemon' : 'Start Daemon'}
          </button>
        </div>

        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
          <div>
            <span className="text-gray-400">Status</span>
            <div className="flex items-center gap-2 mt-1">
              <span className={`h-2 w-2 rounded-full ${daemon?.running ? 'bg-green-400' : 'bg-gray-500'}`} />
              <span className="text-white font-medium">{daemon?.running ? 'Running' : 'Stopped'}</span>
            </div>
          </div>
          <div>
            <span className="text-gray-400">Cycles</span>
            <p className="text-white font-medium mt-1">{daemon?.total_cycles ?? 0}</p>
          </div>
          <div>
            <span className="text-gray-400">Errors</span>
            <p className={`font-medium mt-1 ${(daemon?.total_errors ?? 0) > 0 ? 'text-red-400' : 'text-white'}`}>
              {daemon?.total_errors ?? 0}
            </p>
          </div>
          <div>
            <span className="text-gray-400">Auto-Hunts</span>
            <p className="text-white font-medium mt-1">{daemon?.auto_hunts_done ?? 0}</p>
          </div>
          <div>
            <span className="text-gray-400">Uptime</span>
            <p className="text-white font-medium mt-1">{daemon?.uptime ?? 'N/A'}</p>
          </div>
          <div>
            <span className="text-gray-400">Avg Cycle</span>
            <p className="text-white font-medium mt-1">{daemon?.avg_cycle_duration_ms ?? 0}ms</p>
          </div>
          <div>
            <span className="text-gray-400">Interval</span>
            <p className="text-white font-medium mt-1">{daemon?.interval ?? 3600}s</p>
          </div>
          <div>
            <span className="text-gray-400">Last Sync</span>
            <p className="text-white font-medium mt-1">
              {daemon?.last_program_sync ? new Date(daemon.last_program_sync * 1000).toLocaleTimeString() : 'Never'}
            </p>
          </div>
        </div>
      </div>

      {/* Skill Metrics */}
      <div className="bg-gray-800/50 border border-gray-700 rounded-lg p-5">
        <h2 className="text-lg font-semibold text-white mb-4">Skill Metrics</h2>
        {skills.length === 0 ? (
          <p className="text-gray-400 text-sm">No skill data available yet.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-gray-400 border-b border-gray-700">
                  <th className="text-left py-2">Skill</th>
                  <th className="text-right py-2">Calls</th>
                  <th className="text-right py-2">Success Rate</th>
                  <th className="text-right py-2">Avg Duration</th>
                  <th className="text-right py-2">Errors</th>
                </tr>
              </thead>
              <tbody>
                {skills.map((s) => (
                  <tr key={s.skill_name} className="border-b border-gray-700/50">
                    <td className="py-2 text-white">{s.skill_name}</td>
                    <td className="py-2 text-right text-gray-300">{s.call_count}</td>
                    <td className={`py-2 text-right ${s.success_rate >= 0.8 ? 'text-green-400' : 'text-yellow-400'}`}>
                      {(s.success_rate * 100).toFixed(0)}%
                    </td>
                    <td className="py-2 text-right text-gray-300">{s.avg_duration_ms}ms</td>
                    <td className={`py-2 text-right ${s.error_count > 0 ? 'text-red-400' : 'text-gray-300'}`}>
                      {s.error_count}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Memory Search */}
      <div className="bg-gray-800/50 border border-gray-700 rounded-lg p-5">
        <h2 className="text-lg font-semibold text-white mb-4">Memory Search</h2>
        <div className="flex gap-3 mb-4">
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
            placeholder="Search memory (e.g., reentrancy, session, contract)..."
            className="flex-1 bg-gray-900 border border-gray-600 rounded-lg px-4 py-2 text-white text-sm focus:outline-none focus:border-cyan-500"
          />
          <select
            value={searchStore}
            onChange={(e) => setSearchStore(e.target.value as any)}
            className="bg-gray-900 border border-gray-600 rounded-lg px-3 py-2 text-white text-sm"
          >
            <option value="vector">Vector</option>
            <option value="episodic">Episodic</option>
            <option value="graph">Graph</option>
          </select>
          <button
            onClick={handleSearch}
            disabled={searching || !searchQuery.trim()}
            className="px-4 py-2 bg-cyan-600/20 text-cyan-400 border border-cyan-500/30 rounded-lg text-sm hover:bg-cyan-600/30 disabled:opacity-50"
          >
            {searching ? 'Searching...' : 'Search'}
          </button>
        </div>

        {searchResults.length > 0 && (
          <div className="space-y-2">
            {searchResults.map((r, i) => (
              <div key={i} className="bg-gray-900/50 rounded p-3 text-sm">
                <div className="flex items-center gap-2 mb-1">
                  <span className="text-cyan-400 font-medium">{r.key}</span>
                  {r.score !== undefined && (
                    <span className="text-gray-500 text-xs">score: {r.score}</span>
                  )}
                  {r.node_type && (
                    <span className="text-purple-400 text-xs bg-purple-400/10 px-2 py-0.5 rounded">{r.node_type}</span>
                  )}
                </div>
                <p className="text-gray-300 text-xs">{(r.content_preview || r.label || '')}</p>
              </div>
            ))}
          </div>
        )}
        {searchResults.length === 0 && searchQuery && !searching && (
          <p className="text-gray-500 text-sm">No results found.</p>
        )}
      </div>

      {/* Learning & Memory Stats */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Memory Stats */}
        <div className="bg-gray-800/50 border border-gray-700 rounded-lg p-5">
          <h2 className="text-lg font-semibold text-white mb-4">Memory Stats</h2>
          {memStats ? (
            <div className="space-y-3 text-sm">
              <div className="flex justify-between">
                <span className="text-gray-400">Vector Store</span>
                <span className="text-white">{memStats.vector_store?.total_entries ?? 0} items</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-400">Vector Searches</span>
                <span className="text-white">{memStats.vector_store?.total_searches ?? 0}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-400">Episodic Store</span>
                <span className="text-white">{memStats.episodic_store?.total_entries ?? 0} items</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-400">Graph Memory</span>
                <span className="text-white">{memStats.graph_memory?.total_entries ?? 0} items</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-400">Legacy Episodic</span>
                <span className="text-white">{memStats.episodic_legacy?.entries ?? 0} items</span>
              </div>
              <div className="flex justify-between pt-2 border-t border-gray-700">
                <span className="text-gray-300 font-medium">Total</span>
                <span className="text-cyan-400 font-medium">
                  {(memStats.vector_store?.total_entries ?? 0) +
                    (memStats.episodic_store?.total_entries ?? 0) +
                    (memStats.graph_memory?.total_entries ?? 0) +
                    (memStats.working?.entries ?? 0)} items
                </span>
              </div>
            </div>
          ) : (
            <p className="text-gray-400 text-sm">No data.</p>
          )}
        </div>

        {/* Learning Stats */}
        <div className="bg-gray-800/50 border border-gray-700 rounded-lg p-5">
          <h2 className="text-lg font-semibold text-white mb-4">Learning Stats</h2>
          {learning ? (
            <div className="space-y-3 text-sm">
              <div className="flex justify-between">
                <span className="text-gray-400">Sessions Analyzed</span>
                <span className="text-white">{learning.total_sessions_analyzed}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-400">Patterns Found</span>
                <span className="text-white">{learning.patterns_found}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-400">Last Analysis</span>
                <span className="text-white">
                  {learning.last_analysis
                    ? new Date(learning.last_analysis * 1000).toLocaleTimeString()
                    : 'Never'}
                </span>
              </div>

              {Object.keys(learning.top_error_patterns || {}).length > 0 && (
                <div className="pt-3 border-t border-gray-700">
                  <span className="text-red-400 text-xs font-medium uppercase tracking-wider">
                    Top Error Patterns
                  </span>
                  {Object.entries(learning.top_error_patterns)
                    .slice(0, 5)
                    .map(([pattern, count]) => (
                      <div key={pattern} className="flex justify-between mt-1">
                        <span className="text-gray-300 text-xs truncate mr-2">{pattern}</span>
                        <span className="text-red-400 text-xs font-medium">{count}x</span>
                      </div>
                    ))}
                </div>
              )}

              {Object.keys(learning.task_type_performance || {}).length > 0 && (
                <div className="pt-3 border-t border-gray-700">
                  <span className="text-cyan-400 text-xs font-medium uppercase tracking-wider">
                    Task Type Performance
                  </span>
                  {Object.entries(learning.task_type_performance).map(([tt, perf]: [string, any]) => (
                    <div key={tt} className="flex justify-between mt-1">
                      <span className="text-gray-300 text-xs">{tt}</span>
                      <span className="text-green-400 text-xs font-medium">
                        {perf.success}/{perf.total} ({(perf.total > 0 ? (perf.success / perf.total) * 100 : 0).toFixed(0)}%)
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          ) : (
            <p className="text-gray-400 text-sm">No learning data yet. Run some agent sessions first.</p>
          )}
        </div>
      </div>
    </div>
  );
}
