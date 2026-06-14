import { useState } from 'react';
import { api, type BackupSummary } from '../lib/api';
import { FilesModule } from './modules/FilesModule';
import { WhatsAppModule } from './modules/WhatsAppModule';
import { MessagesModule } from './modules/MessagesModule';
import { PeopleModule } from './modules/PeopleModule';
import { PhotosTab } from './modules/PhotosTab';
import { NotesTab } from './modules/NotesTab';
import { CalendarTab } from './modules/CalendarTab';
import { ContactsTab } from './modules/ContactsTab';
import { CallsTab } from './modules/CallsTab';
import { SafariTab } from './modules/SafariTab';
import { LocationsTab } from './modules/LocationsTab';
import { VoicemailTab } from './modules/VoicemailTab';
import { TimelineTab } from './modules/TimelineTab';
import { SearchTab, type SearchNavTarget } from './modules/SearchTab';
import { ErrorBoundary } from '../components/ErrorBoundary';
import '../styles/Explorer.css';

interface ExplorerProps {
  apiToken: string;
  backup: BackupSummary;
  sessionToken?: string;
  onSessionToken?: (token: string) => void;
}

type ModuleView =
  | 'files'
  | 'people'
  | 'whatsapp'
  | 'messages'
  | 'photos'
  | 'notes'
  | 'calendar'
  | 'contacts'
  | 'calls'
  | 'safari'
  | 'locations'
  | 'voicemail'
  | 'timeline'
  | 'search';

const MODULES: { id: ModuleView; label: string; description: string }[] = [
  { id: 'search', label: 'Search', description: 'Search across all artifacts' },
  { id: 'people', label: 'People', description: 'Everything tied to a person' },
  { id: 'timeline', label: 'Timeline', description: 'Chronological activity' },
  { id: 'files', label: 'Manifest', description: 'Browse manifest entries' },
  { id: 'whatsapp', label: 'WhatsApp', description: 'Explore chats and messages' },
  { id: 'messages', label: 'Messages', description: 'iMessage/SMS conversations' },
  { id: 'photos', label: 'Photos', description: 'Photos timeline' },
  { id: 'notes', label: 'Notes', description: 'Notes database' },
  { id: 'calendar', label: 'Calendar', description: 'Calendar events' },
  { id: 'contacts', label: 'Contacts', description: 'Address book entries' },
  { id: 'calls', label: 'Calls', description: 'Call history' },
  { id: 'safari', label: 'Safari', description: 'Browsing history' },
  { id: 'locations', label: 'Locations', description: 'Significant locations' },
  { id: 'voicemail', label: 'Voicemail', description: 'Voicemail messages' },
];

export function Explorer({ apiToken, backup, sessionToken, onSessionToken }: ExplorerProps) {
  const [activeModule, setActiveModule] = useState<ModuleView>('files');
  const [pendingChatGuid, setPendingChatGuid] = useState<string | undefined>(undefined);
  const [pendingConversationGuid, setPendingConversationGuid] = useState<string | undefined>(undefined);
  const [pendingPersonKey, setPendingPersonKey] = useState<string | undefined>(undefined);
  const [error, setError] = useState<string | null>(null);

  const goToModule = (module: ModuleView) => {
    setPendingChatGuid(undefined);
    setPendingConversationGuid(undefined);
    setPendingPersonKey(undefined);
    setActiveModule(module);
  };

  // Search results and the People "View conversation" jump both land here:
  // open a WhatsApp/Messages thread and clear any pending person selection.
  const handleSearchNavigate = (target: SearchNavTarget) => {
    setPendingChatGuid(target.chatGuid);
    setPendingConversationGuid(target.conversationGuid);
    setPendingPersonKey(undefined);
    setActiveModule(target.module as ModuleView);
  };

  // Reverse jump: clicking a sender inside a conversation opens that person.
  const handleOpenPerson = (personKey: string) => {
    setPendingChatGuid(undefined);
    setPendingConversationGuid(undefined);
    setPendingPersonKey(personKey);
    setActiveModule('people');
  };

  const handleDownloadReport = async () => {
    setError(null);
    try {
      const response = await api.downloadReport(backup.id, apiToken);
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `report-${backup.id}.pdf`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Report failed');
    }
  };

  return (
    <div className="explorer">
      <div className="explorer-header">
        <div className="backup-info-card">
          <div className="backup-title-line">
            <h2>{backup.display_name}</h2>
            {backup.device_name && <span className="device-name">{backup.device_name}</span>}
            {backup.product_version && <span className="product-version">{backup.product_version}</span>}
            <button className="download-btn" onClick={handleDownloadReport} style={{ marginLeft: 'auto' }}>
              PDF report
            </button>
          </div>
          <div className="backup-metadata">
            <div className="metadata-item">
              <span className="metadata-label">Backup ID:</span>
              <span className="metadata-value">{backup.id}</span>
            </div>
            {backup.size_bytes && (
              <div className="metadata-item">
                <span className="metadata-label">Size:</span>
                <span className="metadata-value">{(backup.size_bytes / (1024 * 1024 * 1024)).toFixed(2)} GB</span>
              </div>
            )}
            {backup.last_modified_at && (
              <div className="metadata-item">
                <span className="metadata-label">Created:</span>
                <span className="metadata-value">{new Date(backup.last_modified_at).toLocaleString()}</span>
              </div>
            )}
            {backup.decrypted_at && (
              <div className="metadata-item">
                <span className="metadata-label">Decrypted:</span>
                <span className="metadata-value">{new Date(backup.decrypted_at).toLocaleString()}</span>
              </div>
            )}
          </div>
          {error && <div className="error-message">{error}</div>}
        </div>
      </div>

      <div className="explorer-content">
        <div className="module-selector">
          <div className="module-tabs">
            {MODULES.map((module) => (
              <button
                key={module.id}
                className={`module-tab ${activeModule === module.id ? 'active' : ''}`}
                onClick={() => goToModule(module.id)}
              >
                <span className="module-label">{module.label}</span>
                <span className="module-description">{module.description}</span>
              </button>
            ))}
          </div>
        </div>

        <div className="module-content">
          <ErrorBoundary resetKey={activeModule} label={MODULES.find((m) => m.id === activeModule)?.label}>
          {activeModule === 'files' && <FilesModule apiToken={apiToken} backupId={backup.id} />}

          {activeModule === 'people' && (
            <PeopleModule
              apiToken={apiToken}
              backupId={backup.id}
              initialSelectedKey={pendingPersonKey}
              onOpenThread={handleSearchNavigate}
            />
          )}

          {activeModule === 'whatsapp' && (
            <WhatsAppModule
              apiToken={apiToken}
              backup={backup}
              sessionToken={sessionToken}
              onSessionToken={onSessionToken}
              initialSelectedGuid={pendingChatGuid}
              onOpenPerson={handleOpenPerson}
            />
          )}

          {activeModule === 'messages' && (
            <MessagesModule
              apiToken={apiToken}
              backup={backup}
              sessionToken={sessionToken}
              onSessionToken={onSessionToken}
              initialSelectedGuid={pendingConversationGuid}
              onOpenPerson={handleOpenPerson}
            />
          )}

          {activeModule === 'photos' && (
            <PhotosTab apiToken={apiToken} backupId={backup.id} sessionToken={sessionToken} />
          )}

          {activeModule === 'notes' && <NotesTab apiToken={apiToken} backupId={backup.id} />}

          {activeModule === 'calendar' && <CalendarTab apiToken={apiToken} backupId={backup.id} />}

          {activeModule === 'contacts' && <ContactsTab apiToken={apiToken} backupId={backup.id} />}

          {activeModule === 'calls' && <CallsTab apiToken={apiToken} backupId={backup.id} />}

          {activeModule === 'safari' && <SafariTab apiToken={apiToken} backupId={backup.id} />}

          {activeModule === 'locations' && <LocationsTab apiToken={apiToken} backupId={backup.id} />}

          {activeModule === 'voicemail' && <VoicemailTab apiToken={apiToken} backupId={backup.id} />}

          {activeModule === 'timeline' && <TimelineTab apiToken={apiToken} backupId={backup.id} />}

          {activeModule === 'search' && (
            <SearchTab apiToken={apiToken} backupId={backup.id} onNavigate={handleSearchNavigate} />
          )}
          </ErrorBoundary>
        </div>
      </div>
    </div>
  );
}
