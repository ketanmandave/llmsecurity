import { motion } from 'framer-motion';
import { Save } from 'lucide-react';

export default function SettingsPage() {
  return (
    <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} className="rounded-3xl border border-slate-800 bg-slate-900/70 p-6">
      <h2 className="text-xl font-semibold">Application Settings</h2>
      <div className="mt-6 grid gap-4 md:grid-cols-2">
        <label className="block text-sm text-slate-300">
          <span className="mb-2 block">Application Name</span>
          <input defaultValue="SentinelAI" className="w-full rounded-xl border border-slate-800 bg-slate-950/70 px-3 py-3 outline-none" />
        </label>
        <label className="block text-sm text-slate-300">
          <span className="mb-2 block">Theme</span>
          <select defaultValue="dark" className="w-full rounded-xl border border-slate-800 bg-slate-950/70 px-3 py-3 outline-none">
            <option value="dark">Dark</option>
            <option value="light">Light</option>
          </select>
        </label>
        <label className="block text-sm text-slate-300">
          <span className="mb-2 block">Language</span>
          <input defaultValue="English" className="w-full rounded-xl border border-slate-800 bg-slate-950/70 px-3 py-3 outline-none" />
        </label>
        <label className="block text-sm text-slate-300">
          <span className="mb-2 block">Session Timeout</span>
          <input defaultValue="30" className="w-full rounded-xl border border-slate-800 bg-slate-950/70 px-3 py-3 outline-none" />
        </label>
      </div>
      <button className="mt-6 inline-flex items-center gap-2 rounded-xl bg-blue-500 px-4 py-3 font-medium text-white hover:bg-blue-400">
        <Save size={16} /> Save Settings
      </button>
    </motion.div>
  );
}
