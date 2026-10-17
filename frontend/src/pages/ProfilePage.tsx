import { motion } from 'framer-motion';
import { Camera, Clock3, KeyRound, ShieldCheck, User } from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';

export default function ProfilePage() {
  const { user } = useAuth();

  return (
    <div className="grid gap-6 lg:grid-cols-[1.2fr_0.8fr]">
      <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} className="rounded-3xl border border-slate-800 bg-slate-900/70 p-6">
        <div className="flex items-center gap-4">
          <div className="rounded-2xl bg-blue-500/20 p-4 text-blue-400"><User size={24} /></div>
          <div>
            <h2 className="text-xl font-semibold">{user?.name}</h2>
            <p className="text-sm text-slate-400">{user?.email}</p>
          </div>
        </div>

        <div className="mt-6 grid gap-4 sm:grid-cols-2">
          <div className="rounded-2xl border border-slate-800 bg-slate-950/70 p-4">
            <p className="text-sm text-slate-400">Status</p>
            <p className="mt-2 font-medium text-emerald-400">Active</p>
          </div>
        </div>
      </motion.div>

      <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} className="rounded-3xl border border-slate-800 bg-slate-900/70 p-6">
        <div className="flex items-center gap-2 text-blue-300"><ShieldCheck size={18} /> Security Profile</div>
        <div className="mt-4 space-y-3 text-sm text-slate-400">
          <div className="flex items-center gap-2"><KeyRound size={16} /> Change password</div>
          <div className="flex items-center gap-2"><Camera size={16} /> Avatar upload</div>
          <div className="flex items-center gap-2"><Clock3 size={16} /> Recent login activity</div>
        </div>
      </motion.div>
    </div>
  );
}
