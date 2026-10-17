import { NavLink, Outlet } from 'react-router-dom';
import { Files, LayoutDashboard, LogOut, Settings, ShieldCheck, UserCircle2, Users, FileText } from 'lucide-react';
import { motion } from 'framer-motion';
import { useAuth } from '../contexts/AuthContext';

const links = [
  { to: '/dashboard', label: 'Dashboard', icon: LayoutDashboard },
  { to: '/users', label: 'Users', icon: Users },
  { to: '/documents', label: 'Documents', icon: Files },
  { to: '/audit-logs', label: 'Audit Logs', icon: FileText },
  { to: '/settings', label: 'Settings', icon: Settings },
  { to: '/profile', label: 'Profile', icon: UserCircle2 },
];

export default function ProtectedLayout() {
  const { user, logout } = useAuth();

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100">
      <div className="flex flex-col lg:flex-row">
        <aside className="w-full border-b border-slate-800/80 bg-slate-900/70 p-4 backdrop-blur lg:min-h-screen lg:w-72 lg:border-b-0 lg:border-r">
          <div className="mb-6 flex items-center gap-3 rounded-2xl border border-slate-800 bg-slate-800/70 p-4">
            <div className="rounded-xl bg-blue-500/20 p-2 text-blue-400"><ShieldCheck size={20} /></div>
            <div>
              <p className="text-sm font-semibold">SentinelAI</p>
              <p className="text-xs text-slate-400">Enterprise Security Gateway</p>
            </div>
          </div>

          <nav className="space-y-2">
            {links.map(({ to, label, icon: Icon }) => (
              <NavLink key={to} to={to} className={({ isActive }) => `flex items-center gap-3 rounded-xl px-3 py-3 text-sm transition ${isActive ? 'bg-blue-500/20 text-blue-300' : 'text-slate-400 hover:bg-slate-800 hover:text-slate-100'}`}>
                <Icon size={18} /> {label}
              </NavLink>
            ))}
          </nav>

          <button onClick={() => { void logout(); }} className="mt-8 flex w-full items-center gap-3 rounded-xl border border-slate-800 px-3 py-3 text-sm text-slate-300 hover:bg-slate-800">
            <LogOut size={18} /> Logout
          </button>
        </aside>

        <main className="flex-1 p-4 md:p-8">
          <motion.header initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }} className="mb-6 flex flex-col gap-2 rounded-2xl border border-slate-800 bg-slate-900/70 p-4 shadow-glow backdrop-blur md:flex-row md:items-center md:justify-between">
            <div>
              <p className="text-sm text-slate-400">Secure operations console</p>
              <h1 className="text-xl font-semibold">Welcome back, {user?.name || 'Administrator'}</h1>
            </div>
            <div className="flex items-center gap-3">
              <div className="rounded-full border border-blue-500/20 bg-blue-500/10 px-3 py-1 text-sm text-blue-300">
                {user?.email}
              </div>

              {['/dashboard', '/audit-logs'].includes(window.location.pathname) && (
                <button
                  onClick={() => window.dispatchEvent(new Event('dashboard-refresh'))}
                  className="rounded-lg border border-slate-700 px-3 py-2 text-sm text-slate-300 transition hover:bg-slate-800"
                >
                  Refresh data
                </button>
              )}
            </div>
          </motion.header>
          <Outlet />
        </main>
      </div>
    </div>
  );
}
