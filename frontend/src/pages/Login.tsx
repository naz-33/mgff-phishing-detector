import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { ShieldAlert, Lock, User, AlertCircle, ArrowRight, CheckCircle2 } from 'lucide-react';
import { api } from '../services/api';
import { useAuth } from '../context/AuthContext';

export const Login: React.FC = () => {
  const [username, setUsername] = useState('admin');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const navigate = useNavigate();
  const { login } = useAuth();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);

    try {
      const data = await api.login(username, password);
      login(data.access_token, data.username);
      navigate('/');
    } catch (err: any) {
      setError(err.message || 'Authentication failed. Please verify credentials.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-900 flex items-center justify-center p-4 relative overflow-hidden">
      {/* Background radial glow */}
      <div className="absolute w-[500px] h-[500px] bg-blue-600/10 rounded-full blur-3xl pointer-events-none -top-24 -left-24"></div>
      <div className="absolute w-[500px] h-[500px] bg-emerald-600/10 rounded-full blur-3xl pointer-events-none -bottom-24 -right-24"></div>

      <div className="w-full max-w-md z-10">
        <div className="bg-slate-800/90 border border-slate-700/80 rounded-2xl shadow-2xl p-8 backdrop-blur-xl">
          {/* Logo & Header */}
          <div className="text-center mb-8">
            <div className="inline-flex p-3 bg-blue-600 rounded-xl shadow-lg shadow-blue-500/20 text-white mb-3">
              <ShieldAlert className="w-8 h-8" />
            </div>
            <h1 className="text-2xl font-bold tracking-tight text-white">
              ZanderEtAlFishing
            </h1>
            <p className="text-xs text-slate-400 mt-1.5 leading-relaxed">
              Automated Phishing Email Detection &amp; Monitoring Dashboard
            </p>
          </div>

          {error && (
            <div className="mb-6 p-3.5 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-400 text-xs flex items-center space-x-2.5">
              <AlertCircle className="w-4 h-4 shrink-0 text-rose-400" />
              <span>{error}</span>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-2">
                Administrator Username
              </label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-400">
                  <User className="w-4 h-4" />
                </div>
                <input
                  type="text"
                  required
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  placeholder="admin"
                  className="w-full pl-10 pr-4 py-2.5 rounded-xl bg-slate-900/80 border border-slate-700 text-slate-100 placeholder-slate-500 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all"
                />
              </div>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-2">
                Password
              </label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-400">
                  <Lock className="w-4 h-4" />
                </div>
                <input
                  type="password"
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••••••"
                  className="w-full pl-10 pr-4 py-2.5 rounded-xl bg-slate-900/80 border border-slate-700 text-slate-100 placeholder-slate-500 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all"
                />
              </div>
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full mt-2 py-3 px-4 rounded-xl bg-blue-600 hover:bg-blue-500 text-white font-medium text-sm shadow-lg shadow-blue-600/30 flex items-center justify-center space-x-2 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <span>{loading ? 'Authenticating...' : 'Sign In to Dashboard'}</span>
              {!loading && <ArrowRight className="w-4 h-4" />}
            </button>
          </form>

          {/* Thesis Prototype Credentials Hint */}
          <div className="mt-6 pt-5 border-t border-slate-700/60 text-[11px] text-slate-400">
            <div className="flex items-center space-x-1.5 text-slate-300 font-semibold mb-1">
              <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
              <span>Thesis Prototype Credentials</span>
            </div>
            <p>
              Default Admin: <code className="text-blue-300">admin</code> | Default Password: <code className="text-blue-300">ZanderAdmin2026!</code>
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};

