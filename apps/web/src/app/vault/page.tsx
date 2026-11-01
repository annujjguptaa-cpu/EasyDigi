'use client';

import React, { useState } from 'react';
import {
  Banner,
  Section,
  Panel,
  Button,
  StatusDot,
  DocumentRow,
} from '@/ui';

export default function VaultPage() {
  const [activeTab, setActiveTab] = useState<'Identity' | 'Income' | 'Property' | 'Photo' | 'Signature' | 'Other'>('Identity');
  const [passphrase, setPassphrase] = useState('');
  const [isUnlocked, setIsUnlocked] = useState(false);
  const [statusMsg, setStatusMsg] = useState('');

  const vaultFiles = [
    {
      id: 'VLT-01',
      docType: 'Permanent Account Number (PAN)',
      category: 'Identity' as const,
      maskedFields: { pan: 'ABXXXXXXXF', name: 'Rahul Verma' },
      status: 'verified' as const,
      source: 'DigiLocker' as const,
    },
    {
      id: 'VLT-02',
      docType: 'Offline Aadhaar XML',
      category: 'Identity' as const,
      maskedFields: { id_last4: '4321', name: 'Rahul Verma' },
      status: 'verified' as const,
      source: 'DigiLocker' as const,
    },
    {
      id: 'VLT-03',
      docType: 'Q3 Salary Statement',
      category: 'Income' as const,
      maskedFields: { employer: 'Apex Cloud Systems', net_pay: '85,000' },
      status: 'verified' as const,
      source: 'Upload' as const,
    },
    {
      id: 'VLT-04',
      docType: 'Passport Size Photograph',
      category: 'Photo' as const,
      maskedFields: { format: 'JPEG', dimensions: '35x45mm' },
      status: 'verified' as const,
      source: 'Camera' as const,
    },
    {
      id: 'VLT-05',
      docType: 'Customer Signature Specimen',
      category: 'Signature' as const,
      maskedFields: { format: 'PNG', background: 'White Clean' },
      status: 'verified' as const,
      source: 'Upload' as const,
    },
  ];

  const handleUnlock = (e: React.FormEvent) => {
    e.preventDefault();
    if (passphrase.length >= 6) {
      setIsUnlocked(true);
      setStatusMsg('Device Vault Decrypted locally using Web Crypto PBKDF2 + AES-GCM.');
    } else {
      setStatusMsg('Passphrase must be at least 6 characters.');
    }
  };

  const handleExportBackup = () => {
    setStatusMsg('Authenticated encrypted backup export generated (.zip format).');
  };

  return (
    <div className="min-h-screen bg-paper flex flex-col items-center">
      <Banner type="demo" />

      <main className="max-w-4xl w-full p-4 sm:p-6 space-y-6">
        <header className="border-b border-hairline pb-4 flex flex-wrap items-center justify-between gap-4">
          <div>
            <span className="font-mono text-xs text-ink-muted uppercase tracking-widest block">
              CLIENT-SIDE ENCRYPTED STORAGE
            </span>
            <h1 className="font-serif text-2xl text-ink font-normal">Personal Device Vault</h1>
            <p className="text-xs text-ink-muted mt-1 font-sans">
              All documents are stored exclusively on this device. Nothing is stored unencrypted on servers.
            </p>
          </div>
          <div className="flex gap-2">
            <Button variant="secondary" onClick={handleExportBackup}>
              EXPORT ENCRYPTED BACKUP
            </Button>
          </div>
        </header>

        {!isUnlocked ? (
          <Panel caption="DEVICE VAULT SECURITY CHECK">
            <form onSubmit={handleUnlock} className="max-w-md space-y-4">
              <p className="font-sans text-sm text-ink">
                Enter your vault passphrase or use your WebAuthn device passkey to decrypt your local files:
              </p>
              <div>
                <label className="block font-mono text-xs text-ink-muted uppercase mb-1">
                  VAULT PASSPHRASE
                </label>
                <input
                  type="password"
                  value={passphrase}
                  onChange={(e) => setPassphrase(e.target.value)}
                  placeholder="Enter 6+ character passphrase"
                  className="w-full px-4 py-2.5 border border-hairline bg-surface text-ink text-sm rounded-[2px] focus:outline-none focus:ring-2 focus:ring-ink"
                />
              </div>
              <div className="p-3 bg-amber-50 border border-amber-200 text-amber-900 text-xs rounded-[2px]">
                <strong>Notice:</strong> DocFlow does not store passwords, PINs, or master keys. If you lose your passphrase, files cannot be recovered.
              </div>
              <Button type="submit" variant="primary" className="w-full">
                UNLOCK MY VAULT
              </Button>
            </form>
          </Panel>
        ) : (
          <div className="space-y-6">
            {/* Category Navigation */}
            <div className="flex gap-2 overflow-x-auto pb-1 border-b border-hairline">
              {(['Identity', 'Income', 'Property', 'Photo', 'Signature', 'Other'] as const).map((cat) => (
                <button
                  key={cat}
                  onClick={() => setActiveTab(cat)}
                  className={`font-mono text-xs px-3 py-1.5 rounded-[2px] border transition whitespace-nowrap ${
                    activeTab === cat
                      ? 'border-ink bg-ink text-paper font-semibold'
                      : 'border-hairline bg-surface text-ink-muted hover:text-ink'
                  }`}
                >
                  {cat.toUpperCase()}
                </button>
              ))}
            </div>

            {/* Document List in Vault */}
            <Section
              index="01"
              title={`${activeTab} Documents`}
              caption="Encrypted with unique AES-GCM IV per file"
            >
              <div className="border border-hairline bg-surface rounded-[2px] divide-y divide-hairline">
                {vaultFiles
                  .filter((f) => f.category === activeTab)
                  .map((doc) => (
                    <DocumentRow
                      key={doc.id}
                      id={doc.id}
                      docType={doc.docType}
                      maskedFields={doc.maskedFields}
                      status={doc.status}
                      source={doc.source}
                      action={
                        <button className="font-mono text-xs underline text-status-error hover:opacity-80 ml-2">
                          DELETE
                        </button>
                      }
                    />
                  ))}
              </div>
            </Section>

            {/* Save to DigiLocker Guide Panel */}
            <Panel caption="MANUAL SYNC GUIDE (DIGILOCKER COMPLIANCE)">
              <div className="space-y-2 text-xs font-sans text-ink leading-relaxed">
                <p>
                  <strong>How to upload copies to your official DigiLocker:</strong>
                </p>
                <ol className="list-decimal list-inside space-y-1 text-ink-muted">
                  <li>Download your verified copies from the vault.</li>
                  <li>
                    Open the official{' '}
                    <a
                      href="https://digilocker.gov.in"
                      target="_blank"
                      rel="noreferrer"
                      className="underline text-status-verified font-medium"
                    >
                      DigiLocker Portal
                    </a>.
                  </li>
                  <li>Navigate to <em>Drive → Uploaded Documents</em> to store your self-uploaded backup.</li>
                </ol>
                <p className="font-mono text-[11px] text-ink-muted mt-2 border-t border-hairline pt-2">
                  * Note: Under UIDAI & MeitY regulations, third-party apps cannot write directly into your DigiLocker drive.
                </p>
              </div>
            </Panel>
          </div>
        )}
      </main>
    </div>
  );
}
