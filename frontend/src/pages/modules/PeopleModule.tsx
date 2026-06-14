import { useCallback, useEffect, useMemo, useState } from 'react';
import { api, type PersonDetail, type PersonSummary } from '../../lib/api';
import type { SearchNavTarget } from './SearchTab';
import '../../styles/ArtifactTabs.css';

const EVENT_ICONS: Record<string, string> = {
  call: '📞',
  voicemail: '📭',
};

function countLabel(p: PersonSummary): string {
  const parts: string[] = [];
  if (p.whatsapp_count) parts.push(`${p.whatsapp_count} WhatsApp`);
  if (p.message_count) parts.push(`${p.message_count} iMessage`);
  if (p.call_count) parts.push(`${p.call_count} call${p.call_count === 1 ? '' : 's'}`);
  if (p.voicemail_count) parts.push(`${p.voicemail_count} voicemail${p.voicemail_count === 1 ? '' : 's'}`);
  return parts.join(' · ');
}

interface Props {
  apiToken: string;
  backupId: string;
  initialSelectedKey?: string;
  onOpenThread?: (target: SearchNavTarget) => void;
}

export function PeopleModule({ apiToken, backupId, initialSelectedKey, onOpenThread }: Props) {
  const [people, setPeople] = useState<PersonSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedKey, setSelectedKey] = useState<string | null>(initialSelectedKey ?? null);
  const [search, setSearch] = useState('');
  const [detail, setDetail] = useState<PersonDetail | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [detailError, setDetailError] = useState<string | null>(null);

  useEffect(() => {
    if (initialSelectedKey) setSelectedKey(initialSelectedKey);
  }, [initialSelectedKey]);

  useEffect(() => {
    let mounted = true;
    setLoading(true);
    setError(null);
    api
      .listPeople(backupId, apiToken)
      .then((res) => {
        if (!mounted) return;
        setPeople(res.items);
        setSelectedKey((current) => current ?? (res.items[0]?.key ?? null));
        setLoading(false);
      })
      .catch((e) => {
        if (!mounted) return;
        setError(e instanceof Error ? e.message : 'Failed to load people');
        setLoading(false);
      });
    return () => {
      mounted = false;
    };
  }, [backupId, apiToken]);

  const loadDetail = useCallback(
    (key: string) => {
      setDetailLoading(true);
      setDetailError(null);
      api
        .getPerson(backupId, key, apiToken)
        .then((res) => {
          setDetail(res);
          setDetailLoading(false);
        })
        .catch((e) => {
          setDetail(null);
          setDetailError(e instanceof Error ? e.message : 'Could not load this person.');
          setDetailLoading(false);
        });
    },
    [backupId, apiToken],
  );

  useEffect(() => {
    if (selectedKey) loadDetail(selectedKey);
  }, [selectedKey, loadDetail]);

  const filtered = useMemo(() => {
    const term = search.trim().toLowerCase();
    if (!term) return people;
    return people.filter(
      (p) => p.display_name.toLowerCase().includes(term) || p.identifiers.some((id) => id.toLowerCase().includes(term)),
    );
  }, [people, search]);

  const selected = useMemo(() => people.find((p) => p.key === selectedKey) || null, [people, selectedKey]);

  return (
    <div className="whatsapp-module">
      <div className="whatsapp-container">
        <div className="whatsapp-chats-list">
          <div className="whatsapp-header">
            <h3>People</h3>
          </div>
          <div style={{ marginBottom: '1rem' }}>
            <input
              type="text"
              placeholder="Search people…"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="search-input"
            />
          </div>
          {loading ? (
            <div className="loading">Loading people…</div>
          ) : error ? (
            <div className="error-message">{error}</div>
          ) : people.length === 0 ? (
            <div className="no-results">No correlated people found in this backup.</div>
          ) : (
            <div className="chats-list scrollable">
              {filtered.map((p) => (
                <button
                  key={p.key}
                  className={`chat-item ${selectedKey === p.key ? 'active' : ''}`}
                  onClick={() => setSelectedKey(p.key)}
                >
                  <div className="chat-title">
                    {p.display_name}
                    {p.is_contact && <span title="In contacts"> ⭐</span>}
                  </div>
                  <div className="chat-subtitle">{countLabel(p) || `${p.total_events} events`}</div>
                  {p.last_activity_at && (
                    <div className="chat-date">{new Date(p.last_activity_at).toLocaleDateString()}</div>
                  )}
                </button>
              ))}
            </div>
          )}
        </div>

        <div className="whatsapp-messages">
          {!selected ? (
            selectedKey ? (
              <div className="error-message">Could not open this person — they have no correlated activity.</div>
            ) : (
              <div className="no-results">Select a person to view their activity</div>
            )
          ) : (
            <>
              <div className="whatsapp-header">
                <h3>{selected.display_name}</h3>
                <div style={{ display: 'flex', gap: '0.5rem' }}>
                  {detail?.whatsapp_chat_guid && (
                    <button
                      className="download-btn"
                      onClick={() => onOpenThread?.({ module: 'whatsapp', chatGuid: detail.whatsapp_chat_guid ?? undefined })}
                    >
                      View WhatsApp chat
                    </button>
                  )}
                  {detail?.conversation_guid && (
                    <button
                      className="download-btn"
                      onClick={() =>
                        onOpenThread?.({ module: 'messages', conversationGuid: detail.conversation_guid ?? undefined })
                      }
                    >
                      View conversation
                    </button>
                  )}
                </div>
              </div>
              {detail?.contact && (
                <div className="artifact-card" style={{ marginBottom: '1rem' }}>
                  <div className="artifact-card-meta">
                    <span className="artifact-chip">👤</span>
                    <span>Contact card</span>
                  </div>
                  <div className="artifact-card-body">
                    {[detail.contact.first_name, detail.contact.last_name].filter(Boolean).join(' ')}
                    {detail.contact.company ? ` · ${detail.contact.company}` : ''}
                    {detail.contact.phones.length > 0 && <div>{detail.contact.phones.join(', ')}</div>}
                    {detail.contact.emails.length > 0 && <div>{detail.contact.emails.join(', ')}</div>}
                  </div>
                </div>
              )}
              {selected.identifiers.length > 0 && (
                <div className="artifact-card-meta" style={{ marginBottom: '0.5rem' }}>
                  Identifiers: {selected.identifiers.join(', ')}
                </div>
              )}
              {detailLoading ? (
                <div className="loading">Loading activity…</div>
              ) : detailError ? (
                <div className="error-message">{detailError}</div>
              ) : !detail || detail.events.length === 0 ? (
                <div className="no-results">No activity events for this person.</div>
              ) : (
                <div className="messages-list scrollable">
                  {(() => {
                    let lastDay = '';
                    return detail.events.map((e, i) => {
                      const date = new Date(e.timestamp);
                      const day = date.toLocaleDateString();
                      const showDay = day !== lastDay;
                      lastDay = day;
                      const isMessage = e.artifact_type === 'whatsapp_message' || e.artifact_type === 'message';
                      return (
                        <div key={`${e.artifact_type}-${e.timestamp}-${i}`}>
                          {showDay && (
                            <div className="artifact-card-meta" style={{ marginTop: i ? '0.5rem' : 0, fontWeight: 600 }}>
                              {day}
                            </div>
                          )}
                          {isMessage ? (
                            <div className={`message ${e.is_from_me ? 'from-me' : 'from-other'}`}>
                              {!e.is_from_me && <div className="message-sender">{selected.display_name}</div>}
                              <div className="message-body">{e.title || ''}</div>
                              <div className="message-time">
                                {e.subtitle ? `${e.subtitle} · ` : ''}
                                {date.toLocaleString()}
                              </div>
                            </div>
                          ) : (
                            <div className="artifact-card">
                              <div className="artifact-card-meta">
                                <span className="artifact-chip">{EVENT_ICONS[e.artifact_type] ?? '•'}</span>
                                <span>{date.toLocaleTimeString()}</span>
                                {e.subtitle && <span>{e.subtitle}</span>}
                              </div>
                              <div className="artifact-card-body">{e.title || ''}</div>
                            </div>
                          )}
                        </div>
                      );
                    });
                  })()}
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}
