import { useEffect, useState } from 'react';
import { useLocalStorage } from './lib/useLocalStorage';
import { BackupSelector } from './pages/BackupSelector';
import { PasswordPrompt } from './pages/PasswordPrompt';
import { Explorer } from './pages/Explorer';
import { api, type BackupSummary } from './lib/api';
import appLogo from './assets/logo.svg';
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
  const [backupSessions, setBackupSessions] = useLocalStorage<Record<string, string>>('ibe.backupSessions', {});
  const [appState, setAppState] = useState<AppState>('token-input');
  const [selectedBackup, setSelectedBackup] = useState<BackupSummary | null>(null);
  const [tokenInput, setTokenInput] = useState(apiToken);
  const [refreshTick, setRefreshTick] = useState(0);
  const [decryptMessage, setDecryptMessage] = useState<string | null>(null);
  const [decryptingBackupId, setDecryptingBackupId] = useState<string | null>(null);

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
    setDecryptMessage(null);
    setSelectedBackup(backup);
    if (backup.decryption_status === 'decrypted') {
      setAppState('explorer');
    } else {
      setAppState('password-prompt');
    }
  };

  const handleBack = () => {
    setAppState('backup-selector');
    setSelectedBackup(null);
    setDecryptMessage(null);
    setDecryptingBackupId(null);
  };

  const handleLogout = () => {
    setApiToken('');
    setTokenInput('');
    setAppState('token-input');
    setSelectedBackup(null);
    setBackupSessions({});
  };

  const handleSessionToken = (token: string) => {
    if (!selectedBackup) return;
    setBackupSessions({
      ...backupSessions,
      [selectedBackup.id]: token,
    });
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

  const handlePasswordSubmit = async (password: string) => {
    if (!selectedBackup || !apiToken) return;
    setAppState('backup-selector');
    setDecryptMessage('Decrypting backup…');
    setDecryptingBackupId(selectedBackup.id);
    try {
      const response = await api.decryptBackup(selectedBackup.id, password, apiToken);
      if (response.decryption_status === 'decrypted') {
        try {
          const unlock = await api.unlockBackup(selectedBackup.id, password, apiToken);
          handleSessionToken(unlock.session_token);
        } catch {
          // ignore unlock errors
        }
        setDecryptMessage(null);
        setDecryptingBackupId(null);
        setAppState('explorer');
      } else if (response.decryption_status === 'failed') {
        setDecryptMessage(response.error || 'Decryption failed. Please try again.');
        setDecryptingBackupId(null);
      } else {
        setDecryptMessage('Decrypting backup…');
      }
    } catch (err) {
      setDecryptMessage(err instanceof Error ? err.message : 'Decryption failed');
      setDecryptingBackupId(null);
    } finally {
      setRefreshTick((tick) => tick + 1);
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
            <div className="app-icon">
              <img src={appLogo} alt="Apple Juicer logo" />
            </div>
            <RainbowText text="apple-juicer" />
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
          <BackupSelector
            apiToken={apiToken}
            onBackupSelected={handleBackupSelected}
            refreshTrigger={refreshTick}
            externalMessage={decryptMessage}
            decryptingBackupId={decryptingBackupId}
          />
        </div>
      )}

      {appState === 'password-prompt' && selectedBackup && (
        <PasswordPrompt
          backup={selectedBackup}
          onSubmitPassword={handlePasswordSubmit}
          onCancel={handleBack}
        />
      )}

      {appState === 'explorer' && selectedBackup && (
        <div className="app-page">
          <Explorer
            apiToken={apiToken}
            backup={selectedBackup}
            sessionToken={backupSessions[selectedBackup.id]}
            onSessionToken={handleSessionToken}
          />
        </div>
      )}
    </div>
  );
}

export default AppNew;
