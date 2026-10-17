import { motion } from 'framer-motion';
import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../utils/api';

type TimelineEvent = {
  event_id: string;
  request_id: string;
  conversation_id: string;
  timestamp: string;
  user_id: string;
  risk_score: number | null;
  risk_severity: string | null;
  policy_decision: string | null;
  outcome: string;
};

const statusClass = (value: string | null) =>
  value?.toLowerCase() === 'allowed' || value?.toLowerCase() === 'allow'
    ? 'text-emerald-300'
    : value?.toLowerCase().includes('block') || value?.toLowerCase() === 'denied'
      ? 'text-rose-300'
      : 'text-amber-300';

export default function AuditLogsPage() {
  const navigate = useNavigate();
  const [events, setEvents] = useState<TimelineEvent[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    const loadTimeline = async () => {
      try {
        const response = await api.get<TimelineEvent[]>('/dashboard/timeline?limit=100');
        setEvents(response.data);
      } catch {
        setError('Unable to load request timeline.');
      } finally {
        setLoading(false);
      }
    };

    const handleRefresh = () => {
      void loadTimeline();
    };

    void loadTimeline();

    window.addEventListener('dashboard-refresh', handleRefresh);

    return () => {
      window.removeEventListener('dashboard-refresh', handleRefresh);
    };
  }, []);

  return (
    <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} className="space-y-6">
      <motion.div className="rounded-3xl border border-slate-800 bg-slate-900/70 p-6">
        <h2 className="text-xl font-semibold">Request Timeline</h2>
        <p className="text-sm text-slate-400">Historical prompt/request activity.</p>

        {error && (
          <p className="mt-4 rounded-lg border border-rose-500/30 bg-rose-500/10 p-3 text-sm text-rose-300">
            {error}
          </p>
        )}

        <div className="mt-4 max-h-96 overflow-y-auto rounded-2xl border border-slate-800">
          {loading ? (
            <div className="flex items-center justify-center py-8 text-slate-400">Loading timeline...</div>
          ) : events.length > 0 ? (
            <table className="w-full text-left text-xs">
              <thead className="sticky top-0 bg-slate-800/70 text-slate-300">
                <tr>
                  <th className="px-4 py-3">Time</th>
                  <th className="px-4 py-3">User / Request</th>
                  <th className="px-4 py-3">Risk</th>
                  <th className="px-4 py-3">Policy</th>
                  <th className="px-4 py-3">Outcome</th>
                </tr>
              </thead>
              <tbody>
                {events.map((event) => (
                  <tr key={event.event_id} className="border-t border-slate-800 bg-slate-950/60 cursor-pointer hover:bg-slate-900/60" onClick={() => navigate(`/investigations/${event.event_id}`)}>
                    <td className="px-4 py-3 text-slate-400">{new Date(event.timestamp).toLocaleString()}</td>
                    <td className="px-4 py-3 text-blue-300">
                      {event.user_id.slice(0, 8)}
                      <p className="text-slate-500">{event.request_id.slice(0, 8)}</p>
                    </td>
                    <td className={`px-4 py-3 ${statusClass(event.risk_severity)}`}>
                      {event.risk_severity} {event.risk_score ?? ''}
                    </td>
                    <td className="px-4 py-3 text-slate-300">{event.policy_decision}</td>
                    <td className="px-4 py-3 text-slate-300">{event.outcome}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <div className="flex items-center justify-center py-8 text-slate-400">No request timeline data recorded.</div>
          )}
        </div>
      </motion.div>
    </motion.div>
  );
}
