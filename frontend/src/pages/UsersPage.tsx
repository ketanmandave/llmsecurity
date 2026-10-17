import { useCallback, useEffect, useMemo, useState } from 'react';
import { CheckCircle2, LoaderCircle, RefreshCw, Trash2, UserCheck, UserX } from 'lucide-react';
import { motion } from 'framer-motion';

import { useAuth } from '../contexts/AuthContext';
import api from '../utils/api';

type UserRecord = {
  id: string;
  name: string;
  email: string;
  role_id: number;
  is_verified: boolean;
  is_active: boolean;
  created_at: string;
  last_login: string | null;
};

type Role = { id: number; name: string; description: string | null };

function errorDetail(error: unknown, fallback: string) {
  return (error as { response?: { data?: { detail?: string } } }).response?.data?.detail || fallback;
}

export default function UsersPage() {
  const { user: currentUser } = useAuth();
  const [users, setUsers] = useState<UserRecord[]>([]);
  const [roles, setRoles] = useState<Role[]>([]);
  const [loading, setLoading] = useState(true);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');

  const loadData = useCallback(async () => {
    setLoading(true);
    try {
      const [userResponse, roleResponse] = await Promise.all([
        api.get<UserRecord[]>('/users'),
        api.get<Role[]>('/roles'),
      ]);
      setUsers(userResponse.data);
      setRoles(roleResponse.data);
      setError('');
    } catch (requestError) {
      setError(errorDetail(requestError, 'Unable to load users.'));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { void loadData(); }, [loadData]);

  const rolesById = useMemo(
    () => new Map(roles.map((role) => [role.id, role.name])),
    [roles],
  );

  const updateStatus = async (record: UserRecord, isActive: boolean) => {
    setBusyId(record.id);
    setError('');
    try {
      await api.patch(`/users/${record.id}/status`, { is_active: isActive });
      setNotice(isActive ? `${record.name} was approved and activated.` : `${record.name} was deactivated.`);
      await loadData();
    } catch (requestError) {
      setError(errorDetail(requestError, 'Unable to change account status.'));
    } finally {
      setBusyId(null);
    }
  };

  const updateRole = async (record: UserRecord, roleId: number) => {
    setBusyId(record.id);
    setError('');
    try {
      await api.patch(`/users/${record.id}/role`, { role_id: roleId });
      setNotice(`${record.name}'s role was updated.`);
      await loadData();
    } catch (requestError) {
      setError(errorDetail(requestError, 'Unable to change the role.'));
    } finally {
      setBusyId(null);
    }
  };

  const rejectPending = async (record: UserRecord) => {
    if (!window.confirm(`Reject and delete the pending registration for ${record.email}?`)) return;
    setBusyId(record.id);
    setError('');
    try {
      await api.delete(`/users/${record.id}`);
      setNotice('Pending registration rejected.');
      await loadData();
    } catch (requestError) {
      setError(errorDetail(requestError, 'Unable to reject registration.'));
    } finally {
      setBusyId(null);
    }
  };

  return (
    <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} className="rounded-3xl border border-slate-800 bg-slate-900/70 p-6">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div><h2 className="text-xl font-semibold">User Management</h2><p className="mt-1 text-sm text-slate-400">Approve requested roles and control account access.</p></div>
        <button type="button" onClick={() => { void loadData(); }} className="flex items-center gap-2 rounded-lg border border-slate-700 px-3 py-2 text-sm"><RefreshCw size={15} /> Refresh</button>
      </div>

      {error && <div className="mt-4 rounded-xl border border-rose-500/30 bg-rose-500/10 p-3 text-sm text-rose-200">{error}</div>}
      {notice && <div className="mt-4 rounded-xl border border-emerald-500/30 bg-emerald-500/10 p-3 text-sm text-emerald-200">{notice}</div>}

      {loading ? <div className="flex items-center gap-2 py-12 text-slate-400"><LoaderCircle className="animate-spin" size={17} /> Loading users...</div> : (
        <div className="mt-6 space-y-3">
          {users.map((record) => {
            const pending = !record.is_verified;
            const ownAccount = record.id === currentUser?.id;
            const busy = busyId === record.id;
            return <article key={record.id} className={`rounded-2xl border p-4 ${pending ? 'border-amber-500/30 bg-amber-500/5' : 'border-slate-800 bg-slate-950/70'}`}>
              <div className="flex flex-wrap items-center justify-between gap-4">
                <div className="min-w-0"><p className="font-medium text-white">{record.name}</p><p className="mt-1 text-sm text-slate-400">{record.email}</p><p className="mt-1 text-xs text-slate-500">Requested/assigned role: {rolesById.get(record.role_id) || `Role ${record.role_id}`}</p></div>
                <div className="flex flex-wrap items-center gap-2">
                  <span className={`rounded-full px-3 py-1.5 text-xs ${pending ? 'bg-amber-500/15 text-amber-300' : record.is_active ? 'bg-emerald-500/15 text-emerald-300' : 'bg-slate-500/15 text-slate-300'}`}>{pending ? 'Pending approval' : record.is_active ? 'Active' : 'Inactive'}</span>
                  <select aria-label={`Role for ${record.name}`} value={record.role_id} disabled={busy || ownAccount} onChange={(event) => { void updateRole(record, Number(event.target.value)); }} className="rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-sm disabled:opacity-50">
                    {roles.map((role) => <option key={role.id} value={role.id}>{role.name}</option>)}
                  </select>
                </div>
              </div>
              <div className="mt-4 flex flex-wrap gap-2 border-t border-slate-800 pt-4">
                {pending && <button type="button" disabled={busy} onClick={() => { void updateStatus(record, true); }} className="flex items-center gap-1.5 rounded-lg border border-emerald-500/30 px-3 py-2 text-xs text-emerald-300"><CheckCircle2 size={14} /> Approve</button>}
                {pending && <button type="button" disabled={busy} onClick={() => { void rejectPending(record); }} className="flex items-center gap-1.5 rounded-lg border border-rose-500/30 px-3 py-2 text-xs text-rose-300"><Trash2 size={14} /> Reject</button>}
                {!pending && !ownAccount && <button type="button" disabled={busy} onClick={() => { void updateStatus(record, !record.is_active); }} className="flex items-center gap-1.5 rounded-lg border border-slate-700 px-3 py-2 text-xs">{record.is_active ? <UserX size={14} /> : <UserCheck size={14} />}{record.is_active ? 'Deactivate' : 'Reactivate'}</button>}
              </div>
            </article>;
          })}
        </div>
      )}
    </motion.div>
  );
}
