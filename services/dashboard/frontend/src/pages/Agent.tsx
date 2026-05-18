import { useState, useEffect } from 'react';
import { api } from '../lib/api';

interface TeamRole {
  role: string;
  title: string;
  expertise: string;
  allowed_skills: string[];
  registered: boolean;
  skills_loaded: number;
}

interface TeamStructure {
  team_size: number;
  roles: TeamRole[];
}

interface SubAgentInfo {
  role: string;
  status: string;
  task: string;
  summary: string;
  steps: number;
  output: Record<string, any>;
  error: string | null;
}

interface LeadStep {
  step: number;
  thought: string;
  action: string;
  action_input: Record<string, any>;
  observation: string;
  status: string;
  duration_ms: number;
}

interface TeamSession {
  team_session_id: string;
  task_type: string;
  goal: string;
  status: string;
  lead_steps: LeadStep[];
  sub_agents: Record<string, SubAgentInfo>;
  output: Record<string, any>;
  error: string | null;
  created_at: string;
}

interface SessionSummary {
  team_session_id: string;
  task_type: string;
  status: string;
  lead_steps: number;
  sub_agents: string[];
  goal: string;
  created_at: string;
  error: string | null;
}

const STATUS_COLORS: Record<string, string> = {
  completed: 'bg-green-500/20 text-green-400',
  failed: 'bg-red-500/20 text-red-400',
  stopped: 'bg-yellow-500/20 text-yellow-400',
  pending: 'bg-blue-500/20 text-blue-400',
  thinking: 'bg-purple-500/20 text-purple-400',
  acting: 'bg-purple-500/20 text-purple-400',
};

export default function Agent() {
  // Team structure
  const [team, setTeam] = useState<TeamStructure | null>(null);
  // Sessions
  const [sessions, setSessions] = useState<SessionSummary[]>([]);
  const [selectedSession, setSelectedSession] = useState<TeamSession | null>(null);
  const [detailOpen, setDetailOpen] = useState(false);
  // Agent health
  const [health, setHealth] = useState<{ online: boolean; label: string }>({ online: false, label: 'Checking...' });
  // Audit form
  const [address, setAddress] = useState('0x4c9edd5852cd905f086c759e8383e09bff1e68b3');
  const [chain, setChain] = useState('ethereum');
  const [goal, setGoal] = useState('Full audit - find all critical vulnerabilities with PoC');
  const [running, setRunning] = useState(false);
  const [runError, setRunError] = useState('');

  // Load initial data
  useEffect(() => {
    loadTeam();
    loadSessions();
    loadHealth();
    const interval = setInterval(loadHealth, 15000);
    return () => clearInterval(interval);
  }, []);

  async function loadTeam() {
    try {
      const res = await api.getTeamStructure();
      if (res.data) setTeam(res.data);
    } catch { /* ignore */ }
  }

  async function loadSessions() {
    try {
      const res = await api.getTeamSessions({ limit: 20 });
      if (res.data?.sessions) setSessions(res.data.sessions);
    } catch { /* ignore */ }
  }

  async function loadHealth() {
    try {
      const res = await api.getAgentHealth();
      const d = res.data;
      setHealth({
        online: d?.status === 'ok',
        label: d?.status === 'ok'
          ? `Online — ${d.skills_loaded ?? '?'} skills, ${d.team_members ?? '?'} members`
          : 'Offline',
      });
    } catch {
      setHealth({ online: false, label: 'Offline' });
    }
  }

  async function handleRunAudit(e: React.FormEvent) {
    e.preventDefault();
    setRunning(true);
    setRunError('');
    try {
      const res = await api.runTeamAudit({
        task_type: 'full_audit',
        input_data: { contract_address: address.trim(), chain },
        goal,
        max_delegations: 15,
      });
      if (res.data?.team_session_id) {
        await loadSessions();
        await showSessionDetail(res.data.team_session_id);
      }
    } catch (err) {
      setRunError(err instanceof Error ? err.message : 'Failed');
    } finally {
      setRunning(false);
    }
  }

  async function showSessionDetail(sessionId: string) {
    try {
      const res = await api.getTeamSession(sessionId);
      if (res.data) {
        setSelectedSession(res.data);
        setDetailOpen(true);
      }
    } catch { /* ignore */ }
  }

  function closeDetail() {
    setDetailOpen(false);
    setSelectedSession(null);
  }

  return (
    <div className="max-w-7xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold">AI Agent Team</h2>
          <p className="text-sm dark:text-[#a1a1aa] light:text-[#71717a] mt-1">
            Multi-agent audit team with 7 specialized roles
          </p>
        </div>
        <div className="flex items-center gap-2 text-sm">
          <span className={`w-2 h-2 rounded-full ${health.online ? 'bg-green-500 shadow-[0_0_6px_rgba(34,197,94,0.5)]' : 'bg-red-500 shadow-[0_0_6px_rgba(239,68,68,0.5)]'}`} />
          <span className="dark:text-[#a1a1aa]">{health.label}</span>
        </div>
      </div>

      {/* Team Org Chart */}
      <div className="card">
        <h3 className="text-sm font-semibold uppercase tracking-wider dark:text-[#a1a1aa] mb-4">Team Structure</h3>
        {team ? (
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
            {team.roles.filter(r => r.role === 'lead_auditor').map(leader => (
              <div key={leader.role} className="col-span-full mb-1">
                <div className="agent-role-card card p-3 text-center border border-vyper-500/30">
                  <div className="text-lg mb-1">🎯</div>
                  <div className="font-semibold text-sm">{leader.title}</div>
                  <div className="text-xs dark:text-[#a1a1aa]">{leader.expertise}</div>
                  <div className="text-[10px] dark:text-[#a1a1aa] mt-1">Delegates to {team.team_size - 1} specialists</div>
                </div>
              </div>
            ))}
            {team.roles.filter(r => r.role !== 'lead_auditor').map(m => (
              <div key={m.role} className="agent-role-card card p-3">
                <div className="flex items-center gap-2 mb-1">
                  <span className={`w-2 h-2 rounded-full ${m.registered ? 'bg-green-500' : 'bg-red-500'}`} />
                  <span className="font-semibold text-sm">{m.title}</span>
                </div>
                <div className="text-[10px] dark:text-[#a1a1aa] leading-tight mb-2">{m.expertise}</div>
                <div className="flex flex-wrap gap-1">
                  {m.allowed_skills.map(s => (
                    <span key={s} className="text-[10px] px-1.5 py-0.5 rounded-full dark:bg-vyper-500/10 dark:text-vyper-300 light:bg-vyper-500/5 light:text-vyper-600">{s}</span>
                  ))}
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="text-sm dark:text-[#a1a1aa]">Loading team structure...</div>
        )}
      </div>

      {/* Run Audit Form */}
      <div className="card">
        <h3 className="text-sm font-semibold uppercase tracking-wider dark:text-[#a1a1aa] mb-4">Run Team Audit</h3>
        <form onSubmit={handleRunAudit} className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <label className="block text-xs dark:text-[#a1a1aa] mb-1">Contract Address</label>
              <input
                className="input-field font-mono text-xs"
                placeholder="0x..."
                value={address}
                onChange={e => setAddress(e.target.value)}
              />
            </div>
            <div>
              <label className="block text-xs dark:text-[#a1a1aa] mb-1">Chain</label>
              <select className="input-field" value={chain} onChange={e => setChain(e.target.value)}>
                <option value="ethereum">Ethereum</option>
                <option value="bsc">BSC</option>
                <option value="polygon">Polygon</option>
                <option value="arbitrum">Arbitrum</option>
                <option value="avalanche">Avalanche</option>
              </select>
            </div>
            <div>
              <label className="block text-xs dark:text-[#a1a1aa] mb-1">Goal</label>
              <input
                className="input-field"
                placeholder="e.g. Find all critical vulnerabilities"
                value={goal}
                onChange={e => setGoal(e.target.value)}
              />
            </div>
          </div>
          <div className="flex items-center gap-3">
            <button type="submit" disabled={running} className="btn-primary">
              {running ? '⟳ Running...' : 'Run Team Audit'}
            </button>
            {runError && <span className="text-red-400 text-sm">{runError}</span>}
          </div>
        </form>
      </div>

      {/* Session Detail */}
      {detailOpen && selectedSession && (
        <div className="card">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-sm font-semibold uppercase tracking-wider dark:text-[#a1a1aa]">
              Session: <span className="font-mono text-vyper-400">{selectedSession.team_session_id}</span>
            </h3>
            <div className="flex items-center gap-3">
              <span className={`badge ${STATUS_COLORS[selectedSession.status] || ''}`}>{selectedSession.status}</span>
              <button onClick={closeDetail} className="text-xs dark:text-[#a1a1aa] hover:text-white">✕</button>
            </div>
          </div>
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Lead Steps */}
            <div>
              <h4 className="text-xs font-semibold uppercase dark:text-[#a1a1aa] mb-3">Lead Auditor Steps</h4>
              {selectedSession.lead_steps?.length ? (
                <div className="space-y-3 max-h-80 overflow-y-auto">
                  {selectedSession.lead_steps.map(s => (
                    <div key={s.step} className="flex gap-3">
                      <div className="flex flex-col items-center">
                        <div className={`w-3 h-3 rounded-full border-2 ${
                          s.status === 'completed' ? 'bg-green-500 border-green-500' :
                          s.status === 'failed' ? 'bg-red-500 border-red-500' :
                          'bg-vyper-500 border-vyper-500 animate-pulse'
                        }`} />
                        <div className="w-0.5 flex-1 dark:bg-[#27272a] min-h-[24px]" />
                      </div>
                      <div className="flex-1 pb-3">
                        <div className="text-xs font-medium">{s.action}</div>
                        <div className="text-[10px] dark:text-[#a1a1aa]">{s.observation?.slice(0, 150) || '-'}</div>
                        {s.duration_ms ? <div className="text-[10px] dark:text-[#636363]">{(s.duration_ms / 1000).toFixed(1)}s</div> : null}
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-xs dark:text-[#a1a1aa]">No steps yet</div>
              )}
            </div>
            {/* Sub-Agents */}
            <div>
              <h4 className="text-xs font-semibold uppercase dark:text-[#a1a1aa] mb-3">Sub-Agent Results</h4>
              {selectedSession.sub_agents && Object.keys(selectedSession.sub_agents).length ? (
                <div className="space-y-3 max-h-80 overflow-y-auto">
                  {Object.entries(selectedSession.sub_agents).map(([role, sa]) => (
                    <div key={role} className="dark:bg-[#0f0f13] p-3 rounded-lg">
                      <div className="flex items-center justify-between mb-1">
                        <span className="text-xs font-semibold">{role}</span>
                        <span className={`badge ${STATUS_COLORS[sa.status] || ''} text-[10px]`}>{sa.status}</span>
                      </div>
                      <div className="text-[10px] dark:text-[#a1a1aa] mb-1">{sa.task?.slice(0, 120) || '-'}</div>
                      {sa.summary && <div className="text-[10px] dark:text-vyper-300">{sa.summary?.slice(0, 200)}</div>}
                      {sa.steps ? <div className="text-[10px] dark:text-[#636363] mt-1">{sa.steps} steps</div> : null}
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-xs dark:text-[#a1a1aa]">No sub-agents executed</div>
              )}
            </div>
          </div>
          {/* Output */}
          {selectedSession.output && Object.keys(selectedSession.output).length ? (
            <div className="mt-4">
              <h4 className="text-xs font-semibold uppercase dark:text-[#a1a1aa] mb-2">Output Summary</h4>
              <pre className="text-xs dark:bg-[#0f0f13] p-3 rounded-lg overflow-x-auto max-h-48">
                {JSON.stringify(selectedSession.output, null, 2).slice(0, 2000)}
              </pre>
            </div>
          ) : null}
        </div>
      )}

      {/* Session History */}
      <div className="card">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-sm font-semibold uppercase tracking-wider dark:text-[#a1a1aa]">Session History</h3>
          <button onClick={loadSessions} className="btn-secondary text-xs py-1 px-3">Refresh</button>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr>
                <th className="table-header text-left">Session ID</th>
                <th className="table-header text-left">Type</th>
                <th className="table-header text-left">Status</th>
                <th className="table-header text-right">Steps</th>
                <th className="table-header text-left">Goal</th>
                <th className="table-header text-left">Created</th>
                <th className="table-header text-right" />
              </tr>
            </thead>
            <tbody>
              {sessions.length ? sessions.map(s => (
                <tr key={s.team_session_id} className="table-row cursor-pointer" onClick={() => showSessionDetail(s.team_session_id)}>
                  <td className="table-cell font-mono text-xs">{s.team_session_id.slice(0, 16)}...</td>
                  <td className="table-cell text-xs">{s.task_type}</td>
                  <td className="table-cell"><span className={`badge ${STATUS_COLORS[s.status] || ''}`}>{s.status}</span></td>
                  <td className="table-cell text-xs text-right">{s.lead_steps}</td>
                  <td className="table-cell text-xs max-w-[200px] truncate">{s.goal || '-'}</td>
                  <td className="table-cell text-xs">
                    {s.created_at ? new Date(s.created_at).toLocaleString() : '-'}
                  </td>
                  <td className="table-cell text-right">
                    <button className="text-vyper-400 text-xs hover:underline" onClick={e => { e.stopPropagation(); showSessionDetail(s.team_session_id); }}>
                      View
                    </button>
                  </td>
                </tr>
              )) : (
                <tr><td colSpan={7} className="table-cell text-center dark:text-[#a1a1aa]">No sessions yet</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
