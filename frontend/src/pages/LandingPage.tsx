import { Link } from 'react-router-dom';
import { BriefcaseBusiness, ShieldCheck } from 'lucide-react';

export default function LandingPage() {
  return <main className="flex min-h-screen items-center justify-center bg-[radial-gradient(circle_at_top,_rgba(59,130,246,0.18),_transparent_55%)] p-4 text-slate-100">
    <section className="w-full max-w-2xl rounded-3xl border border-slate-800 bg-slate-900/80 p-8 text-center shadow-glow backdrop-blur md:p-12">
      <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-2xl bg-blue-500/20 text-blue-400"><ShieldCheck size={28} /></div>
      <h1 className="mt-6 text-3xl font-semibold">SentinelAI</h1>
      <p className="mt-2 text-slate-400">Enterprise LLM Security Gateway</p>
      <p className="mt-10 text-sm font-medium uppercase tracking-[0.2em] text-slate-500">Choose mode</p>
      <div className="mt-5 grid gap-4 md:grid-cols-2">
        <Link to="/login" className="rounded-2xl border border-slate-700 bg-slate-950/60 p-5 text-left transition hover:border-blue-500/50 hover:bg-slate-800"><BriefcaseBusiness className="text-blue-400" size={22} /><p className="mt-4 font-medium">Employee Workspace</p><p className="mt-1 text-sm text-slate-400">Access the enterprise assistant workspace.</p></Link>
        <Link to="/admin/login" className="rounded-2xl border border-slate-700 bg-slate-950/60 p-5 text-left transition hover:border-blue-500/50 hover:bg-slate-800"><ShieldCheck className="text-blue-400" size={22} /><p className="mt-4 font-medium">Administrator Console</p><p className="mt-1 text-sm text-slate-400">Manage the SentinelAI platform.</p></Link>
      </div>
    </section>
  </main>;
}
