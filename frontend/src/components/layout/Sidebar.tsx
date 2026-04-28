import React from 'react';
import { NavLink } from 'react-router-dom';
import { 
  PlusCircle, 
  LayoutDashboard, 
  Search, 
  Settings, 
  ShieldCheck
} from 'lucide-react';
import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';

function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

const Sidebar: React.FC = () => {
  const navItems = [
    { to: '/new-audit', icon: PlusCircle, label: 'New Audit' },
    { to: '/dashboard', icon: LayoutDashboard, label: 'Audit History' },
    { to: '/scorecards', icon: Search, label: 'Counterfactual Explorer' },
    { to: '/settings', icon: Settings, label: 'Settings' },
  ];

  return (
    <div className="w-64 bg-slate-900 text-white flex flex-col h-screen fixed left-0 top-0">
      <div className="p-8 flex items-center gap-3">
        <div className="bg-primary p-2 rounded-lg">
          <ShieldCheck className="text-white h-6 w-6" />
        </div>
        <span className="text-2xl font-black tracking-tight italic">FairAI</span>
      </div>
      
      <nav className="flex-1 mt-6">
        <ul className="space-y-1 px-4">
          {navItems.map((item) => (
            <li key={item.to}>
              <NavLink
                to={item.to}
                className={({ isActive }) => cn(
                  "flex items-center gap-3 px-4 py-3 rounded-xl transition-all",
                  isActive 
                    ? "bg-primary text-white shadow-lg shadow-primary/20" 
                    : "text-slate-400 hover:text-white hover:bg-slate-800/50"
                )}
              >
                <item.icon size={20} />
                <span className="font-semibold">{item.label}</span>
              </NavLink>
            </li>
          ))}
        </ul>
      </nav>
      
      <div className="p-6 border-t border-slate-800/50">
        <div className="flex items-center gap-3 px-2 py-1">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-primary to-indigo-600 flex items-center justify-center font-bold text-sm shadow-inner">
            AD
          </div>
          <div className="flex flex-col overflow-hidden">
            <span className="text-sm font-bold text-slate-100">Admin User</span>
            <span className="text-[10px] text-slate-500 truncate font-medium uppercase tracking-wider">Enterprise Tier</span>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Sidebar;
