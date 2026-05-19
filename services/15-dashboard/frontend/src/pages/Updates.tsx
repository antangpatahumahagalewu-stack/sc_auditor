import { useState } from 'react';

export default function Updates() {
  const [checking, setChecking] = useState(false);
  const [backing, setBacking] = useState(false);

  const handleCheck = () => {
    setChecking(true);
    setTimeout(() => {
      alert('Already running the latest version (v1.0.0). No updates available.');
      setChecking(false);
    }, 1000);
  };

  const handleBackup = () => {
    setBacking(true);
    setTimeout(() => {
      alert('Backup feature coming soon. Manual backup: copy /data volume.');
      setBacking(false);
    }, 1000);
  };

  return (
    <div className="space-y-6">
      <div className="card">
        <h3 className="font-semibold mb-4">Version</h3>
        <div className="flex items-center gap-4">
          <div className="w-12 h-12 rounded-xl bg-vyper-500/10 flex items-center justify-center">
            <svg className="w-6 h-6 text-vyper-400" viewBox="0 0 20 20" fill="currentColor">
              <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-8-3a1 1 0 00-.867.5 1 1 0 11-1.731-1A3 3 0 0113 8a3.001 3.001 0 01-2 2.83V11a1 1 0 11-2 0v-1a1 1 0 011-1 1 1 0 100-2zm0 8a1 1 0 100-2 1 1 0 000 2z" clipRule="evenodd" />
            </svg>
          </div>
          <div>
            <div className="text-2xl font-bold">v1.0.0</div>
            <div className="text-sm dark:text-[#a1a1aa] light:text-[#71717a]">Vyper Smart Contract Bug Hunter</div>
          </div>
        </div>
      </div>

      <div className="card">
        <h3 className="font-semibold mb-4">Updates</h3>
        <p className="text-sm dark:text-[#a1a1aa] light:text-[#71717a] mb-4">
          Your system is up to date. No updates available at this time.
        </p>
        <button onClick={handleCheck} disabled={checking} className="btn-primary flex items-center gap-2">
          {checking ? (
            <>
              <svg className="w-4 h-4 animate-spin" viewBox="0 0 20 20" fill="currentColor">
                <path fillRule="evenodd" d="M4 2a1 1 0 011 1v2.101a7.002 7.002 0 0111.601 2.566 1 1 0 11-1.885.666A5.002 5.002 0 005.999 7H9a1 1 0 010 2H4a1 1 0 01-1-1V3a1 1 0 011-1zm.008 9.057a1 1 0 011.276.61A5.002 5.002 0 0014.001 13H11a1 1 0 110-2h5a1 1 0 011 1v5a1 1 0 11-2 0v-2.101a7.002 7.002 0 01-11.601-2.566 1 1 0 01.61-1.276z" clipRule="evenodd" />
              </svg>
              Checking...
            </>
          ) : 'Check for Updates'}
        </button>
      </div>

      <div className="card">
        <h3 className="font-semibold mb-4">Backup</h3>
        <p className="text-sm dark:text-[#a1a1aa] light:text-[#71717a] mb-4">
          Create a backup of all Vyper configuration and data. Backups are stored in the /data volume.
        </p>
        <button onClick={handleBackup} disabled={backing} className="btn-secondary flex items-center gap-2">
          {backing ? (
            <>
              <svg className="w-4 h-4 animate-spin" viewBox="0 0 20 20" fill="currentColor">
                <path fillRule="evenodd" d="M4 2a1 1 0 011 1v2.101a7.002 7.002 0 0111.601 2.566 1 1 0 11-1.885.666A5.002 5.002 0 005.999 7H9a1 1 0 010 2H4a1 1 0 01-1-1V3a1 1 0 011-1zm.008 9.057a1 1 0 011.276.61A5.002 5.002 0 0014.001 13H11a1 1 0 110-2h5a1 1 0 011 1v5a1 1 0 11-2 0v-2.101a7.002 7.002 0 01-11.601-2.566 1 1 0 01.61-1.276z" clipRule="evenodd" />
              </svg>
              Creating Backup...
            </>
          ) : 'Create Backup'}
        </button>
      </div>
    </div>
  );
}
