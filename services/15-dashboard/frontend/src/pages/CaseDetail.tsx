import { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { api, type VpCase } from '../lib/api';

const SEVERITY_COLORS: Record<string, string> = {
  Critical: 'bg-red-500/20 text-red-400 border-red-500/30',
  High: 'bg-orange-500/20 text-orange-400 border-orange-500/30',
  Medium: 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30',
  Low: 'bg-green-500/20 text-green-400 border-green-500/30',
  Info: 'bg-blue-500/20 text-blue-400 border-blue-500/30',
};

const CLOSE_REASONS = [
  { value: 'confirmed', label: '✅ Confirmed — Bounty Received' },
  { value: 'rejected', label: '❌ Rejected — Not a Bug' },
  { value: 'duplicate', label: '🔁 Duplicate — Already Reported' },
  { value: 'false_positive', label: '⚠️ False Positive' },
];

function inputFieldClass() {
  return 'w-full px-3 py-2 rounded-lg text-sm outline-none focus:border-vyper-500 focus:shadow-[0_0_0_2px_rgba(108,92,231,0.2)] dark:bg-[#18181b] dark:border dark:border-[#27272a] dark:text-[#f4f4f5] light:bg-white light:border light:border-[#d4d4d8] light:text-[#09090b] transition-all';
}

function statCardClass() {
  return 'rounded-xl p-6 dark:bg-[#1a1a1e] dark:border dark:border-[#27272a] light:bg-white light:border light:border-[#e4e4e7]';
}

export default function CaseDetail() {
  const { caseId } = useParams<{ caseId: string }>();
  const navigate = useNavigate();

  const [caseData, setCaseData] = useState<VpCase | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  // Close modal state
  const [showCloseModal, setShowCloseModal] = useState(false);
  const [closeReason, setCloseReason] = useState('confirmed');
  const [bountyAmount, setBountyAmount] = useState('');
  const [closeNotes, setCloseNotes] = useState('');
  const [closing, setClosing] = useState(false);
  const [closeError, setCloseError] = useState('');

  useEffect(() => {
    if (!caseId) return;
    let cancelled = false;
    async function load() {
      try {
        const res = await api.getCase(caseId!);
        if (!cancelled) {
          setCaseData(res.data || null);
          if (res.data?.bounty_amount) setBountyAmount(String(res.data.bounty_amount));
        }
      } catch {
        if (!cancelled) setError('Case not found');
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    load();
    return () => { cancelled = true; };
  }, [caseId]);

  async function handleClose() {
    if (!caseId || !caseData) return;
    setClosing(true);
    setCloseError('');
    try {
      const res = await api.closeCase(caseId, {
        closed_reason: closeReason,
        bounty_amount: bountyAmount ? parseFloat(bountyAmount) : undefined,
        notes: closeNotes,
      });
      setCaseData(res.data || null);
      setShowCloseModal(false);
    } catch (err: any) {
      setCloseError(err?.message || 'Failed to close case');
    } finally {
      setClosing(false);
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-sm dark:text-[#a1a1aa] light:text-[#71717a]">Loading case...</div>
      </div>
    );
  }

  if (error || !caseData) {
    return (
      <div className="space-y-4">
        <h2 className="text-2xl font-bold">Case Not Found</h2>
        <p className="dark:text-[#a1a1aa] light:text-[#71717a]">{error || 'The requested case does not exist.'}</p>
        <button onClick={() => navigate('/cases')} className="text-vyper-400 hover:text-vyper-300">
          ← Back to Cases
        </button>
      </div>
    );
  }

  const c = caseData;
  const isClosed = c.status === 'CLOSED';
  const sevColor = SEVERITY_COLORS[c.severity] || 'bg-gray-500/20 text-gray-400 border-gray-500/30';

  return (
    <div className="space-y-6">
      {/* Back + Header */}
      <div className="flex items-start justify-between">
        <div>
          <button
            onClick={() => navigate('/cases')}
            className="text-sm dark:text-[#a1a1aa] light:text-[#71717a] hover:text-vyper-400 mb-2 flex items-center gap-1"
          >
            <svg className="w-4 h-4" viewBox="0 0 20 20" fill="currentColor">
              <path fillRule="evenodd" d="M9.707 16.707a1 1 0 01-1.414 0l-6-6a1 1 0 010-1.414l6-6a1 1 0 011.414 1.414L5.414 9H17a1 1 0 110 2H5.414l4.293 4.293a1 1 0 010 1.414z" clipRule="evenodd" />
            </svg>
            Back to Cases
          </button>
          <h2 className="text-2xl font-bold">{c.title}</h2>
          <div className="flex items-center gap-3 mt-2">
            <span className={`px-2.5 py-0.5 rounded-full text-xs font-semibold border ${sevColor}`}>
              {c.severity}
            </span>
            <span className={`px-2.5 py-0.5 rounded-full text-xs font-semibold ${
              isClosed ? 'bg-red-500/20 text-red-400' : 'bg-green-500/20 text-green-400'
            }`}>
              {isClosed ? '🔴 CLOSED' : '🟢 OPEN'}
            </span>
            <span className="text-xs font-mono dark:text-[#a1a1aa] light:text-[#71717a]">{c.case_id}</span>
          </div>
        </div>

        {/* Actions */}
        <div className="flex gap-2">
          <a
            href={api.getCaseReportMdUrl(c.case_id)}
            download
            className="bg-transparent border dark:border-[#27272a] dark:text-[#a1a1aa] light:border-[#e4e4e7] light:text-[#71717a] px-3 py-2 rounded-lg text-sm font-medium hover:border-vyper-500 hover:text-vyper-500 transition-all flex items-center gap-1.5"
          >
            <svg className="w-4 h-4" viewBox="0 0 20 20" fill="currentColor">
              <path fillRule="evenodd" d="M3 17a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zm3.293-7.707a1 1 0 011.414 0L9 10.586V3a1 1 0 112 0v7.586l1.293-1.293a1 1 0 111.414 1.414l-3 3a1 1 0 01-1.414 0l-3-3a1 1 0 010-1.414z" clipRule="evenodd" />
            </svg>
            MD Report
          </a>
          <a
            href={api.getCaseReportPdfUrl(c.case_id)}
            download
            className="bg-transparent border dark:border-[#27272a] dark:text-[#a1a1aa] light:border-[#e4e4e7] light:text-[#71717a] px-3 py-2 rounded-lg text-sm font-medium hover:border-vyper-500 hover:text-vyper-500 transition-all flex items-center gap-1.5"
          >
            <svg className="w-4 h-4" viewBox="0 0 20 20" fill="currentColor">
              <path fillRule="evenodd" d="M3 17a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zm3.293-7.707a1 1 0 011.414 0L9 10.586V3a1 1 0 112 0v7.586l1.293-1.293a1 1 0 111.414 1.414l-3 3a1 1 0 01-1.414 0l-3-3a1 1 0 010-1.414z" clipRule="evenodd" />
            </svg>
            PDF Report
          </a>
          {!isClosed && (
            <button
              onClick={() => setShowCloseModal(true)}
              className="bg-vyper-500 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-vyper-600 transition-all flex items-center gap-1.5"
            >
              <svg className="w-4 h-4" viewBox="0 0 20 20" fill="currentColor">
                <path fillRule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clipRule="evenodd" />
              </svg>
              Close Case
            </button>
          )}
        </div>
      </div>

      {/* Main Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left — Details */}
        <div className="lg:col-span-2 space-y-6">
          {/* Description */}
          <div className={statCardClass()}>
            <h3 className="font-semibold mb-3">Description</h3>
            <p className="text-sm leading-relaxed dark:text-[#d4d4d8] light:text-[#52525b]">
              {c.description || 'No description provided.'}
            </p>
          </div>

          {/* Recommendation */}
          {c.recommendation && (
            <div className={statCardClass()}>
              <h3 className="font-semibold mb-3">Recommendation</h3>
              <p className="text-sm leading-relaxed dark:text-[#d4d4d8] light:text-[#52525b]">
                {c.recommendation}
              </p>
            </div>
          )}

          {/* Proof of Concept */}
          {c.proof_of_concept && (
            <div className={statCardClass()}>
              <h3 className="font-semibold mb-3">Proof of Concept</h3>
              <pre className="text-xs font-mono p-4 rounded-lg dark:bg-[#18181b] light:bg-[#f4f4f5] overflow-x-auto">
                {c.proof_of_concept}
              </pre>
            </div>
          )}

          {/* Scanners */}
          <div className={statCardClass()}>
            <h3 className="font-semibold mb-3">Scanners</h3>
            <div className="space-y-2">
              {c.scanners.map((s, i) => (
                <div key={i} className="flex items-center justify-between py-2 px-3 rounded-lg dark:bg-[#18181b] light:bg-[#f4f4f5]">
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-medium">{s.name}</span>
                    <span className="text-xs px-1.5 py-0.5 rounded dark:bg-[#27272a] light:bg-[#e4e4e7] font-mono">
                      {s.detector}
                    </span>
                  </div>
                  <span className="text-xs font-mono">{(s.confidence * 100).toFixed(0)}%</span>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Right — Metadata */}
        <div className="space-y-4">
          <div className={statCardClass()}>
            <h3 className="font-semibold mb-3">Case Info</h3>
            <dl className="space-y-3 text-sm">
              <div>
                <dt className="dark:text-[#a1a1aa] light:text-[#71717a] text-xs">Project</dt>
                <dd>{c.project || '—'}</dd>
              </div>
              <div>
                <dt className="dark:text-[#a1a1aa] light:text-[#71717a] text-xs">Contract</dt>
                <dd className="font-mono text-xs">{c.contract || '—'}</dd>
              </div>
              <div>
                <dt className="dark:text-[#a1a1aa] light:text-[#71717a] text-xs">Function</dt>
                <dd className="font-mono text-xs">{c.function || '—'}</dd>
              </div>
              <div>
                <dt className="dark:text-[#a1a1aa] light:text-[#71717a] text-xs">Line</dt>
                <dd>{c.line || '—'}</dd>
              </div>
              <div>
                <dt className="dark:text-[#a1a1aa] light:text-[#71717a] text-xs">Platform</dt>
                <dd>{c.platform || '—'}</dd>
              </div>
              <div>
                <dt className="dark:text-[#a1a1aa] light:text-[#71717a] text-xs">Confidence</dt>
                <dd>{(c.confidence * 100).toFixed(0)}% ({c.scanner_count} scanner{c.scanner_count !== 1 ? 's' : ''})</dd>
              </div>
              <div>
                <dt className="dark:text-[#a1a1aa] light:text-[#71717a] text-xs">Created</dt>
                <dd>{new Date(c.created_at).toLocaleString()}</dd>
              </div>
              {c.closed_at && (
                <>
                  <div>
                    <dt className="dark:text-[#a1a1aa] light:text-[#71717a] text-xs">Closed</dt>
                    <dd>{new Date(c.closed_at).toLocaleString()}</dd>
                  </div>
                  <div>
                    <dt className="dark:text-[#a1a1aa] light:text-[#71717a] text-xs">Closed Reason</dt>
                    <dd className="capitalize">{c.closed_reason || '—'}</dd>
                  </div>
                </>
              )}
              {c.bounty_amount != null && (
                <div>
                  <dt className="dark:text-[#a1a1aa] light:text-[#71717a] text-xs">Bounty</dt>
                  <dd className="text-green-400 font-semibold">${c.bounty_amount.toLocaleString()}</dd>
                </div>
              )}
            </dl>
          </div>

          {c.notes && (
            <div className={statCardClass()}>
              <h3 className="font-semibold mb-3">Notes</h3>
              <p className="text-sm whitespace-pre-wrap dark:text-[#d4d4d8] light:text-[#52525b]">
                {c.notes}
              </p>
            </div>
          )}
        </div>
      </div>

      {/* ── Close Case Modal ──────────────────────────── */}
      {showCloseModal && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/50"
          onClick={(e) => { if (e.target === e.currentTarget) setShowCloseModal(false); }}
        >
          <div
            className="rounded-xl p-6 w-full max-w-md mx-4 dark:bg-[#1a1a1e] dark:border dark:border-[#27272a] light:bg-white light:border light:border-[#e4e4e7]"
            onClick={(e) => e.stopPropagation()}
          >
            <h3 className="font-semibold text-lg mb-4">Close Case</h3>
            <p className="text-sm dark:text-[#a1a1aa] light:text-[#71717a] mb-4">
              Are you sure you want to close <strong>{c.case_id}</strong>?
              {c.case_id && <span className="block mt-1 text-xs">This action cannot be undone.</span>}
            </p>

            <div className="space-y-4">
              {/* Reason */}
              <div>
                <label className="block text-sm font-medium mb-1">Closure Reason</label>
                <select
                  value={closeReason}
                  onChange={(e) => setCloseReason(e.target.value)}
                  className={inputFieldClass()}
                >
                  {CLOSE_REASONS.map((r) => (
                    <option key={r.value} value={r.value}>{r.label}</option>
                  ))}
                </select>
              </div>

              {/* Bounty */}
              {(closeReason === 'confirmed' || closeReason === 'duplicate') && (
                <div>
                  <label className="block text-sm font-medium mb-1">
                    Bounty Amount ($)
                  </label>
                  <input
                    type="number"
                    value={bountyAmount}
                    onChange={(e) => setBountyAmount(e.target.value)}
                    placeholder="e.g. 5000"
                    className={inputFieldClass()}
                    min={0}
                    step={0.01}
                  />
                </div>
              )}

              {/* Notes */}
              <div>
                <label className="block text-sm font-medium mb-1">Notes (optional)</label>
                <textarea
                  value={closeNotes}
                  onChange={(e) => setCloseNotes(e.target.value)}
                  placeholder="Any additional notes..."
                  rows={3}
                  className={inputFieldClass()}
                />
              </div>

              {/* Error */}
              {closeError && (
                <div className="text-sm text-red-400">{closeError}</div>
              )}
            </div>

            <div className="flex justify-end gap-3 mt-6">
              <button
                onClick={() => setShowCloseModal(false)}
                disabled={closing}
                className="bg-transparent border dark:border-[#27272a] dark:text-[#a1a1aa] light:border-[#e4e4e7] light:text-[#71717a] px-4 py-2 rounded-lg font-medium hover:border-vyper-500 hover:text-vyper-500 transition-all disabled:opacity-50"
              >
                Cancel
              </button>
              <button
                onClick={handleClose}
                disabled={closing}
                className="bg-red-500 text-white px-4 py-2 rounded-lg font-medium hover:bg-red-600 transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
              >
                {closing ? (
                  <>
                    <svg className="w-4 h-4 animate-spin" viewBox="0 0 24 24" fill="none">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                    </svg>
                    Closing...
                  </>
                ) : (
                  'Close Case'
                )}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
