import { useState } from 'react';
import { motion } from 'framer-motion';
import { BriefcaseBusiness, Eye, EyeOff, Lock, Mail, ShieldCheck, User } from 'lucide-react';
import { useForm } from 'react-hook-form';
import { z } from 'zod';
import { zodResolver } from '@hookform/resolvers/zod';
import { Link } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';

const schema = z.object({
  name: z.string().min(2, 'Name must be at least 2 characters'),
  email: z.string().email('Enter a valid email'),
  password: z.string().min(8, 'Password must be at least 8 characters'),
  confirm_password: z.string().min(8, 'Confirm your password'),
  requested_role: z.enum(['Employee', 'Manager', 'HR', 'Payroll Administrator']),
}).refine((data) => data.password === data.confirm_password, {
  message: 'Passwords do not match',
  path: ['confirm_password'],
});

type FormValues = z.infer<typeof schema>;

export default function RegisterPage() {
  const { register: registerUser } = useAuth();
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [notice, setNotice] = useState('');
  const [submitError, setSubmitError] = useState('');
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: { requested_role: 'Employee' },
  });

  const onSubmit = async (values: FormValues) => {
    setNotice('');
    setSubmitError('');
    try {
      const result = await registerUser(values);
      if (result.status === 'pending_approval') setNotice(result.message);
    } catch (error) {
      setSubmitError((error as { response?: { data?: { detail?: string } } }).response?.data?.detail || 'Unable to create account.');
    }
  };

  return (
    <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="w-full max-w-lg rounded-3xl border border-slate-800 bg-slate-900/80 p-8 shadow-glow backdrop-blur">
      <div className="mb-6 flex items-center gap-3">
        <div className="rounded-2xl bg-blue-500/20 p-3 text-blue-400"><ShieldCheck size={24} /></div>
        <div>
          <h1 className="text-2xl font-semibold">Create Account</h1>
          <p className="text-sm text-slate-400">Join SentinelAI Security Console</p>
        </div>
      </div>

      {notice && <div className="mb-5 rounded-xl border border-emerald-500/30 bg-emerald-500/10 p-4 text-sm text-emerald-200">{notice} You can sign in after approval.</div>}
      {submitError && <div className="mb-5 rounded-xl border border-rose-500/30 bg-rose-500/10 p-4 text-sm text-rose-200">{submitError}</div>}

      <form className="space-y-4" onSubmit={handleSubmit(onSubmit)} autoComplete="on">
        <label className="block text-sm text-slate-300">
          <span className="mb-2 block">Name</span>
          <div className="flex items-center gap-2 rounded-xl border border-slate-800 bg-slate-950/70 px-3 py-3">
            <User size={16} className="text-slate-500" />
            <input autoComplete="name" {...register('name')} className="w-full bg-transparent outline-none" placeholder="Alex Rivera" />
          </div>
          {errors.name && <p className="mt-1 text-sm text-rose-400">{errors.name.message}</p>}
        </label>

        <label className="block text-sm text-slate-300">
          <span className="mb-2 block">Requested role</span>
          <div className="flex items-center gap-2 rounded-xl border border-slate-800 bg-slate-950/70 px-3 py-3">
            <BriefcaseBusiness size={16} className="text-slate-500" />
            <select {...register('requested_role')} className="w-full bg-transparent outline-none">
              <option>Employee</option>
              <option>Manager</option>
              <option>HR</option>
              <option>Payroll Administrator</option>
            </select>
          </div>
          <p className="mt-1 text-xs text-slate-500">Employee accounts activate immediately. Other roles require administrator approval.</p>
        </label>

        <label className="block text-sm text-slate-300">
          <span className="mb-2 block">Email</span>
          <div className="flex items-center gap-2 rounded-xl border border-slate-800 bg-slate-950/70 px-3 py-3">
            <Mail size={16} className="text-slate-500" />
            <input type="email" autoComplete="email" {...register('email')} className="w-full bg-transparent outline-none" placeholder="alex@company.com" />
          </div>
          {errors.email && <p className="mt-1 text-sm text-rose-400">{errors.email.message}</p>}
        </label>

        <label className="block text-sm text-slate-300">
          <span className="mb-2 block">Password</span>
          <div className="flex items-center gap-2 rounded-xl border border-slate-800 bg-slate-950/70 px-3 py-3">
            <Lock size={16} className="text-slate-500" />
            <input type={showPassword ? 'text' : 'password'} autoComplete="new-password" {...register('password')} className="w-full bg-transparent outline-none" placeholder="••••••••" />
            <button type="button" onClick={() => setShowPassword((value) => !value)} className="text-slate-500">
              {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
            </button>
          </div>
          {errors.password && <p className="mt-1 text-sm text-rose-400">{errors.password.message}</p>}
          <div className="mt-2 h-2 w-full rounded-full bg-slate-800"><div className="h-2 w-3/4 rounded-full bg-blue-500" /></div>
        </label>

        <label className="block text-sm text-slate-300">
          <span className="mb-2 block">Confirm Password</span>
          <div className="flex items-center gap-2 rounded-xl border border-slate-800 bg-slate-950/70 px-3 py-3">
            <Lock size={16} className="text-slate-500" />
            <input type={showConfirmPassword ? 'text' : 'password'} autoComplete="new-password" {...register('confirm_password')} className="w-full bg-transparent outline-none" placeholder="••••••••" />
            <button type="button" onClick={() => setShowConfirmPassword((value) => !value)} className="text-slate-500">
              {showConfirmPassword ? <EyeOff size={16} /> : <Eye size={16} />}
            </button>
          </div>
          {errors.confirm_password && <p className="mt-1 text-sm text-rose-400">{errors.confirm_password.message}</p>}
        </label>

        <button disabled={isSubmitting} className="w-full rounded-xl bg-blue-500 px-4 py-3 font-medium text-white transition hover:bg-blue-400 disabled:opacity-70">
          {isSubmitting ? 'Creating account...' : 'Create Account'}
        </button>
      </form>

      <p className="mt-6 text-center text-sm text-slate-400">
        Already have an account? <Link to="/login" className="text-blue-400">Sign in</Link>
      </p>
    </motion.div>
  );
}
