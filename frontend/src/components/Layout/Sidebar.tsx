import React from 'react';
import { NavLink } from 'react-router-dom';
import {
  LayoutDashboard,
  Mail,
  BarChart3,
  Sliders,
  ShieldAlert,
  ShieldCheck,
  Radio,
} from 'lucide-react';

interface SidebarProps {
  isOpen: boolean;
  onClose: () => void;
}

export const Sidebar: React.FC<SidebarProps> = ({ isOpen, onClose }) => {
  const navItems = [
    { name: 'Dashboard', path: '/', icon: LayoutDashboard },
    { name: 'Monitored Emails', path: '/emails', icon: Mail },
    { name: 'Analytics & Research', path: '/analytics', icon: BarChart3 },
    { name: 'Settings & Status', path: '/settings', icon: Sliders },
  ];

  return (
    <>
      {/* Mobile backdrop */}
      {isOpen && (
        <div
          className="fixed inset-0 z-40 bg-slate-900/60 backdrop-blur-sm lg:hidden"
          onClick={onClose}
        />
      )}

      <aside
        className={`fixed top-0 left-0 z-50 h-screen w-64 bg-slate-900 border-r border-slate-800 text-slate-200 transition-transform duration-300 ease-in-out lg:translate-x-0 ${
          isOpen ? 'translate-x-0' : '-translate-x-full'
        } flex flex-col justify-between`}
      >
        <div>
          {/* Brand Header */}
          <div className="p-6 border-b border-slate-800">
            <div className="flex items-center space-x-3">
              <div className="p-2 bg-blue-600 rounded-lg shadow-lg shadow-blue-500/20 text-white">
                <ShieldAlert className="w-6 h-6" />
              </div>
              <div>
                <h1 className="text-base font-bold tracking-tight text-white leading-tight">
                  ZanderEtAlFishing
                </h1>
                <p className="text-[11px] text-blue-400 font-medium">
                  Hybrid ML Phishing Monitor
                </p>
              </div>
            </div>
          </div>

          {/* Navigation Links */}
          <nav className="p-4 space-y-1.5">
            {navItems.map((item) => {
              const Icon = item.icon;
              return (
                <NavLink
                  key={item.path}
                  to={item.path}
                  end={item.path === '/'}
                  onClick={onClose}
                  className={({ isActive }) =>
                    `flex items-center px-4 py-3 text-sm font-medium rounded-xl transition-all ${
                      isActive
                        ? 'bg-blue-600 text-white shadow-md shadow-blue-600/30'
                        : 'text-slate-400 hover:text-white hover:bg-slate-800/60'
                    }`
                  }
                >
                  <Icon className="w-5 h-5 mr-3 shrink-0" />
                  <span>{item.name}</span>
                </NavLink>
              );
            })}
          </nav>
        </div>

        {/* Footer Info Card */}
        <div className="p-4 m-4 rounded-xl bg-slate-800/80 border border-slate-700/60">
          <div className="flex items-center space-x-2 text-xs font-semibold text-emerald-400 mb-1">
            <Radio className="w-3.5 h-3.5 animate-pulse" />
            <span>Multi-Granularity Engine</span>
          </div>
          <p className="text-[11px] text-slate-400 leading-relaxed">
            LR 50% + LightGBM 50% Soft Blend probability architecture.
          </p>
          <div className="mt-2.5 pt-2 border-t border-slate-700/60 flex items-center justify-between text-[11px] text-slate-400">
            <span>Model v1.0</span>
            <span className="flex items-center text-emerald-400 font-medium">
              <ShieldCheck className="w-3.5 h-3.5 mr-1" /> Active
            </span>
          </div>
        </div>
      </aside>
    </>
  );
};

