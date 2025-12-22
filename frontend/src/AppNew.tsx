import { useEffect, useState } from 'react';
import { useLocalStorage } from './lib/useLocalStorage';
import { BackupSelector } from './pages/BackupSelector';
import { PasswordPrompt } from './pages/PasswordPrompt';
import { Explorer } from './pages/Explorer';
import type { BackupSummary } from './lib/api';
import './AppNew.css';

type AppState = 'token-input' | 'backup-selector' | 'password-prompt' | 'explorer';

const rainbowColors = ['#5EBD3E', '#FFB900', '#F78200', '#E23838', '#973999', '#009CDF'];

function RainbowText({ text }: { text: string }) {
  return (
    <span className="rainbow-text">
      {text.split('').map((char, index) => (
        <span key={index} style={{ color: rainbowColors[index % rainbowColors.length] }}>
          {char}
        </span>
      ))}
    </span>
  );
}

function Breadcrumbs({ currentState, onNavigate }: { currentState: AppState; onNavigate: (state: AppState) => void }) {
  const steps = [
    { state: 'backup-selector', label: 'Select Backup' },
    { state: 'password-prompt', label: 'Decrypt Backup' },
    { state: 'explorer', label: 'Explore' },
  ];

  return (
    <div className="breadcrumbs">
      {steps.map((step) => (
        <button
          key={step.state}
          className={`breadcrumb-label ${currentState === step.state ? 'active' : ''}`}
          onClick={() => onNavigate(step.state as AppState)}
        >
          {step.label}
        </button>
      ))}
    </div>
  );
}

function AppNew() {
  const [apiToken, setApiToken] = useLocalStorage<string>('ibe.apiToken', '');
  const [appState, setAppState] = useState<AppState>('token-input');
  const [selectedBackup, setSelectedBackup] = useState<BackupSummary | null>(null);
  const [tokenInput, setTokenInput] = useState(apiToken);

  useEffect(() => {
    if (apiToken) {
      setAppState('backup-selector');
    }
  }, [apiToken]);

  const handleTokenSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (tokenInput.trim()) {
      setApiToken(tokenInput);
      setAppState('backup-selector');
    }
  };

  const handleBackupSelected = (backup: BackupSummary) => {
    setSelectedBackup(backup);
    if (backup.decryption_status === 'decrypted') {
      setAppState('explorer');
    } else {
      setAppState('password-prompt');
    }
  };

  const handleDecryptComplete = () => {
    setAppState('explorer');
  };

  const handleBack = () => {
    setAppState('backup-selector');
    setSelectedBackup(null);
  };

  const handleLogout = () => {
    setApiToken('');
    setTokenInput('');
    setAppState('token-input');
    setSelectedBackup(null);
  };

  const handleNavigate = (state: AppState) => {
    if (state === 'backup-selector') {
      setAppState('backup-selector');
      setSelectedBackup(null);
    } else if (state === 'password-prompt' && selectedBackup) {
      setAppState('password-prompt');
    } else if (state === 'explorer' && selectedBackup) {
      setAppState('explorer');
    }
  };

  return (
    <div className="app-new">
      {appState === 'token-input' && (
        <div className="token-input-page">
          <div className="token-input-container">
            <h1>Apple Juicer</h1>
            <p>Enter your API token to continue</p>
            <form onSubmit={handleTokenSubmit}>
              <input
                type="password"
                placeholder="API Token"
                value={tokenInput}
                onChange={(e) => setTokenInput(e.target.value)}
                autoFocus
              />
              <button type="submit">Connect</button>
            </form>
          </div>
        </div>
      )}

      {(appState === 'backup-selector' || appState === 'password-prompt' || appState === 'explorer') && (
        <div className="app-header">
          <div className="header-left">
            <div className="app-icon">📱</div>
            <RainbowText text="iOS Backup Explorer" />
          </div>
          <div className="header-right">
            <Breadcrumbs currentState={appState} onNavigate={handleNavigate} />
            <button className="logout-btn" onClick={handleLogout}>
              Logout
            </button>
          </div>
        </div>
      )}

      {appState === 'backup-selector' && (
        <div className="app-page">
          <BackupSelector apiToken={apiToken} onBackupSelected={handleBackupSelected} />
        </div>
      )}

      {appState === 'password-prompt' && selectedBackup && (
        <PasswordPrompt
          apiToken={apiToken}
          backup={selectedBackup}
          onDecryptComplete={handleDecryptComplete}
          onCancel={handleBack}
        />
      )}

      {appState === 'explorer' && selectedBackup && (
        <div className="app-page">
          <Explorer apiToken={apiToken} backup={selectedBackup} />
        </div>
      )}
    </div>
  );
}

export default AppNew;
