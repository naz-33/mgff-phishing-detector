import React, { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import {
  ArrowLeft,
  ShieldAlert,
  ShieldCheck,
  ShieldQuestion,
  Mail,
  Zap,
  Layers,
  Cpu,
  Info,
  AlertTriangle,
  FileText,
  Copy,
  Check,
  CloudDownload,
} from 'lucide-react';
import { api } from '../services/api';
import type { EmailScanDetail } from '../types';

// ─── Three-tier risk helper ───────────────────────────────────────────────────
type RiskTier = 'phishing' | 'suspicious' | 'legitimate';

function getRiskTier(email: EmailScanDetail): RiskTier {
  if (email.risk_tier === 'High-Confidence Phishing') return 'phishing';
  if (email.risk_tier === 'Suspicious') return 'suspicious';
  if (email.risk_tier === 'Legitimate') return 'legitimate';
  const p = email.phishing_probability;
  const hct = email.high_confidence_threshold ?? 0.70;
  const lt = email.threshold ?? 0.50;
  if (p >= hct) return 'phishing';
  if (p >= lt) return 'suspicious';
  return 'legitimate';
}

export const EmailDetail: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const [email, setEmail] = useState<EmailScanDetail | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState<boolean>(false);
  const [fetchingBody, setFetchingBody] = useState<boolean>(false);
  const [fetchError, setFetchError] = useState<string | null>(null);

  const handleCopyBody = () => {
    if (!email?.body) return;
    navigator.clipboard.writeText(email.body);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleFetchBodyOnDemand = async () => {
    if (!email) return;
    setFetchingBody(true);
    setFetchError(null);
    try {
      const updated = await api.fetchEmailBody(email.id);
      setEmail(updated);
    } catch (err: any) {
      setFetchError(err.message || 'Failed to fetch email body from Gmail');
    } finally {
      setFetchingBody(false);
    }
  };

  useEffect(() => {
    if (!id) return;
    setLoading(true);
    api.getEmailDetail(parseInt(id, 10))
      .then((data) => {
        setEmail(data);
        setError(null);
      })
      .catch((err) => {
        setError(err.message || 'Failed to load email detection details');
      })
      .finally(() => {
        setLoading(false);
      });
  }, [id]);

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] space-y-3">
        <div className="w-8 h-8 border-4 border-blue-600 border-t-transparent rounded-full animate-spin"></div>
        <p className="text-xs text-slate-500 font-medium">Loading detection analysis...</p>
      </div>
    );
  }

  if (error || !email) {
    return (
      <div className="p-6 rounded-2xl bg-rose-50 border border-rose-200 text-rose-800">
        <h2 className="text-sm font-bold flex items-center gap-2">
          <AlertTriangle className="w-4 h-4 text-rose-600" />
          Detection Details Unavailable
        </h2>
        <p className="mt-2 text-xs text-rose-600">{error || 'Email record not found.'}</p>
        <Link
          to="/emails"
          className="mt-4 inline-flex items-center space-x-1.5 px-3 py-1.5 bg-rose-600 text-white rounded-xl text-xs font-semibold"
        >
          <ArrowLeft className="w-3.5 h-3.5" />
          <span>Back to Monitored Emails</span>
        </Link>
      </div>
    );
  }

  const tier = getRiskTier(email);

  return (
    <div className="space-y-6">
      {/* Back button & Action Header */}
      <div className="flex items-center justify-between">
        <Link
          to="/emails"
          className="inline-flex items-center space-x-2 text-xs font-semibold text-slate-600 hover:text-slate-900 bg-white px-3 py-2 rounded-xl border border-slate-200 transition-colors shadow-sm"
        >
          <ArrowLeft className="w-4 h-4" />
          <span>Back to Email Log</span>
        </Link>

        <span className="text-xs font-mono text-slate-400">
          Scan ID #{email.id} • Message ID: {email.gmail_message_id}
        </span>
      </div>

      {/* Main Classification Banner */}
      <div
        className={`p-6 rounded-2xl border shadow-sm flex flex-col md:flex-row md:items-center justify-between gap-6 ${
          tier === 'phishing'
            ? 'bg-rose-50/70 border-rose-200 text-rose-950'
            : tier === 'suspicious'
            ? 'bg-amber-50/70 border-amber-200 text-amber-950'
            : 'bg-emerald-50/70 border-emerald-200 text-emerald-950'
        }`}
      >
        <div className="flex items-start space-x-4">
          <div
            className={`p-3 rounded-2xl ${
              tier === 'phishing'
                ? 'bg-rose-600 text-white shadow-lg shadow-rose-600/30'
                : tier === 'suspicious'
                ? 'bg-amber-500 text-white shadow-lg shadow-amber-500/30'
                : 'bg-emerald-600 text-white shadow-lg shadow-emerald-600/30'
            }`}
          >
            {tier === 'phishing' ? (
              <ShieldAlert className="w-8 h-8" />
            ) : tier === 'suspicious' ? (
              <ShieldQuestion className="w-8 h-8" />
            ) : (
              <ShieldCheck className="w-8 h-8" />
            )}
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <span
                className={`text-xs font-bold uppercase tracking-wider px-2.5 py-0.5 rounded-full ${
                  tier === 'phishing'
                    ? 'bg-rose-200 text-rose-800'
                    : tier === 'suspicious'
                    ? 'bg-amber-200 text-amber-800'
                    : 'bg-emerald-200 text-emerald-800'
                }`}
              >
                Verdict: {tier === 'phishing' ? 'High-Confidence Phishing' : tier === 'suspicious' ? 'Suspicious (Needs Review)' : 'Legitimate'}
              </span>
              <span className="text-xs text-slate-500">
                Model: <span className="font-semibold text-slate-700">{email.model_version}</span>
              </span>
            </div>
            <h1 className="text-2xl font-black mt-1.5 tracking-tight">
              {tier === 'phishing'
                ? 'High-Confidence Phishing Threat Flagged'
                : tier === 'suspicious'
                ? 'Suspicious Notification Flagged for Review'
                : 'Legitimate Email Verified'}
            </h1>
            <p className="text-xs text-slate-600 mt-1">
              Final hybrid ensemble probability: <span className="font-bold">{(email.phishing_probability * 100).toFixed(2)}%</span>{' '}
              (Cutoffs: Legitimate &lt; {email.threshold.toFixed(2)}, High-Conf ≥ {(email.high_confidence_threshold ?? 0.70).toFixed(2)})
            </p>
          </div>
        </div>

        {/* Probability Gauge Box */}
        <div className="bg-white/90 p-4 rounded-xl border border-slate-200/80 shadow-sm shrink-0 min-w-[200px] text-center">
          <p className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider">Threat Probability</p>
          <div className="text-3xl font-black font-mono mt-1 text-slate-900">
            {(email.phishing_probability * 100).toFixed(2)}%
          </div>
          <div className="w-full bg-slate-100 rounded-full h-2 mt-2 overflow-hidden">
            <div
              className={`h-full rounded-full transition-all duration-500 ${
                tier === 'phishing' ? 'bg-rose-600' : tier === 'suspicious' ? 'bg-amber-500' : 'bg-emerald-500'
              }`}
              style={{ width: `${Math.min(100, Math.max(0, email.phishing_probability * 100))}%` }}
            ></div>
          </div>
          <p className="text-[10px] text-slate-400 mt-1">
            {tier === 'phishing'
              ? 'Exceeds 0.70 high-confidence cutoff'
              : tier === 'suspicious'
              ? 'Borderline 0.50–0.70 review zone'
              : 'Below 0.50 decision threshold'}
          </p>
        </div>
      </div>

      {/* Grid: Email Metadata & Ensemble Breakdown */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Email Metadata Card */}
        <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm space-y-4">
          <h2 className="text-sm font-bold text-slate-900 tracking-tight flex items-center gap-2">
            <Mail className="w-4 h-4 text-blue-600" />
            Email Header Metadata
          </h2>

          <div className="space-y-3 text-xs">
            <div className="p-3 rounded-xl bg-slate-50 border border-slate-100">
              <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider block mb-0.5">Subject</span>
              <p className="font-bold text-slate-900 break-words">{email.subject || '(No Subject)'}</p>
            </div>

            <div className="p-3 rounded-xl bg-slate-50 border border-slate-100">
              <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider block mb-0.5">Sender</span>
              <p className="font-medium text-slate-800 break-words">{email.sender || 'Unknown Sender'}</p>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div className="p-3 rounded-xl bg-slate-50 border border-slate-100">
                <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider block mb-0.5">Received Date</span>
                <p className="text-slate-700 font-medium">{new Date(email.received_at).toLocaleString()}</p>
              </div>
              <div className="p-3 rounded-xl bg-slate-50 border border-slate-100">
                <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider block mb-0.5">Scanned Date</span>
                <p className="text-slate-700 font-medium">{new Date(email.scanned_at).toLocaleString()}</p>
              </div>
            </div>

            <div className="p-3 rounded-xl bg-slate-50 border border-slate-100 flex items-center justify-between">
              <div>
                <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider block">Inference Latency</span>
                <p className="text-sm font-mono font-bold text-slate-800">{email.inference_time_ms.toFixed(2)} ms</p>
              </div>
              <Zap className="w-4 h-4 text-amber-500" />
            </div>

            {/* Gateway Authentication Trust Signals */}
            <div className="p-3 rounded-xl bg-slate-50 border border-slate-100">
              <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider block mb-2">
                Gateway Authentication Verification (SPF / DKIM / DMARC)
              </span>
              <div className="flex flex-wrap gap-2">
                <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs font-semibold ${
                  email.spf_pass === true ? 'bg-emerald-50 text-emerald-700 border border-emerald-200' :
                  email.spf_pass === false ? 'bg-rose-50 text-rose-700 border border-rose-200' :
                  'bg-slate-100 text-slate-500 border border-slate-200'
                }`}>
                  <ShieldCheck className="w-3.5 h-3.5" />
                  SPF: {email.spf_pass === true ? 'Passed' : email.spf_pass === false ? 'Failed' : 'N/A'}
                </span>
                <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs font-semibold ${
                  email.dkim_pass === true ? 'bg-blue-50 text-blue-700 border border-blue-200' :
                  email.dkim_pass === false ? 'bg-rose-50 text-rose-700 border border-rose-200' :
                  'bg-slate-100 text-slate-500 border border-slate-200'
                }`}>
                  <ShieldCheck className="w-3.5 h-3.5" />
                  DKIM: {email.dkim_pass === true ? 'Passed' : email.dkim_pass === false ? 'Failed' : 'N/A'}
                </span>
                <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs font-semibold ${
                  email.dmarc_pass === true ? 'bg-indigo-50 text-indigo-700 border border-indigo-200' :
                  email.dmarc_pass === false ? 'bg-rose-50 text-rose-700 border border-rose-200' :
                  'bg-slate-100 text-slate-500 border border-slate-200'
                }`}>
                  <ShieldCheck className="w-3.5 h-3.5" />
                  DMARC: {email.dmarc_pass === true ? 'Passed' : email.dmarc_pass === false ? 'Failed' : 'N/A'}
                </span>
              </div>
            </div>
          </div>

          {/* Email Body Content Card / Section */}
          <div className="pt-2 space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider flex items-center gap-1.5">
                <FileText className="w-3.5 h-3.5 text-blue-600" />
                Email Body Content
              </span>
              {email.body && email.body.trim() ? (
                <div className="flex items-center space-x-2">
                  <span className="text-[10px] text-slate-400 font-mono">
                    {email.body.length.toLocaleString()} chars
                  </span>
                  <button
                    type="button"
                    onClick={handleCopyBody}
                    className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[11px] font-medium bg-slate-100 hover:bg-slate-200 text-slate-600 hover:text-slate-900 border border-slate-200 transition-colors"
                    title="Copy email body to clipboard"
                  >
                    {copied ? (
                      <>
                        <Check className="w-3 h-3 text-emerald-600" />
                        <span className="text-emerald-600 font-semibold">Copied</span>
                      </>
                    ) : (
                      <>
                        <Copy className="w-3 h-3 text-slate-500" />
                        <span>Copy</span>
                      </>
                    )}
                  </button>
                </div>
              ) : null}
            </div>

            {email.body && email.body.trim() ? (
              <div className="max-h-72 overflow-y-auto rounded-xl bg-slate-50 p-3.5 border border-slate-200 text-xs font-mono text-slate-800 whitespace-pre-wrap break-words leading-relaxed select-text shadow-inner">
                {email.body}
              </div>
            ) : (
              <div className="py-5 px-4 rounded-xl bg-slate-50 border border-dashed border-slate-200 text-center space-y-2.5">
                <p className="text-xs text-slate-400 italic flex items-center justify-center gap-1.5">
                  <Info className="w-3.5 h-3.5 text-slate-400 shrink-0" />
                  Email body not captured for older scans
                </p>
                <button
                  type="button"
                  disabled={fetchingBody}
                  onClick={handleFetchBodyOnDemand}
                  className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold bg-blue-50 text-blue-700 hover:bg-blue-100 border border-blue-200 transition-colors disabled:opacity-50 shadow-sm cursor-pointer"
                >
                  {fetchingBody ? (
                    <>
                      <div className="w-3.5 h-3.5 border-2 border-blue-600 border-t-transparent rounded-full animate-spin"></div>
                      <span>Fetching from Gmail...</span>
                    </>
                  ) : (
                    <>
                      <CloudDownload className="w-3.5 h-3.5 text-blue-600" />
                      <span>Fetch Body from Gmail</span>
                    </>
                  )}
                </button>
                {fetchError && (
                  <p className="text-[11px] text-rose-600 font-medium">{fetchError}</p>
                )}
              </div>
            )}
          </div>
        </div>

        {/* 50/50 Ensemble Probability Decomposition Card */}
        <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm space-y-4">
          <h2 className="text-sm font-bold text-slate-900 tracking-tight flex items-center gap-2">
            <Cpu className="w-4 h-4 text-blue-600" />
            Hybrid Ensemble Decomposition
          </h2>

          <p className="text-xs text-slate-500 leading-relaxed">
            The hybrid architecture combines predictions from two distinct algorithmic paradigms using soft probability blending:
          </p>

          <div className="space-y-3 text-xs">
            {/* Stream 1: Logistic Regression */}
            <div className="p-4 rounded-xl border border-slate-200 bg-slate-50">
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center space-x-2">
                  <span className="w-2.5 h-2.5 rounded-full bg-blue-600"></span>
                  <span className="font-bold text-slate-800">Stream 1: Logistic Regression</span>
                </div>
                <span className="px-2 py-0.5 bg-blue-100 text-blue-700 rounded-md font-semibold text-[11px]">
                  Weight: {(email.ensemble_weights.logistic_regression * 100).toFixed(0)}%
                </span>
              </div>
              <div className="flex items-center justify-between mt-2">
                <span className="text-slate-500">Positive Probability:</span>
                <span className="font-mono font-bold text-slate-900 text-sm">
                  {(email.logistic_regression_probability * 100).toFixed(2)}%
                </span>
              </div>
              <div className="w-full bg-slate-200 rounded-full h-1.5 mt-2">
                <div
                  className="bg-blue-600 h-1.5 rounded-full"
                  style={{ width: `${Math.min(100, Math.max(0, email.logistic_regression_probability * 100))}%` }}
                ></div>
              </div>
            </div>

            {/* Stream 2: LightGBM */}
            <div className="p-4 rounded-xl border border-slate-200 bg-slate-50">
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center space-x-2">
                  <span className="w-2.5 h-2.5 rounded-full bg-emerald-600"></span>
                  <span className="font-bold text-slate-800">Stream 2: LightGBM (Gradient Boosted Trees)</span>
                </div>
                <span className="px-2 py-0.5 bg-emerald-100 text-emerald-700 rounded-md font-semibold text-[11px]">
                  Weight: {(email.ensemble_weights.lightgbm * 100).toFixed(0)}%
                </span>
              </div>
              <div className="flex items-center justify-between mt-2">
                <span className="text-slate-500">Positive Probability:</span>
                <span className="font-mono font-bold text-slate-900 text-sm">
                  {(email.lightgbm_probability * 100).toFixed(2)}%
                </span>
              </div>
              <div className="w-full bg-slate-200 rounded-full h-1.5 mt-2">
                <div
                  className="bg-emerald-600 h-1.5 rounded-full"
                  style={{ width: `${Math.min(100, Math.max(0, email.lightgbm_probability * 100))}%` }}
                ></div>
              </div>
            </div>

            {/* Mathematical Formula Explanation */}
            <div className="p-3 rounded-xl bg-blue-50/60 border border-blue-100 text-blue-900 font-mono text-[11px]">
              P_final = (0.50 × {email.logistic_regression_probability.toFixed(4)}) + (0.50 × {email.lightgbm_probability.toFixed(4)}) = <span className="font-bold">{email.phishing_probability.toFixed(4)}</span>
            </div>
          </div>
        </div>
      </div>

      {/* Feature Engineering Architecture Specs */}
      <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm space-y-4">
        <h2 className="text-sm font-bold text-slate-900 tracking-tight flex items-center gap-2">
          <Layers className="w-4 h-4 text-blue-600" />
          Multi-Granularity Feature Extraction Pipeline
        </h2>

        <p className="text-xs text-slate-500">
          This email was transformed and vectorized across multiple representations prior to classification:
        </p>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-xs">
          <div className="p-4 rounded-xl border border-slate-200 bg-slate-50">
            <h3 className="font-bold text-slate-800 mb-1">1. Lexical Word-Level TF-IDF</h3>
            <p className="text-slate-500 text-[11px] leading-relaxed">
              10,000 top n-gram features (1-2 words). Lemmatized with POS tagging, sublinear TF scaling, and stopword removal.
            </p>
          </div>

          <div className="p-4 rounded-xl border border-slate-200 bg-slate-50">
            <h3 className="font-bold text-slate-800 mb-1">2. Lexical Char-Level TF-IDF</h3>
            <p className="text-slate-500 text-[11px] leading-relaxed">
              5,000 sub-word character n-grams (3-5 characters) capturing obfuscation, typo-squatting, and anomalous token patterns.
            </p>
          </div>

          <div className="p-4 rounded-xl border border-slate-200 bg-slate-50">
            <h3 className="font-bold text-slate-800 mb-1">3. Nine Stylometric Features</h3>
            <p className="text-slate-500 text-[11px] leading-relaxed">
              Shannon character entropy, URL counts, uppercase ratio, digit frequency, punctuation count (!/?), and urgency keyword density.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};
