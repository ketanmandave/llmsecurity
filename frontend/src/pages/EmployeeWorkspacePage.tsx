import { useEffect, useRef, useState } from 'react';
import { ArrowLeft, BookOpen, Bot, LoaderCircle, LogOut, Menu, Plus, Send, Trash2, X } from 'lucide-react';

import api from '../utils/api';
import { useAuth } from '../contexts/AuthContext';

type Conversation = { id: string; title: string; created_at: string; updated_at: string };
type Citation = { source_id: string; document_id: string; document_name: string; page_number: number | null };
type Message = {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  mode: 'assistant' | 'rag';
  citations: Citation[];
  grounded: boolean | null;
  timestamp: string;
};

function InlineContent({ text }: { text: string }) {
  return <>{text.split(/(`[^`]+`|\*\*[^*]+\*\*|\*[^*]+\*)/g).map((part, index) => {
    if (part.startsWith('`') && part.endsWith('`')) return <code key={index} className="rounded bg-slate-800 px-1.5 py-0.5 text-cyan-200">{part.slice(1, -1)}</code>;
    if (part.startsWith('**') && part.endsWith('**')) return <strong key={index}>{part.slice(2, -2)}</strong>;
    if (part.startsWith('*') && part.endsWith('*')) return <em key={index}>{part.slice(1, -1)}</em>;
    return <span key={index}>{part}</span>;
  })}</>;
}

function ResponseContent({ content }: { content: string }) {
  const blocks = content.split(/```(?:[\w+-]+)?\n?/);
  return <div className="space-y-3 break-words">
    {blocks.map((block, index) => {
      if (index % 2) return <pre key={index} className="overflow-x-auto rounded-lg border border-slate-700 bg-slate-950 p-3 text-xs leading-5 text-cyan-100"><code>{block.trim()}</code></pre>;
      return block.split(/\n{2,}/).map((paragraph, paragraphIndex) => {
        const lines = paragraph.split('\n');
        return <div key={`${index}-${paragraphIndex}`} className="space-y-1">
          {lines.map((line, lineIndex) => {
            const heading = line.match(/^(#{1,3})\s+(.+)$/);
            const listItem = line.match(/^\s*([-*]|\d+\.)\s+(.+)$/);
            if (heading) return <h3 key={lineIndex} className="pt-1 text-base font-semibold text-white"><InlineContent text={heading[2]} /></h3>;
            if (listItem) return <div key={lineIndex} className="ml-4 list-item"><InlineContent text={listItem[2]} /></div>;
            return <p key={lineIndex} className="whitespace-pre-wrap"><InlineContent text={line} /></p>;
          })}
        </div>;
      });
    })}
  </div>;
}

export default function EmployeeWorkspacePage() {
  const { user, logout } = useAuth();
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [mode, setMode] = useState<'assistant' | 'rag'>('assistant');
  const [loading, setLoading] = useState(false);
  const [loadingConversations, setLoadingConversations] = useState(true);
  const [loadingMessages, setLoadingMessages] = useState(false);
  const [error, setError] = useState('');
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const scrollRef = useRef<HTMLDivElement>(null);
  const endRef = useRef<HTMLDivElement>(null);
  const shouldFollowRef = useRef(true);
  const loadedUserIdRef = useRef<string | null>(null);

  const loadConversations = async () => {
    setLoadingConversations(true);
    try {
      const response = await api.get<Conversation[]>('/workspace/conversations');
      setConversations(response.data);
    } finally {
      setLoadingConversations(false);
    }
  };

  useEffect(() => {
    if (!user?.id) {
      loadedUserIdRef.current = null;
      return;
    }

    if (loadedUserIdRef.current === user.id) {
      return;
    }

    loadedUserIdRef.current = user.id;
    setConversations([]);
    setConversationId(null);
    setMessages([]);
    setError('');
    void loadConversations().catch(() => setError('Unable to load conversation history.'));
  }, [user?.id]);

  useEffect(() => {
    if (shouldFollowRef.current) endRef.current?.scrollIntoView({ behavior: loading ? 'auto' : 'smooth', block: 'end' });
  }, [messages, loading]);

  const trackScroll = () => {
    const element = scrollRef.current;
    if (!element) return;
    shouldFollowRef.current = element.scrollHeight - element.scrollTop - element.clientHeight < 120;
  };

  const openConversation = async (id: string) => {
    setLoadingMessages(true);
    setError('');
    try {
      const response = await api.get<{ messages: Message[] }>(`/workspace/conversations/${id}`);
      setConversationId(id);
      setMessages(response.data.messages);
      shouldFollowRef.current = true;
    } catch {
      setError('Unable to open conversation.');
    } finally {
      setLoadingMessages(false);
    }
  };

  const newChat = async () => {
    try {
      const response = await api.post<Conversation>('/workspace/conversations', {});
      setConversationId(response.data.id);
      setMessages([]);
      setError('');
      await loadConversations();
    } catch {
      setError('Unable to create a conversation.');
    }
  };

  const deleteConversation = async (id: string) => {
    const conversation = conversations.find((item) => item.id === id);
    if (!conversation || !window.confirm(`Delete "${conversation.title}"? This cannot be undone.`)) return;
    try {
      await api.delete(`/workspace/conversations/${id}`);
      setConversations((current) => current.filter((item) => item.id !== id));
      if (conversationId === id) {
        setConversationId(null);
        setMessages([]);
      }
      setError('');
    } catch {
      setError('Unable to delete conversation.');
    }
  };

  const send = async () => {
    if (!input.trim() || loading) return;
    let activeId = conversationId;
    const content = input.trim();
    try {
      if (!activeId) {
        const response = await api.post<Conversation>('/workspace/conversations', {});
        activeId = response.data.id;
        setConversationId(activeId);
      }
      setInput('');
      setError('');
      shouldFollowRef.current = true;
      const pendingId = `pending-${Date.now()}`;
      setMessages((current) => [...current, { id: pendingId, role: 'user', content, mode, citations: [], grounded: null, timestamp: new Date().toISOString() }]);
      setLoading(true);
      const response = await api.post<{ user_message: Message; assistant_message: Message }>(`/workspace/conversations/${activeId}/messages`, { content, mode });
      setMessages((current) => [...current.filter((message) => message.id !== pendingId), response.data.user_message, response.data.assistant_message]);
      await loadConversations();
    } catch (requestError) {
      const detail = (requestError as { response?: { data?: { detail?: string } } }).response?.data?.detail;
      setMessages((current) => current.filter((message) => !message.id.startsWith('pending-')));
      setError(detail || 'Unable to send your message. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  return <main className="flex h-[100dvh] min-h-0 overflow-hidden bg-slate-950 text-slate-100">
    <aside className={`${sidebarOpen ? 'w-72' : 'w-0'} h-full shrink-0 overflow-hidden border-r border-slate-800 bg-slate-900/90 transition-all`}>
      <div className="flex h-full w-72 min-w-72 flex-col p-4">
        <button onClick={() => { void logout(); }} className="inline-flex items-center gap-2 text-left text-sm text-slate-400 hover:text-slate-100"><ArrowLeft size={16} /> Exit Workspace</button>
        <div className="mt-6"><p className="font-semibold">Employee Workspace</p><p className="mt-1 text-xs text-slate-400">Role: {user?.role_name}</p></div>
        <button onClick={() => { void newChat(); }} className="mt-6 flex items-center justify-center gap-2 rounded-lg bg-blue-500 px-3 py-2 text-sm font-medium hover:bg-blue-400"><Plus size={16} /> New Chat</button>
        <nav className="mt-5 min-h-0 flex-1 space-y-1 overflow-y-auto pr-1">
          {loadingConversations && <p className="px-3 py-2 text-sm text-slate-500">Loading conversations...</p>}
          {!loadingConversations && conversations.length === 0 && <p className="px-3 py-2 text-sm text-slate-500">No conversations yet.</p>}
          {conversations.map((conversation) => <div key={conversation.id} className={`group flex items-center gap-1 rounded-lg ${conversation.id === conversationId ? 'bg-slate-800 text-white' : 'text-slate-400 hover:bg-slate-800/60 hover:text-slate-100'}`}>
            <button onClick={() => { void openConversation(conversation.id); }} className="min-w-0 flex-1 truncate px-3 py-2 text-left text-sm">{conversation.title}</button>
            <button aria-label={`Delete ${conversation.title}`} title="Delete conversation" onClick={() => { void deleteConversation(conversation.id); }} className="mr-1 rounded p-1.5 text-slate-500 opacity-0 hover:bg-rose-500/15 hover:text-rose-300 group-hover:opacity-100"><Trash2 size={14} /></button>
          </div>)}
        </nav>
        <button onClick={() => { void logout(); }} className="flex items-center gap-2 rounded-lg border border-slate-800 px-3 py-2 text-sm text-slate-300 hover:bg-slate-800"><LogOut size={16} /> Logout</button>
      </div>
    </aside>
    <section className="flex min-h-0 min-w-0 flex-1 flex-col">
      <header className="flex shrink-0 items-center gap-3 border-b border-slate-800 bg-slate-900/60 p-4"><button aria-label="Toggle conversations" onClick={() => setSidebarOpen((value) => !value)} className="rounded-lg p-2 hover:bg-slate-800">{sidebarOpen ? <X size={18} /> : <Menu size={18} />}</button><div className="min-w-0 flex-1"><h1 className="font-semibold">SentinelAI Assistant</h1><p className="text-xs text-slate-400">Secure employee workspace</p></div><div className="flex rounded-lg border border-slate-700 bg-slate-950 p-1" aria-label="Answer mode"><button type="button" onClick={() => setMode('assistant')} className={`flex items-center gap-1.5 rounded-md px-3 py-1.5 text-xs font-medium ${mode === 'assistant' ? 'bg-blue-500 text-white' : 'text-slate-400 hover:text-white'}`}><Bot size={14} /> Assistant</button><button type="button" onClick={() => setMode('rag')} className={`flex items-center gap-1.5 rounded-md px-3 py-1.5 text-xs font-medium ${mode === 'rag' ? 'bg-emerald-500 text-white' : 'text-slate-400 hover:text-white'}`}><BookOpen size={14} /> Company Knowledge</button></div></header>
      <div ref={scrollRef} onScroll={trackScroll} className="min-h-0 flex-1 overflow-y-auto p-4">
        <div className="mx-auto max-w-3xl space-y-4 pb-4">
          {loadingMessages && <div className="flex items-center justify-center gap-2 py-16 text-sm text-slate-400"><LoaderCircle className="animate-spin" size={18} /> Loading messages...</div>}
          {!loadingMessages && messages.length === 0 && <div className="pt-24 text-center"><h2 className="text-2xl font-semibold">What can SentinelAI help with?</h2><p className="mt-2 text-sm text-slate-400">Ask a workplace question to begin a secure conversation.</p></div>}
          {messages.map((message) => <div key={message.id} className={`max-w-[90%] rounded-2xl px-4 py-3 text-sm leading-6 ${message.role === 'user' ? 'ml-auto bg-blue-500 text-white' : 'mr-auto border border-slate-800 bg-slate-900/80'}`}>
            {message.role === 'assistant' ? <ResponseContent content={message.content} /> : <p className="whitespace-pre-wrap break-words">{message.content}</p>}
            {message.role === 'assistant' && message.citations?.length > 0 && <div className="mt-3 border-t border-slate-700 pt-3"><p className="mb-2 text-xs font-semibold uppercase tracking-wide text-emerald-300">Sources</p><div className="space-y-1.5">{message.citations.map((citation) => <div key={`${citation.source_id}-${citation.document_id}`} className="rounded-lg bg-slate-950/70 px-3 py-2 text-xs text-slate-300"><span className="font-semibold text-emerald-300">[{citation.source_id}]</span> {citation.document_name}{citation.page_number ? ` · Page ${citation.page_number}` : ''}</div>)}</div></div>}
          </div>)}
          {loading && <div className="flex items-center gap-2 text-sm text-slate-400"><LoaderCircle className="animate-spin" size={16} /> Generating response...</div>}
          {error && <p className="rounded-lg border border-rose-500/30 bg-rose-500/10 p-3 text-sm text-rose-300">{error}</p>}
          <div ref={endRef} />
        </div>
      </div>
      <form onSubmit={(event) => { event.preventDefault(); void send(); }} className="shrink-0 border-t border-slate-800 bg-slate-900/60 p-4"><div className="mx-auto max-w-3xl"><p className="mb-2 text-xs text-slate-500">{mode === 'rag' ? 'Answers use only company documents allowed for your role.' : 'General AI assistant mode.'}</p><div className="flex items-end gap-2 rounded-xl border border-slate-700 bg-slate-900 p-2"><textarea value={input} onChange={(event) => setInput(event.target.value)} onKeyDown={(event) => { if (event.key === 'Enter' && !event.shiftKey) { event.preventDefault(); void send(); } }} rows={2} placeholder={mode === 'rag' ? 'Ask about company documents...' : 'Write a message...'} className="min-h-12 flex-1 resize-none bg-transparent px-2 py-1 text-sm outline-none" /><button aria-label="Send message" disabled={loading || !input.trim()} className="rounded-lg bg-blue-500 p-3 text-white disabled:cursor-not-allowed disabled:opacity-40"><Send size={17} /></button></div></div></form>
    </section>
  </main>;
}
