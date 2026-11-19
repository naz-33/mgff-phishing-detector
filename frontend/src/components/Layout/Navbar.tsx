import React from 'react';
import { Menu, LogOut, ShieldCheck, Mail, User } from 'lucide-react';
import { useAuth } from '../../context/AuthContext';

interface NavbarProps {
  onMenuToggle: () => void;
  mailbox?: string | null;
  scannerStatus?: string;
}

export const Navbar: React.FC<NavbarProps> = ({ onMenuToggle, mailbox, scannerStatus = 'ACTIVE' }) => {
  const { username, logout } = useAuth();

  return (
    <header className="sticky top-0 z-30 flex h-16 w-full items-center justify-between border-b border-slate-200 bg-white/90 backdrop-blur-md px-4 sm:px-6 lg:px-8">
      {/* Mobile Menu Button */}
      <div className="flex items-center space-x-3">
        <button
          type="button"
          onClick={onMenuToggle}
          className="rounded-lg p-2 text-slate-600 hover:bg-slate-100 lg:hidden"
        >
          <Menu className="w-5 h-5" />
        </button>
        <div className="hidden sm:flex items-center space-x-2 text-xs font-medium text-slate-600">
          <span className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-blue-50 text-blue-700 border border-blue-200">
            <Mail className="w-3.5 h-3.5" />
            <span>Target: {mailbox || 'Connected Gmail Inbox'}</span>
          </span>
          <span className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-emerald-50 text-emerald-700 border border-emerald-200">
            <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
            <span>Scanner: {scannerStatus}</span>
          </span>
        </div>
      </div>

      {/* User Controls & Logout */}
      <div className="flex items-center space-x-4">
        <div className="hidden md:flex items-center space-x-2 text-xs text-slate-500">
          <ShieldCheck className="w-4 h-4 text-emerald-600" />
          <span>OAuth 2.0 Read-Only</span>
        </div>

        <div className="h-4 w-px bg-slate-200 hidden md:block"></div>

        <div className="flex items-center space-x-3">
          <div className="flex items-center space-x-2 px-3 py-1.5 rounded-lg bg-slate-100 text-slate-700 text-xs font-semibold">
            <User className="w-3.5 h-3.5 text-slate-500" />
            <span>{username || 'Administrator'}</span>
          </div>

          <button
            onClick={logout}
            className="flex items-center space-x-1.5 px-3 py-1.5 rounded-lg text-xs font-medium text-rose-600 hover:bg-rose-50 border border-transparent hover:border-rose-200 transition-colors"
            title="Log out of monitoring session"
          >
            <LogOut className="w-3.5 h-3.5" />
            <span className="hidden sm:inline">Logout</span>
          </button>
        </div>
      </div>
    </header>
  );
};

