import { useEffect, useState } from 'react';
import { ArrowLeft, LoaderCircle, AlertTriangle, CheckCircle } from 'lucide-react';
import { Link, useParams } from 'react-router-dom';
import api from '../utils/api';
import { formatSecurityIntent } from '../utils/security-intent';

type Investigation = {
  id: string;
  request_id: string;
  conversation_id: string;
  user_id: string;
  user_role: string;
  request_timestamp: string;
  completed_at: string;
  prompt: string;
  authorization_decision: string | null;
  authorization_reason: string | null;
  detector_results: Record<string, unknown>[] | null;
  risk_score: number | null;
  risk_severity: string | null;
  policy_decision: string | null;
  outcome: string;
  provider: string | null;
  provider_called: boolean;
  provider_status_code: number | null;
  response_assessment: Record<string, unknown> | null;
  response_outcome: string | null;
  latency_ms: number | null;
  metadata_json: Record<string, unknown> | null;
  error_type: string | null;
  error_message: string | null;
};

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="rounded-xl border border-slate-800 bg-slate-900/70 p-5">
      <h2 className="mb-4 font-semibold text-blue-200">{title}</h2>
      {children}
    </section>
  );
}

function Data({ label, value }: { label: string; value: unknown }) {
  return (
    <div>
      <dt className="text-xs uppercase tracking-wide text-slate-500">{label}</dt>
      <dd className="mt-1 break-words text-sm text-slate-200">{String(value ?? 'Not recorded')}</dd>
    </div>
  );
}

function extractSemanticIntentFromDetectors(
  detectors: Record<string, unknown>[] | null
): { intent: string; confidence: number; status: string } | null {
  if (!detectors || detectors.length === 0) return null;

  for (const detector of detectors) {
    if (!detector || typeof detector !== 'object') continue;

    const metadata = (detector as any).metadata;
    if (metadata && typeof metadata === 'object' && metadata.security_intent) {
      return {
        intent: String(metadata.security_intent),
        confidence: Number(metadata.security_intent_confidence) || 0,
        status: String((detector as any).status || 'SAFE'),
      };
    }
  }

  return null;
}

export default function InvestigationPage() {
  const { identifier } = useParams();
  const [event, setEvent] = useState<Investigation | null>(null);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!identifier) return;

    api
      .get<Investigation>(`/dashboard/investigations/${identifier}`)
      .then((response) => setEvent(response.data))
      .catch((requestError) =>
        setError(
          requestError.response?.status === 404
            ? 'Security event not found.'
            : 'Unable to load this investigation.'
        )
      );
  }, [identifier]);

  if (error) {
    return (
      <div className="rounded-xl border border-rose-500/30 bg-rose-500/10 p-6 text-rose-300">
        {error}
        <Link to="/dashboard" className="ml-4 underline">
          Back to dashboard
        </Link>
      </div>
    );
  }

  if (!event) {
    return (
      <div className="flex items-center gap-2 text-slate-400">
        <LoaderCircle className="animate-spin" size={18} />
        Loading investigation...
      </div>
    );
  }

  const semanticIntent = extractSemanticIntentFromDetectors(event.detector_results);
  const isDangerous = semanticIntent?.status === 'DANGEROUS';
  const policyDecisionClass =
    event.policy_decision?.toUpperCase() === 'ALLOW'
      ? 'bg-emerald-500/20 text-emerald-300 border-emerald-500/30'
      : event.policy_decision?.toUpperCase() === 'BLOCK'
        ? 'bg-rose-500/20 text-rose-300 border-rose-500/30'
        : 'bg-amber-500/20 text-amber-300 border-amber-500/30';

  return (
    <div className="space-y-5">
      <Link to="/dashboard" className="inline-flex items-center gap-2 text-sm text-slate-400 hover:text-white">
        <ArrowLeft size={16} />
        Back to dashboard
      </Link>

      <div>
        <p className="text-sm text-blue-300">Historical gateway record</p>
        <h1 className="text-2xl font-semibold">Request Investigation</h1>
      </div>

      <Section title="Request overview">
        <dl className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <Data label="Request ID" value={event.request_id} />
          <Data label="Conversation ID" value={event.conversation_id} />
          <Data label="User" value={`${event.user_id} (${event.user_role})`} />
          <Data label="Timestamp" value={new Date(event.request_timestamp).toLocaleString()} />
          <Data label="Provider" value={event.provider} />
          <Data label="Risk" value={`${event.risk_severity || 'Not recorded'} ${event.risk_score ?? ''}`} />
          <Data label="Latency" value={event.latency_ms ? `${event.latency_ms} ms` : null} />
        </dl>
      </Section>

      {semanticIntent && (
        <div className="rounded-xl border border-slate-800 bg-slate-900/70 p-6">
          <h2 className="mb-4 font-semibold text-blue-200">Prompt Security</h2>

          <div className="space-y-4">
            <div>
              <div className="text-4xl font-bold tracking-tight text-slate-100">
                {formatSecurityIntent(semanticIntent.intent).toUpperCase()}
              </div>
            </div>

            <div className="flex items-center gap-4">
              <div
                className={`inline-flex items-center gap-2 rounded-lg border px-4 py-2 ${isDangerous ? 'border-rose-500/30 bg-rose-500/10 text-rose-300' : 'border-emerald-500/30 bg-emerald-500/10 text-emerald-300'}`}
              >
                {isDangerous ? <AlertTriangle size={16} /> : <CheckCircle size={16} />}
                <span className="font-medium">{isDangerous ? 'DANGEROUS' : 'SAFE'}</span>
              </div>

              <div className="text-2xl font-semibold text-blue-300">
                {semanticIntent.confidence.toFixed(2)}%
              </div>
            </div>
          </div>
        </div>
      )}

      <div className="grid gap-5 lg:grid-cols-2">
        <Section title="Authorization">
          <dl className="space-y-3">
            <Data label="Decision" value={event.authorization_decision} />
            <Data label="Reason" value={event.authorization_reason} />
          </dl>
        </Section>

        <Section title="Policy Decision">
          <dl className="space-y-3">
            <div>
              <dt className="text-xs uppercase tracking-wide text-slate-500">Decision</dt>
              <dd className={`mt-2 inline-block rounded-lg border px-4 py-2 font-semibold ${policyDecisionClass}`}>
                {event.policy_decision?.toUpperCase() || 'NOT RECORDED'}
              </dd>
            </div>
            <Data label="Response outcome" value={event.response_outcome} />
            <Data label="Provider called" value={event.provider_called ? 'Yes' : 'No'} />
          </dl>
        </Section>
      </div>

      <Section title="Prompt security detectors">
        {event.detector_results?.length ? (
          <div className="grid gap-3 md:grid-cols-2">
            {event.detector_results.map((detector, index) => (
              <div key={index} className="rounded-lg border border-slate-800 bg-slate-950/60 p-3 text-sm">
                <p className="font-medium text-slate-300">{String(detector.detector_name || 'Detector')}</p>
                <p className="mt-2 text-slate-400">
                  {String(detector.status || 'Unknown')} · {String(detector.severity || 'No severity')} · score{' '}
                  {String(detector.score ?? 'n/a')}
                </p>
                <p className="mt-2 text-xs text-slate-500">{String(detector.reason || '')}</p>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-sm text-slate-500">No prompt detector data recorded.</p>
        )}
      </Section>

      <Section title="Response security">
        {event.response_assessment ? (
          <div className="space-y-3">
            <dl className="grid gap-4 sm:grid-cols-3">
              <Data label="Score" value={event.response_assessment.overall_score} />
              <Data label="Severity" value={event.response_assessment.overall_severity} />
              <Data label="Summary" value={event.response_assessment.summary} />
            </dl>
            <details>
              <summary className="cursor-pointer text-sm text-slate-400">Show persisted response assessment</summary>
              <pre className="mt-3 max-h-80 overflow-auto rounded-lg bg-slate-950 p-3 text-xs text-slate-300">
                {JSON.stringify(event.response_assessment, null, 2)}
              </pre>
            </details>
          </div>
        ) : (
          <p className="text-sm text-slate-500">No response assessment recorded.</p>
        )}
      </Section>

      <Section title="Persisted request text">
        <p className="whitespace-pre-wrap break-words text-sm text-slate-300">{event.prompt}</p>
      </Section>
    </div>
  );
}
