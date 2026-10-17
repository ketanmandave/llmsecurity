import { useState } from 'react';
import { motion } from 'framer-motion';
import { Eye, EyeOff, Lock, Mail, ShieldCheck } from 'lucide-react';
import { useForm } from 'react-hook-form';
import { z } from 'zod';
import { zodResolver } from '@hookform/resolvers/zod';
import { Link } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';

const employeeRoles = ['Employee', 'Manager', 'HR', 'Payroll Administrator', 'Security Analyst'] as const;
const schema = z.object({ email: z.string().email('Enter a valid email'), password: z.string().min(1, 'Enter your password'), login_as: z.string().optional() });
type FormValues = z.infer<typeof schema>;

export default function LoginPage({ portal }: { portal: 'employee' | 'administrator' }) {
  const { login } = useAuth();
  const [showPassword, setShowPassword] = useState(false);
  const [loginError, setLoginError] = useState('');
  const employeePortal = portal === 'employee';
  const { register, handleSubmit, formState: { errors, isSubmitting } } = useForm<FormValues>({ resolver: zodResolver(schema), defaultValues: { login_as: 'Employee' } });
  const onSubmit = async (values: FormValues) => {
    setLoginError('');
    try { await login({ ...values, login_as: employeePortal ? values.login_as : undefined, portal }); }
    catch { setLoginError('Invalid credentials'); }
  };
  return <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="w-full max-w-md rounded-3xl border border-slate-800 bg-slate-900/80 p-8 shadow-glow backdrop-blur">
    {loginError && <p role="alert" className="mb-5 rounded-xl border border-rose-500/30 bg-rose-500/10 p-3 text-sm text-rose-200">{loginError}</p>}
    <div className="mb-6 flex items-center gap-3"><div className="rounded-2xl bg-blue-500/20 p-3 text-blue-400"><ShieldCheck size={24} /></div><div><h1 className="text-2xl font-semibold">SentinelAI</h1><p className="text-sm text-slate-400">{employeePortal ? 'Employee Workspace' : 'Administrator Console'}</p></div></div>
    <form className="space-y-4" onSubmit={handleSubmit(onSubmit)} autoComplete="on">
      <label className="block text-sm text-slate-300"><span className="mb-2 block">Email</span><div className="flex items-center gap-2 rounded-xl border border-slate-800 bg-slate-950/70 px-3 py-3"><Mail size={16} className="text-slate-500" /><input type="email" autoComplete="username" {...register('email', { onChange: () => setLoginError('') })} className="w-full bg-transparent outline-none" /></div>{errors.email && <p className="mt-1 text-sm text-rose-400">{errors.email.message}</p>}</label>
      {employeePortal && <label className="block text-sm text-slate-300"><span className="mb-2 block">Login As</span><select {...register('login_as', { onChange: () => setLoginError('') })} className="w-full rounded-xl border border-slate-800 bg-slate-950/70 px-3 py-3 outline-none">{employeeRoles.map((role) => <option key={role}>{role}</option>)}</select></label>}
      <label className="block text-sm text-slate-300"><span className="mb-2 block">Password</span><div className="flex items-center gap-2 rounded-xl border border-slate-800 bg-slate-950/70 px-3 py-3"><Lock size={16} className="text-slate-500" /><input type={showPassword ? 'text' : 'password'} autoComplete="current-password" {...register('password', { onChange: () => setLoginError('') })} className="w-full bg-transparent outline-none" /><button type="button" onClick={() => setShowPassword((value) => !value)} className="text-slate-500">{showPassword ? <EyeOff size={16} /> : <Eye size={16} />}</button></div>{errors.password && <p className="mt-1 text-sm text-rose-400">{errors.password.message}</p>}</label>
      <p className="text-xs text-slate-500">This login is isolated to the current browser tab.</p><button disabled={isSubmitting} className="w-full rounded-xl bg-blue-500 px-4 py-3 font-medium text-white disabled:opacity-70">{isSubmitting ? 'Signing in...' : 'Sign In'}</button>
    </form>
    {employeePortal && <p className="mt-6 text-center text-sm text-slate-400">New to SentinelAI? <Link to="/register" className="text-blue-400">Create account</Link></p>}
  </motion.div>;
}
