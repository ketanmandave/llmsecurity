import { FormEvent, useCallback, useEffect, useMemo, useState } from 'react';
import { ArchiveRestore, FilePlus2, LoaderCircle, Pencil, RefreshCw, ShieldCheck, Trash2, Upload } from 'lucide-react';
import { motion } from 'framer-motion';

import api from '../utils/api';

type RoleOption = { id: number; name: string; slug: string };
type Classification = 'public' | 'internal' | 'confidential' | 'restricted';
type DocumentStatus = 'processing' | 'active' | 'quarantined' | 'failed' | 'inactive';
type UploadConfig = {
  allowed_roles: RoleOption[];
  classifications: Classification[];
  max_upload_size_bytes: number;
  accepted_file_types: string[];
  native_text_only: boolean;
};
type RagDocument = {
  id: string;
  name: string;
  original_filename: string;
  size_bytes: number;
  classification: Classification;
  status: DocumentStatus;
  processing_error: string | null;
  total_pages: number | null;
  allowed_roles: RoleOption[];
  created_at: string;
};
type DocumentList = { items: RagDocument[]; total: number; limit: number; offset: number };

const statusStyles: Record<DocumentStatus, string> = {
  active: 'bg-emerald-500/15 text-emerald-300',
  processing: 'bg-blue-500/15 text-blue-300',
  inactive: 'bg-slate-500/15 text-slate-300',
  failed: 'bg-rose-500/15 text-rose-300',
  quarantined: 'bg-amber-500/15 text-amber-300',
};

function readableSize(bytes: number) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function errorDetail(error: unknown, fallback: string) {
  return (error as { response?: { data?: { detail?: string } } }).response?.data?.detail || fallback;
}

export default function DocumentsPage() {
  const [config, setConfig] = useState<UploadConfig | null>(null);
  const [documents, setDocuments] = useState<RagDocument[]>([]);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [file, setFile] = useState<File | null>(null);
  const [name, setName] = useState('');
  const [classification, setClassification] = useState<Classification>('internal');
  const [roleIds, setRoleIds] = useState<number[]>([]);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editingRoleIds, setEditingRoleIds] = useState<number[]>([]);

  const loadData = useCallback(async (quiet = false) => {
    if (!quiet) setLoading(true);
    try {
      const [configResponse, documentResponse] = await Promise.all([
        api.get<UploadConfig>('/rag/documents/config'),
        api.get<DocumentList>('/rag/documents', { params: { limit: 100, offset: 0 } }),
      ]);
      setConfig(configResponse.data);
      setDocuments(documentResponse.data.items);
      setError('');
    } catch (requestError) {
      setError(errorDetail(requestError, 'Unable to load the document library.'));
    } finally {
      if (!quiet) setLoading(false);
    }
  }, []);

  useEffect(() => { void loadData(); }, [loadData]);

  const processing = useMemo(
    () => documents.some((document) => document.status === 'processing'),
    [documents],
  );

  useEffect(() => {
    if (!processing) return undefined;
    const timer = window.setInterval(() => { void loadData(true); }, 3000);
    return () => window.clearInterval(timer);
  }, [processing, loadData]);

  const selectFile = (selected: File | null) => {
    setFile(selected);
    if (selected && !name.trim()) setName(selected.name.replace(/\.pdf$/i, ''));
  };

  const toggleRole = (roleId: number, current: number[], update: (roles: number[]) => void) => {
    update(current.includes(roleId) ? current.filter((id) => id !== roleId) : [...current, roleId]);
  };

  const uploadDocument = async (event: FormEvent) => {
    event.preventDefault();
    if (!file || !config) return setError('Choose a text-based PDF first.');
    if (file.type !== 'application/pdf' && !file.name.toLowerCase().endsWith('.pdf')) return setError('Only PDF files are accepted.');
    if (file.size > config.max_upload_size_bytes) return setError(`PDF exceeds the ${readableSize(config.max_upload_size_bytes)} limit.`);
    if (!roleIds.length) return setError('Select at least one access role.');

    const body = new FormData();
    body.append('file', file);
    body.append('name', name.trim());
    body.append('allowed_roles', JSON.stringify(roleIds));
    body.append('classification', classification);
    setBusy(true);
    setError('');
    setNotice('');
    try {
      await api.post('/rag/documents', body);
      setFile(null);
      setName('');
      setRoleIds([]);
      setNotice('Document accepted and queued for secure ingestion.');
      await loadData(true);
    } catch (requestError) {
      setError(errorDetail(requestError, 'Document upload failed.'));
    } finally {
      setBusy(false);
    }
  };

  const saveAccess = async (documentId: string) => {
    if (!editingRoleIds.length) return setError('A document must allow at least one role.');
    setBusy(true);
    try {
      await api.patch(`/rag/documents/${documentId}/access`, { allowed_role_ids: editingRoleIds });
      setEditingId(null);
      setNotice('Document permissions updated.');
      await loadData(true);
    } catch (requestError) {
      setError(errorDetail(requestError, 'Unable to update document permissions.'));
    } finally {
      setBusy(false);
    }
  };

  const changeState = async (document: RagDocument) => {
    setBusy(true);
    setError('');
    try {
      if (document.status === 'inactive') await api.post(`/rag/documents/${document.id}/activate`);
      else await api.delete(`/rag/documents/${document.id}`);
      setNotice(document.status === 'inactive' ? 'Document activated.' : 'Document deactivated.');
      await loadData(true);
    } catch (requestError) {
      setError(errorDetail(requestError, 'Unable to change document status.'));
    } finally {
      setBusy(false);
    }
  };

  const retryProcessing = async (documentId: string) => {
    setBusy(true);
    try {
      await api.post(`/rag/documents/${documentId}/process`);
      setNotice('Document processing queued again.');
      await loadData(true);
    } catch (requestError) {
      setError(errorDetail(requestError, 'Unable to retry document processing.'));
    } finally {
      setBusy(false);
    }
  };

  const permanentlyDelete = async (document: RagDocument) => {
    if (!window.confirm(`Permanently delete “${document.name}”? Its PDF, chunks, vectors, permissions, and findings will be erased.`)) return;
    setBusy(true);
    try {
      await api.delete(`/rag/documents/${document.id}/permanent`);
      setNotice('Document and vector data permanently deleted.');
      await loadData(true);
    } catch (requestError) {
      setError(errorDetail(requestError, 'Permanent deletion failed.'));
    } finally {
      setBusy(false);
    }
  };

  return <div className="space-y-6">
    <motion.section initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} className="rounded-3xl border border-slate-800 bg-slate-900/70 p-6">
      <div className="flex flex-wrap items-start justify-between gap-3"><div><h2 className="text-xl font-semibold">Company Knowledge Documents</h2><p className="mt-1 text-sm text-slate-400">Upload native-text PDFs and control which database roles may retrieve them.</p></div><button type="button" onClick={() => { void loadData(); }} className="flex items-center gap-2 rounded-lg border border-slate-700 px-3 py-2 text-sm text-slate-300 hover:bg-slate-800"><RefreshCw size={15} /> Refresh</button></div>
      {config?.native_text_only && <div className="mt-4 rounded-xl border border-amber-500/25 bg-amber-500/10 p-3 text-sm text-amber-200">Scanned/image-only PDFs are not supported. Upload PDFs containing selectable text.</div>}
      {error && <div className="mt-4 rounded-xl border border-rose-500/30 bg-rose-500/10 p-3 text-sm text-rose-300">{error}</div>}
      {notice && <div className="mt-4 rounded-xl border border-emerald-500/30 bg-emerald-500/10 p-3 text-sm text-emerald-300">{notice}</div>}

      <form onSubmit={uploadDocument} className="mt-6 grid gap-4 rounded-2xl border border-slate-800 bg-slate-950/60 p-5 lg:grid-cols-2">
        <label className="text-sm text-slate-300"><span className="mb-2 block font-medium">PDF file</span><input type="file" accept="application/pdf,.pdf" onChange={(event) => selectFile(event.target.files?.[0] || null)} className="block w-full rounded-lg border border-slate-700 bg-slate-900 p-2 text-sm file:mr-3 file:rounded-md file:border-0 file:bg-blue-500 file:px-3 file:py-2 file:text-white" /></label>
        <label className="text-sm text-slate-300"><span className="mb-2 block font-medium">Document name</span><input required maxLength={255} value={name} onChange={(event) => setName(event.target.value)} className="w-full rounded-lg border border-slate-700 bg-slate-900 px-3 py-2.5 outline-none focus:border-blue-500" /></label>
        <label className="text-sm text-slate-300"><span className="mb-2 block font-medium">Classification</span><select value={classification} onChange={(event) => setClassification(event.target.value as Classification)} className="w-full rounded-lg border border-slate-700 bg-slate-900 px-3 py-2.5 capitalize outline-none">{config?.classifications.map((item) => <option key={item} value={item}>{item}</option>)}</select></label>
        <fieldset><legend className="mb-2 text-sm font-medium text-slate-300">Allowed roles</legend><div className="flex flex-wrap gap-2">{config?.allowed_roles.map((role) => <label key={role.id} className={`cursor-pointer rounded-full border px-3 py-2 text-xs ${roleIds.includes(role.id) ? 'border-blue-400 bg-blue-500/20 text-blue-200' : 'border-slate-700 text-slate-400'}`}><input type="checkbox" checked={roleIds.includes(role.id)} onChange={() => toggleRole(role.id, roleIds, setRoleIds)} className="sr-only" />{role.name}</label>)}</div></fieldset>
        <div className="lg:col-span-2"><button disabled={busy || !config} className="flex items-center gap-2 rounded-lg bg-blue-500 px-4 py-2.5 text-sm font-medium text-white hover:bg-blue-400 disabled:opacity-50">{busy ? <LoaderCircle className="animate-spin" size={16} /> : <Upload size={16} />} Upload and process</button></div>
      </form>
    </motion.section>

    <section className="rounded-3xl border border-slate-800 bg-slate-900/70 p-6">
      <div className="flex items-center gap-2"><FilePlus2 className="text-blue-400" size={20} /><h2 className="text-lg font-semibold">Document library</h2></div>
      {loading ? <div className="flex items-center gap-2 py-12 text-sm text-slate-400"><LoaderCircle className="animate-spin" size={17} /> Loading documents...</div> : documents.length === 0 ? <p className="py-12 text-center text-sm text-slate-500">No documents uploaded.</p> : <div className="mt-5 space-y-3">{documents.map((document) => <article key={document.id} className="rounded-2xl border border-slate-800 bg-slate-950/60 p-4">
        <div className="flex flex-wrap items-start justify-between gap-4"><div className="min-w-0"><p className="truncate font-semibold text-white">{document.name}</p><p className="mt-1 text-xs text-slate-500">{document.original_filename} · {readableSize(document.size_bytes)}{document.total_pages ? ` · ${document.total_pages} pages` : ''}</p><div className="mt-3 flex flex-wrap gap-1.5">{document.allowed_roles.map((role) => <span key={role.id} className="rounded-full bg-slate-800 px-2.5 py-1 text-xs text-slate-300">{role.name}</span>)}</div>{document.processing_error && <p className="mt-3 text-xs text-rose-300">{document.processing_error}</p>}</div><div className="flex flex-wrap items-center gap-2"><span className="rounded-full bg-violet-500/15 px-3 py-1.5 text-xs capitalize text-violet-200">{document.classification}</span><span className={`rounded-full px-3 py-1.5 text-xs capitalize ${statusStyles[document.status]}`}>{document.status}</span></div></div>
        {editingId === document.id && <div className="mt-4 rounded-xl border border-slate-700 bg-slate-900 p-4"><p className="mb-3 text-sm font-medium">Replace allowed roles</p><div className="flex flex-wrap gap-2">{config?.allowed_roles.map((role) => <label key={role.id} className={`cursor-pointer rounded-full border px-3 py-2 text-xs ${editingRoleIds.includes(role.id) ? 'border-blue-400 bg-blue-500/20 text-blue-200' : 'border-slate-700 text-slate-400'}`}><input type="checkbox" checked={editingRoleIds.includes(role.id)} onChange={() => toggleRole(role.id, editingRoleIds, setEditingRoleIds)} className="sr-only" />{role.name}</label>)}</div><div className="mt-3 flex gap-2"><button type="button" disabled={busy} onClick={() => { void saveAccess(document.id); }} className="rounded-lg bg-blue-500 px-3 py-2 text-xs font-medium">Save access</button><button type="button" onClick={() => setEditingId(null)} className="rounded-lg border border-slate-700 px-3 py-2 text-xs">Cancel</button></div></div>}
        <div className="mt-4 flex flex-wrap gap-2 border-t border-slate-800 pt-4"><button type="button" onClick={() => { setEditingId(document.id); setEditingRoleIds(document.allowed_roles.map((role) => role.id)); }} className="flex items-center gap-1.5 rounded-lg border border-slate-700 px-3 py-2 text-xs hover:bg-slate-800"><Pencil size={13} /> Permissions</button>{['failed', 'quarantined'].includes(document.status) && <button type="button" disabled={busy} onClick={() => { void retryProcessing(document.id); }} className="flex items-center gap-1.5 rounded-lg border border-amber-500/30 px-3 py-2 text-xs text-amber-300"><RefreshCw size={13} /> Retry processing</button>}<button type="button" disabled={busy || document.status === 'processing'} onClick={() => { void changeState(document); }} className="flex items-center gap-1.5 rounded-lg border border-slate-700 px-3 py-2 text-xs hover:bg-slate-800">{document.status === 'inactive' ? <ArchiveRestore size={13} /> : <ShieldCheck size={13} />}{document.status === 'inactive' ? 'Activate' : 'Deactivate'}</button><button type="button" disabled={busy} onClick={() => { void permanentlyDelete(document); }} className="flex items-center gap-1.5 rounded-lg border border-rose-500/30 px-3 py-2 text-xs text-rose-300 hover:bg-rose-500/10"><Trash2 size={13} /> Delete permanently</button></div>
      </article>)}</div>}
    </section>
  </div>;
}
