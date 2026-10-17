export default function ForbiddenPage() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-slate-950 p-4 text-center text-slate-100">
      <div className="rounded-3xl border border-slate-800 bg-slate-900/80 p-8 shadow-glow">
        <h1 className="text-3xl font-semibold">403</h1>
        <p className="mt-2 text-slate-400">You do not have permission to view this resource.</p>
      </div>
    </div>
  );
}
