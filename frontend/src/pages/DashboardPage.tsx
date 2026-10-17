import { useEffect, useState } from 'react';
import { Activity, AlertTriangle, Ban, CheckCircle2, ShieldAlert } from 'lucide-react';
import api from '../utils/api';
import { formatSecurityIntent } from '../utils/security-intent';

type Metrics = {
  total_requests: number;
  allowed_requests: number;
  blocked_requests: number;
  warned_requests: number;
  threat_counts: Record<string, number>;
  average_risk_score: number;
};

type SecurityIntent = {
  security_intent: string;
  count: number;
  dangerous_count: number;
};

type Risk = {
  severity_distribution: Record<string, number>;
  high_risk_requests: number;
  trend: {
    timestamp: string;
    average_score: number;
    high_risk_count: number;
  }[];
};

type Outcomes = {
  percentages: Record<string, number>;
  policy_distribution: Record<string, number>;
};

type UserActivity = {
  user_id: string;
  user_name: string | null;
  request_count: number;
  threat_count: number;
  average_risk_score: number;
};

const statusClass = (value: string | null) =>
  value?.toLowerCase() === 'allowed' || value?.toLowerCase() === 'allow'
    ? 'text-emerald-300'
    : value?.toLowerCase().includes('block') || value?.toLowerCase() === 'denied'
      ? 'text-rose-300'
      : 'text-amber-300';

export default function DashboardPage() {
  const [metrics, setMetrics] = useState<Metrics | null>(null);
  const [securityIntents, setSecurityIntents] = useState<SecurityIntent[]>([]);
  const [risk, setRisk] = useState<Risk | null>(null);
  const [outcomes, setOutcomes] = useState<Outcomes | null>(null);
  const [users, setUsers] = useState<UserActivity[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const load = async () => {
    setLoading(true);
    setError('');
    try {
      const [metricResponse, intentsResponse, riskResponse, outcomeResponse, usersResponse] = await Promise.all([
        api.get<Metrics>('/dashboard/metrics'),
        api.get<{ intents: SecurityIntent[] }>('/dashboard/semantic-intents'),
        api.get<Risk>('/dashboard/risk'),
        api.get<Outcomes>('/dashboard/outcomes'),
        api.get<UserActivity[]>('/dashboard/users'),
      ]);

      setMetrics(metricResponse.data);
      setSecurityIntents(intentsResponse.data.intents);
      setRisk(riskResponse.data);
      setOutcomes(outcomeResponse.data);
      setUsers(usersResponse.data);
    } catch {
      setError('Unable to load security analytics. Check the API connection and try again.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
      void load();

      const handleRefresh = () => {
        void load();
      };

      window.addEventListener('dashboard-refresh', handleRefresh);

      return () => {
        window.removeEventListener('dashboard-refresh', handleRefresh);
      };
    }, []);

  if (loading && !metrics) {
    return (
      <div className="rounded-2xl border border-slate-800 bg-slate-900/70 p-8 text-slate-400">
        Loading security analytics...
      </div>
    );
  }

  if (error && !metrics) {
    return (
      <div className="rounded-2xl border border-rose-500/30 bg-rose-500/10 p-6 text-rose-300">
        {error}
        <button
          onClick={() => {
            void load();
          }}
          className="ml-4 rounded-lg border border-rose-400/30 px-3 py-1 text-sm"
        >
          Retry
        </button>
      </div>
    );
  }

  const cards = [
    ['Total Requests', metrics?.total_requests, Activity],
    ['Allowed', metrics?.allowed_requests, CheckCircle2],
    ['Blocked', metrics?.blocked_requests, Ban],
    ['Warned / Reviewed', metrics?.warned_requests, AlertTriangle],
    [
      'Threats',
      Object.values(metrics?.threat_counts || {}).reduce((sum, count) => sum + count, 0),
      ShieldAlert,
    ],
  ] as const;

  const maxIntent = Math.max(1, ...securityIntents.map((item) => item.count));

  return (
    <div className="space-y-6">
  {error && <p className="rounded-lg border border-rose-500/30 bg-rose-500/10 p-3 text-sm text-rose-300">{error}</p>}

  <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-5">
    {cards.map(([label, value, Icon]) => (
      <div key={label} className="rounded-xl border border-slate-800 bg-slate-900/70 p-4">
        <div className="flex justify-between text-sm text-slate-400">
          <span>{label}</span>
          <Icon size={17} className="text-blue-300" />
        </div>
        <p className="mt-3 text-2xl font-semibold">{value ?? 0}</p>
      </div>
    ))}
  </div>

  <div className="grid gap-6 lg:grid-cols-3 items-start">
    {/* COLUMN 1 */}
    <section className="rounded-xl border border-slate-800 bg-slate-900/70 p-5">
      <h3 className="font-semibold">Security Intent Activity</h3>
      <div className="mt-5 space-y-4">
        {securityIntents.length ? (
          securityIntents.map((intent) => (
            <div key={intent.security_intent}>
              <div className="mb-1 flex justify-between text-sm">
                <span>{formatSecurityIntent(intent.security_intent)}</span>
                <span className="text-amber-300">
                  {intent.dangerous_count} Found
                </span>
              </div>
              <div className="h-2 rounded-full bg-slate-800">
                <div
                  className="h-2 rounded-full bg-amber-400"
                  style={{ width: `${(intent.count / maxIntent) * 100}%` }}
                />
              </div>
            </div>
          ))
        ) : (
          <p className="py-8 text-sm text-slate-500">No security intent observations recorded.</p>
        )}
      </div>
    </section>

    {/* COLUMN 2 */}
    <div className="flex flex-col gap-6">
      <section className="rounded-xl border border-slate-800 bg-slate-900/70 p-5">
        <h3 className="font-semibold">Risk distribution</h3>
        <div className="mt-4 space-y-3">
          {Object.entries(risk?.severity_distribution || {}).map(([severity, count]) => (
            <div key={severity} className="flex items-center justify-between rounded-lg bg-slate-950/60 p-3">
              <span className={statusClass(severity)}>{severity}</span>
              <strong>{count}</strong>
            </div>
          ))}
          <p className="text-sm text-slate-400">High-risk requests: {risk?.high_risk_requests || 0}</p>
        </div>
      </section>

      <section className="rounded-xl border border-slate-800 bg-slate-900/70 p-5">
        <h3 className="font-semibold">Risk over time</h3>
        <div className="mt-4 max-h-40 space-y-2 overflow-y-auto">
          {risk?.trend.length ? (
            risk.trend.map((point) => (
              <div key={point.timestamp} className="flex items-center justify-between text-xs">
                <span className="text-slate-500">{new Date(point.timestamp).toLocaleString()}</span>
                <span className="text-cyan-300">
                  {point.average_score} avg · {point.high_risk_count} high
                </span>
              </div>
            ))
          ) : (
            <p className="text-sm text-slate-500">No risk trend data recorded.</p>
          )}
        </div>
      </section>
    </div>

    {/* COLUMN 3 */}
    <div className="flex flex-col gap-6">
      <section className="rounded-xl border border-slate-800 bg-slate-900/70 p-5">
        <h3 className="font-semibold">Outcome analytics</h3>
        <div className="mt-4 space-y-2 text-sm">
          {Object.entries(outcomes?.percentages || {}).map(([key, value]) => (
            <div key={key} className="flex justify-between">
              <span className="text-slate-400">{key.replace(/_/g, ' ')}</span>
              <span>{value}%</span>
            </div>
          ))}
          <p className="mt-4 border-t border-slate-800 pt-3 text-slate-400">
            Policy:{' '}
            {Object.entries(outcomes?.policy_distribution || {})
              .map(([key, value]) => `${key} ${value}`)
              .join(' · ') || 'No policy data'}
          </p>
        </div>
      </section>

      <section className="rounded-xl border border-slate-800 bg-slate-900/70 p-5">
        <h3 className="font-semibold">User activity</h3>
        <div className="mt-4 space-y-2">
          {users.length ? (
            users.slice(0, 6).map((item) => (
              <div key={item.user_id} className="flex items-center justify-between border-b border-slate-800 pb-2 text-sm">
                <span className="truncate">
                  {item.user_name || item.user_id.slice(0, 8)}
                  <small className="block text-xs text-slate-500">
                    {item.request_count} requests · {item.threat_count} threats
                  </small>
                </span>
                <span className="text-slate-300">{item.average_risk_score}</span>
              </div>
            ))
          ) : (
            <p className="text-sm text-slate-500">No user activity recorded.</p>
          )}
        </div>
      </section>
    </div>
  </div>
</div>
  );
}
