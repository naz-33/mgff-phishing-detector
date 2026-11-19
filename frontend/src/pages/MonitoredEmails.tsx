import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import {
  Search,
  Filter,
  ArrowUpDown,
  ChevronLeft,
  ChevronRight,
  ShieldAlert,
  ShieldCheck,
  ShieldQuestion,
  RefreshCw,
  Mail,
  ArrowRight,
} from 'lucide-react';
import { api } from '../services/api';
import type { EmailScanItem } from '../types';

// ─── Three-tier risk helper ───────────────────────────────────────────────────
type RiskTier = 'phishing' | 'suspicious' | 'legitimate';

function getRiskTier(email: EmailScanItem): RiskTier {
  // Prefer the explicit risk_tier field when present (new records).
  if (email.risk_tier === 'High-Confidence Phishing') return 'phishing';
  if (email.risk_tier === 'Suspicious') return 'suspicious';
  if (email.risk_tier === 'Legitimate') return 'legitimate';
  // Fallback for legacy rows without risk_tier: derive from probability.
  const p = email.phishing_probability;
  if (p >= 0.70) return 'phishing';
  if (p >= 0.50) return 'suspicious';
  return 'legitimate';
}

const TIER_BADGE: Record<RiskTier, { label: string; className: string; Icon: React.ElementType }> = {
  phishing: {
    label: 'High-Confidence Phishing',
    className: 'bg-rose-100 text-rose-700 border border-rose-300',
    Icon: ShieldAlert,
  },
  suspicious: {
    label: 'Suspicious — Review',
    className: 'bg-amber-100 text-amber-700 border border-amber-300',
    Icon: ShieldQuestion,
  },
  legitimate: {
    label: 'Legitimate',
    className: 'bg-emerald-100 text-emerald-700 border border-emerald-300',
    Icon: ShieldCheck,
  },
};

const PROB_COLOR: Record<RiskTier, string> = {
  phishing: 'text-rose-600',
  suspicious: 'text-amber-600',
  legitimate: 'text-emerald-600',
};

export const MonitoredEmails: React.FC = () => {
  const [emails, setEmails] = useState<EmailScanItem[]>([]);
  const [total, setTotal] = useState<number>(0);
  const [totalPages, setTotalPages] = useState<number>(1);
  const [page, setPage] = useState<number>(1);
  const [pageSize] = useState<number>(15);

  const [search, setSearch] = useState<string>('');
  const [classification, setClassification] = useState<string>('ALL');
  const [sortBy, setSortBy] = useState<string>('received_at');
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc');

  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const fetchEmails = async () => {
    setLoading(true);
    try {
      const data = await api.getEmails({
        page,
        pageSize,
        search: search.trim() || undefined,
        classification,
        sortBy,
        sortOrder,
      });
      setEmails(data.items);
      setTotal(data.total);
      setTotalPages(data.total_pages);
      setError(null);
    } catch (err: any) {
      setError(err.message || 'Failed to fetch email records');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchEmails();
  }, [page, classification, sortBy, sortOrder]);

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setPage(1);
    fetchEmails();
  };

  const toggleSortOrder = () => {
    setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc');
  };

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 bg-white p-6 rounded-2xl border border-slate-200 shadow-sm">
        <div>
          <h1 className="text-2xl font-extrabold text-slate-900 tracking-tight">
            Monitored Email Logs
          </h1>
          <p className="text-xs text-slate-500 mt-1">
            Real-time feed of scanned emails with individual hybrid ensemble probability scores.
          </p>
        </div>

        <div className="flex items-center space-x-2 text-xs font-semibold px-3 py-1.5 bg-slate-100 rounded-xl text-slate-700">
          <Mail className="w-4 h-4 text-slate-500" />
          <span>Total Logged: {total.toLocaleString()} Emails</span>
        </div>
      </div>

      {/* Filter and Search Bar */}
      <div className="bg-white p-4 rounded-2xl border border-slate-200 shadow-sm flex flex-col md:flex-row items-stretch md:items-center justify-between gap-4">
        {/* Search Input */}
        <form onSubmit={handleSearchSubmit} className="relative flex-1">
          <Search className="w-4 h-4 absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400" />
          <input
            type="text"
            placeholder="Search by subject or sender..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full pl-10 pr-4 py-2 text-xs rounded-xl bg-slate-50 border border-slate-200 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:bg-white transition-all"
          />
        </form>

        {/* Filter Controls */}
        <div className="flex flex-wrap items-center gap-3">
          {/* Classification Dropdown */}
          <div className="flex items-center space-x-1.5">
            <Filter className="w-3.5 h-3.5 text-slate-500" />
            <select
              value={classification}
              onChange={(e) => {
                setClassification(e.target.value);
                setPage(1);
              }}
              className="text-xs py-2 px-3 rounded-xl bg-slate-50 border border-slate-200 text-slate-700 font-medium focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="ALL">All Classifications</option>
              <option value="Phishing">Phishing Only</option>
              <option value="Suspicious">Suspicious — Needs Review</option>
              <option value="Legitimate">Legitimate Only</option>
            </select>
          </div>

          {/* Sort By Field */}
          <div className="flex items-center space-x-1.5">
            <select
              value={sortBy}
              onChange={(e) => {
                setSortBy(e.target.value);
                setPage(1);
              }}
              className="text-xs py-2 px-3 rounded-xl bg-slate-50 border border-slate-200 text-slate-700 font-medium focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="received_at">Sort: Received Date</option>
              <option value="scanned_at">Sort: Scanned Date</option>
              <option value="phishing_probability">Sort: Probability</option>
              <option value="inference_time_ms">Sort: Latency</option>
            </select>

            <button
              onClick={toggleSortOrder}
              className="p-2 rounded-xl bg-slate-50 hover:bg-slate-100 border border-slate-200 text-slate-600 transition-colors"
              title={`Switch to ${sortOrder === 'asc' ? 'Descending' : 'Ascending'}`}
            >
              <ArrowUpDown className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>
      </div>

      {/* Emails Table */}
      <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
        {loading ? (
          <div className="flex flex-col items-center justify-center p-16 space-y-3">
            <RefreshCw className="w-6 h-6 text-blue-600 animate-spin" />
            <p className="text-xs text-slate-500">Loading scanned records...</p>
          </div>
        ) : error ? (
          <div className="p-8 text-center text-rose-600 text-xs">
            <p className="font-semibold">Failed to load emails: {error}</p>
            <button
              onClick={fetchEmails}
              className="mt-3 px-3 py-1.5 bg-rose-600 text-white rounded-lg text-xs font-medium"
            >
              Retry
            </button>
          </div>
        ) : emails.length === 0 ? (
          <div className="p-16 text-center text-slate-400">
            <Mail className="w-10 h-10 mx-auto mb-3 text-slate-300" />
            <p className="text-sm font-semibold text-slate-600">No emails found</p>
            <p className="text-xs text-slate-400 mt-1">
              Try adjusting your search criteria or classification filter.
            </p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse text-xs">
              <thead>
                <tr className="bg-slate-50 border-b border-slate-200 text-slate-600 font-semibold uppercase tracking-wider text-[11px]">
                  <th className="py-3.5 px-6">Classification</th>
                  <th className="py-3.5 px-6">Subject</th>
                  <th className="py-3.5 px-6">Sender</th>
                  <th className="py-3.5 px-6 text-center">Probability</th>
                  <th className="py-3.5 px-6">Received Date</th>
                  <th className="py-3.5 px-6">Scanned At</th>
                  <th className="py-3.5 px-6 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 text-slate-700">
                {emails.map((email) => {
                  const tier = getRiskTier(email);
                  const { label, className: badgeClass, Icon: BadgeIcon } = TIER_BADGE[tier];
                  const probColorClass = PROB_COLOR[tier];
                  return (
                    <tr
                      key={email.id}
                      className="hover:bg-slate-50/80 transition-colors"
                    >
                      {/* Risk-Tier Badge */}
                      <td className="py-3 px-6 whitespace-nowrap">
                        <span className={`inline-flex items-center px-2.5 py-1 rounded-full text-[11px] font-bold ${badgeClass}`}>
                          <BadgeIcon className="w-3.5 h-3.5 mr-1" />
                          {label}
                        </span>
                      </td>

                      {/* Subject */}
                      <td className="py-3 px-6 max-w-xs truncate font-medium text-slate-900" title={email.subject || ''}>
                        {email.subject || '(No Subject)'}
                      </td>

                      {/* Sender */}
                      <td className="py-3 px-6 max-w-xs truncate text-slate-500" title={email.sender || ''}>
                        {email.sender}
                      </td>

                      {/* Phishing Probability */}
                      <td className="py-3 px-6 text-center whitespace-nowrap">
                        <div className="inline-flex items-center space-x-1.5">
                          <span className={`font-mono font-bold ${probColorClass}`}>
                            {(email.phishing_probability * 100).toFixed(1)}%
                          </span>
                        </div>
                      </td>

                      {/* Received Date */}
                      <td className="py-3 px-6 whitespace-nowrap text-slate-500 text-[11px]">
                        {new Date(email.received_at).toLocaleDateString()} {new Date(email.received_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                      </td>

                      {/* Scanned Date */}
                      <td className="py-3 px-6 whitespace-nowrap text-slate-400 text-[11px]">
                        {new Date(email.scanned_at).toLocaleDateString()} {new Date(email.scanned_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                      </td>

                      {/* Details Link */}
                      <td className="py-3 px-6 text-right whitespace-nowrap">
                        <Link
                          to={`/emails/${email.id}`}
                          className="inline-flex items-center space-x-1 px-3 py-1 rounded-lg bg-slate-100 hover:bg-blue-600 text-slate-700 hover:text-white font-semibold transition-colors"
                        >
                          <span>Inspect</span>
                          <ArrowRight className="w-3 h-3" />
                        </Link>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}

        {/* Pagination Controls */}
        <div className="p-4 border-t border-slate-200 bg-slate-50 flex items-center justify-between text-xs text-slate-600">
          <div>
            Showing <span className="font-semibold">{emails.length > 0 ? (page - 1) * pageSize + 1 : 0}</span> to{' '}
            <span className="font-semibold">{Math.min(page * pageSize, total)}</span> of{' '}
            <span className="font-semibold">{total}</span> records
          </div>

          <div className="flex items-center space-x-2">
            <button
              onClick={() => setPage(page - 1)}
              disabled={page <= 1}
              className="p-1.5 rounded-lg bg-white border border-slate-200 text-slate-600 hover:bg-slate-100 disabled:opacity-40 disabled:cursor-not-allowed transition-all"
            >
              <ChevronLeft className="w-4 h-4" />
            </button>
            <span className="font-medium text-slate-700 px-2">
              Page {page} of {totalPages}
            </span>
            <button
              onClick={() => setPage(page + 1)}
              disabled={page >= totalPages}
              className="p-1.5 rounded-lg bg-white border border-slate-200 text-slate-600 hover:bg-slate-100 disabled:opacity-40 disabled:cursor-not-allowed transition-all"
            >
              <ChevronRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
