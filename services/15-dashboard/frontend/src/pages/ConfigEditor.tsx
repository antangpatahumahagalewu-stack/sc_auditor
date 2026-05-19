import { useEffect, useState, useCallback } from 'react';
import { api } from '../lib/api';

function statCardClass(): string {
  return 'rounded-xl p-6 dark:bg-[#1a1a1e] dark:border dark:border-[#27272a] light:bg-white light:border light:border-[#e4e4e7] transition-all duration-200';
}

function inputFieldClass(): string {
  return 'w-full px-3 py-2 rounded-lg text-sm outline-none focus:border-vyper-500 focus:shadow-[0_0_0_2px_rgba(108,92,231,0.2)] dark:bg-[#18181b] dark:border dark:border-[#27272a] dark:text-[#f4f4f5] light:bg-white light:border light:border-[#d4d4d8] light:text-[#09090b] transition-all';
}

export default function ConfigEditor() {
  const [config, setConfig] = useState<Record<string, any> | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [editingKey, setEditingKey] = useState<string | null>(null);
  const [editValue, setEditValue] = useState('');
  const [saving, setSaving] = useState(false);
  const [newKey, setNewKey] = useState('');
  const [newValue, setNewValue] = useState('');
  const [showAdd, setShowAdd] = useState(false);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        const res = await api.getConfig();
        if (!cancelled) setConfig(res.data || null);
      } catch (err: any) {
        if (!cancelled) setError(err?.message || 'Failed to fetch config');
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    load();
    return () => { cancelled = true; };
  }, []);

  const handleSave = useCallback(async (key: string) => {
    setSaving(true);
    try {
      let parsed: any = editValue;
      try { parsed = JSON.parse(editValue); } catch {}
      await api.setConfigKey(key, parsed);
      setConfig((prev) => prev ? { ...prev, [key]: parsed } : prev);
      setEditingKey(null);
    } catch (err: any) {
      setError(err?.message || 'Failed to save config key');
    } finally {
      setSaving(false);
    }
  }, [editValue]);

  async function handleAddKey() {
    if (!newKey.trim()) return;
    setSaving(true);
    try {
      let parsed: any = newValue;
      try { parsed = JSON.parse(newValue); } catch {}
      await api.setConfigKey(newKey.trim(), parsed);
      setConfig((prev) => prev ? { ...prev, [newKey.trim()]: parsed } : prev);
      setNewKey('');
      setNewValue('');
      setShowAdd(false);
    } catch (err: any) {
      setError(err?.message || 'Failed to add config key');
    } finally {
      setSaving(false);
    }
  }

  const entries = config ? Object.entries(config) : [];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold">Config Editor</h2>
          <p className="dark:text-[#a1a1aa] light:text-[#71717a] mt-1">
            View and edit Vyper runtime configuration
          </p>
        </div>
        <button
          onClick={() => setShowAdd(!showAdd)}
          className="bg-vyper-500 text-white px-4 py-2 rounded-lg font-medium hover:bg-vyper-600 transition-all text-sm flex items-center gap-2"
        >
          <svg className="w-4 h-4" viewBox="0 0 20 20" fill="currentColor">
            <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm1-11a1 1 0 10-2 0v2H7a1 1 0 100 2h2v2a1 1 0 102 0v-2h2a1 1 0 100-2h-2V7z" clipRule="evenodd" />
          </svg>
          Add Key
        </button>
      </div>

      {error && (
        <div className="rounded-xl p-4 bg-red-500/10 border border-red-500/20 text-red-400 text-sm flex items-center gap-2">
          <svg className="w-4 h-4 flex-shrink-0" viewBox="0 0 20 20" fill="currentColor">
            <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
          </svg>
          <span>{error}</span>
          <button onClick={() => setError('')} className="ml-auto text-red-400/70 hover:text-red-400">✕</button>
        </div>
      )}

      {showAdd && (
        <div className={statCardClass()}>
          <h3 className="font-semibold mb-4">Add New Key</h3>
          <div className="flex gap-3 items-end">
            <div className="flex-1">
              <label className="block text-xs font-medium mb-1 dark:text-[#a1a1aa] light:text-[#71717a]">Key</label>
              <input type="text" className={inputFieldClass()} placeholder="config.key.name" value={newKey} onChange={(e) => setNewKey(e.target.value)} />
            </div>
            <div className="flex-1">
              <label className="block text-xs font-medium mb-1 dark:text-[#a1a1aa] light:text-[#71717a]">Value</label>
              <input type="text" className={inputFieldClass()} placeholder="value" value={newValue} onChange={(e) => setNewValue(e.target.value)} />
            </div>
            <button onClick={handleAddKey} disabled={saving || !newKey.trim()} className="bg-vyper-500 text-white px-4 py-2 rounded-lg font-medium hover:bg-vyper-600 transition-all disabled:opacity-50 text-sm">Add</button>
          </div>
        </div>
      )}

      <div className={statCardClass()}>
        <h3 className="font-semibold mb-4">Configuration Keys ({entries.length})</h3>
        {loading ? (
          <div className="text-center py-8 text-sm dark:text-[#a1a1aa] light:text-[#71717a]">Loading config...</div>
        ) : entries.length === 0 ? (
          <div className="text-center py-8 text-sm dark:text-[#a1a1aa] light:text-[#71717a]">No configuration keys found.</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider dark:bg-[#18181b] dark:text-[#a1a1aa] dark:border-b dark:border-[#27272a] light:bg-[#f4f4f5] light:text-[#71717a] light:border-b light:border-[#e4e4e7]">Key</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider dark:bg-[#18181b] dark:text-[#a1a1aa] dark:border-b dark:border-[#27272a] light:bg-[#f4f4f5] light:text-[#71717a] light:border-b light:border-[#e4e4e7]">Value</th>
                  <th className="px-4 py-3 text-right text-xs font-semibold uppercase tracking-wider dark:bg-[#18181b] dark:text-[#a1a1aa] dark:border-b dark:border-[#27272a] light:bg-[#f4f4f5] light:text-[#71717a] light:border-b light:border-[#e4e4e7]">Actions</th>
                </tr>
              </thead>
              <tbody>
                {entries.map(([key, value]) => (
                  <tr key={key} className="dark:border-b dark:border-[#27272a] light:border-b light:border-[#e4e4e7] hover:dark:bg-vyper-500/5 hover:light:bg-vyper-500/3 transition-colors">
                    <td className="px-4 py-3 text-sm font-mono text-xs dark:text-[#f4f4f5] light:text-[#09090b]">{key}</td>
                    <td className="px-4 py-3 text-sm">
                      {editingKey === key ? (
                        <div className="flex gap-2">
                          <input
                            type="text"
                            className={`${inputFieldClass()} font-mono text-xs flex-1`}
                            value={editValue}
                            onChange={(e) => setEditValue(e.target.value)}
                            onKeyDown={(e) => e.key === 'Enter' && handleSave(key)}
                          />
                          <button onClick={() => handleSave(key)} disabled={saving} className="text-xs text-vyper-400 hover:text-vyper-300 font-medium">Save</button>
                          <button onClick={() => setEditingKey(null)} className="text-xs dark:text-[#a1a1aa] light:text-[#71717a] hover:text-red-400 font-medium">Cancel</button>
                        </div>
                      ) : (
                        <span
                          className="font-mono text-xs cursor-pointer hover:text-vyper-400 transition-colors"
                          onClick={() => { setEditingKey(key); setEditValue(typeof value === 'string' ? value : JSON.stringify(value, null, 2)); }}
                          title="Click to edit"
                        >
                          {typeof value === 'string' ? value : JSON.stringify(value).slice(0, 60)}{typeof value === 'object' && JSON.stringify(value).length > 60 ? '...' : ''}
                        </span>
                      )}
                    </td>
                    <td className="px-4 py-3 text-right">
                      {editingKey !== key && (
                        <button
                          onClick={() => { setEditingKey(key); setEditValue(typeof value === 'string' ? value : JSON.stringify(value, null, 2)); }}
                          className="text-xs text-vyper-400 hover:text-vyper-300 font-medium"
                        >
                          Edit
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
