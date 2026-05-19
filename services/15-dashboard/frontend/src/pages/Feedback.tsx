// FILE: Feedback.tsx
import { useState, useEffect } from 'react';
import { api } from '../lib/api';

interface FeedbackItem {
  finding_id?: string;
  original_classification?: string;
  user_feedback?: string;
  feedback?: string;
  status?: string;
  created_at?: string;
  [key: string]: any;
}

function statusBadge(status?: string) {
  const base = 'inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium';
  const colors: Record<string, string> = {
    confirmed: 'bg-green-500/10 text-green-400 dark:text-green-400 light:text-green-600',
    disputed: 'bg-red-500/10 text-red-400 dark:text-red-400 light:text-red-600',
    pending: 'bg-yellow-500/10 text-yellow-400 dark:text-yellow-400 light:text-yellow-600',
    acknowledged: 'bg-blue-500/10 text-blue-400 dark:text-blue-400 light:text-blue-600',
    dismissed: 'bg-gray-500/10 text-gray-400 dark:text-gray-400 light:text-gray-600',
  };
  return `${base} ${colors[status?.toLowerCase() || ''] || 'bg-gray-500/10 text-gray-400'}`;
}

function formatDate(dateStr?: string): string {
  if (!dateStr) return '—';
  try {
    return new Date(dateStr).toLocaleDateString('en-US', {
      year: 'numeric', month: 'short', day: 'numeric',
    });
  } catch {
    return dateStr;
  }
}

function ExpandingRow({
  item,
  isOpen,
  onToggle,
}: {
  item: FeedbackItem;
  isOpen: boolean;
  onToggle: () => void;
}) {
  return (
    <>
      <tr
        onClick={onToggle}
        className="cursor-pointer dark:hover:bg-[#18181b] light:hover:bg-[#f4f4f5] transition-colors"
      >
        <td className="px-4 py-3 font-mono text-xs dark:text-[#f4f4f5] light:text-[#09090b]">
          {item.finding_id ? item.finding_id.slice(0, 12) : '—'}
        </td>
        <td className="px-4 py-3 dark:text-[#f4f4f5] light:text-[#09090b]">
          {item.original_classification || '—'}
        </td>
        <td className="px-4 py-3 dark:text-[#a1a1aa] light:text-[#71717a] max-w-xs truncate">
          {item.user_feedback || item.feedback || '—'}
        </td>
        <td className="px-4 py-3">
          <span className={statusBadge(item.status)}>{item.status || 'unknown'}</span>
        </td>
        <td className="px-4 py-3 text-xs dark:text-[#a1a1aa] light:text-[#71717a] whitespace-nowrap">
          {formatDate(item.created_at)}
        </td>
        <td className="px-4 py-3 text-right">
          <svg
            className={`w-4 h-4 inline-block dark:text-[#a1a1aa] light:text-[#71717a] transition-transform ${
              isOpen ? 'rotate-180' : ''
            }`}
            viewBox="0 0 20 20"
            fill="currentColor"
          >
            <path fillRule="evenodd" d="M5.293 7.293a1 1 0 011.414 0L10 10.586l3.293-3.293a1 1 0 111.414 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 010-1.414z" clipRule="evenodd" />
          </svg>
        </td>
      </tr>
      {isOpen && (
        <tr className="dark:bg-[#18181b]/50 light:bg-[#f4f4f5]/50">
          <td colSpan={6} className="px-4 py-4">
            <div className="space-y-3 text-sm">
              <div>
                <span className="text-xs dark:text-[#a1a1aa] light:text-[#71717a]">Finding ID</span>
                <p className="font-mono text-xs dark:text-[#f4f4f5] light:text-[#09090b] break-all mt-0.5">
                  {item.finding_id || '—'}
                </p>
              </div>
              <div>
                <span className="text-xs dark:text-[#a1a1aa] light:text-[#71717a]">Original Classification</span>
                <p className="dark:text-[#f4f4f5] light:text-[#09090b] mt-0.5">{item.original_classification || '—'}</p>
              </div>
              <div>
                <span className="text-xs dark:text-[#a1a1aa] light:text-[#71717a]">User Feedback</span>
                <p className="dark:text-[#f4f4f5] light:text-[#09090b] mt-0.5 whitespace-pre-wrap">
                  {item.user_feedback || item.feedback || '—'}
                </p>
              </div>
              <div>
                <span className="text-xs dark:text-[#a1a1aa] light:text-[#71717a]">Status</span>
                <p className="mt-0.5">
                  <span className={statusBadge(item.status)}>{item.status || 'unknown'}</span>
                </p>
              </div>
              {/* Render extra fields */}
              {Object.entries(item)
                .filter(
                  ([key]) =>
                    !['finding_id', 'original_classification', 'user_feedback', 'feedback', 'status', 'created_at'].includes(key),
                )
                .map(([key, value]) => (
                  <div key={key}>
                    <span className="text-xs dark:text-[#a1a1aa] light:text-[#71717a] capitalize">
                      {key.replace(/_/g, ' ')}
                    </span>
                    <p className="dark:text-[#f4f4f5] light:text-[#09090b] mt-0.5">
                      {typeof value === 'object' ? JSON.stringify(value) : String(value)}
                    </p>
                  </div>
                ))}
            </div>
          </td>
        </tr>
      )}
    </>
  );
}

export default function Feedback() {
  const [items, setItems] = useState<FeedbackItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [expandedRow, setExpandedRow] = useState<number | null>(null);

  useEffect(() => {
    setLoading(true);
    setError(null);
    api
      .getFeedback()
      .then((res) => {
        setItems(Array.isArray(res.data) ? res.data : []);
      })
      .catch((err) => {
        setError(err instanceof Error ? err.message : 'Failed to load feedback');
        setItems([]);
      })
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center py-24">
        <div className="flex items-center gap-3 text-sm dark:text-[#a1a1aa] light:text-[#71717a]">
          <svg className="animate-spin h-5 w-5 text-vyper-400" viewBox="0 0 24 24" fill="none">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
          </svg>
          Loading feedback...
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="rounded-lg border dark:border-red-500/30 light:border-red-500/30 bg-red-500/5 px-4 py-3 text-sm text-red-400 dark:text-red-400 light:text-red-600">
        {error}
      </div>
    );
  }

  if (items.length === 0) {
    return (
      <div className="space-y-4">
        <h2 className="text-lg font-semibold dark:text-[#f4f4f5] light:text-[#09090b]">Feedback</h2>
        <div className="flex flex-col items-center justify-center py-16 text-sm dark:text-[#a1a1aa] light:text-[#71717a]">
          <svg className="w-12 h-12 mb-3 opacity-40" viewBox="0 0 20 20" fill="currentColor">
            <path fillRule="evenodd" d="M18 13V5a2 2 0 00-2-2H4a2 2 0 00-2 2v8a2 2 0 002 2h3l3 3 3-3h3a2 2 0 002-2zM5 7a1 1 0 011-1h8a1 1 0 110 2H6a1 1 0 01-1-1zm1 3a1 1 0 100 2h4a1 1 0 100-2H6z" clipRule="evenodd" />
          </svg>
          No feedback submitted yet.
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <h2 className="text-lg font-semibold dark:text-[#f4f4f5] light:text-[#09090b]">
        Feedback ({items.length})
      </h2>

      <div className="overflow-x-auto rounded-lg border dark:border-[#27272a] light:border-[#e4e4e7]">
        <table className="w-full text-sm">
          <thead className="dark:bg-[#18181b] light:bg-[#f4f4f5]">
            <tr>
              <th className="text-left px-4 py-3 font-medium dark:text-[#a1a1aa] light:text-[#71717a]">Finding ID</th>
              <th className="text-left px-4 py-3 font-medium dark:text-[#a1a1aa] light:text-[#71717a]">Classification</th>
              <th className="text-left px-4 py-3 font-medium dark:text-[#a1a1aa] light:text-[#71717a]">Feedback</th>
              <th className="text-left px-4 py-3 font-medium dark:text-[#a1a1aa] light:text-[#71717a]">Status</th>
              <th className="text-left px-4 py-3 font-medium dark:text-[#a1a1aa] light:text-[#71717a]">Date</th>
              <th className="px-4 py-3" />
            </tr>
          </thead>
          <tbody className="divide-y dark:divide-[#27272a] light:divide-[#e4e4e7]">
            {items.map((item, idx) => (
              <ExpandingRow
                key={item.finding_id || idx}
                item={item}
                isOpen={expandedRow === idx}
                onToggle={() => setExpandedRow(expandedRow === idx ? null : idx)}
              />
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
