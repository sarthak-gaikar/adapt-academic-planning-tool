import React from 'react';
import { Link, useNavigate, useLocation } from 'react-router-dom';
import { GraduationCap, LogOut, User as UserIcon, BookOpen, Sparkles } from 'lucide-react';
import { useAuth } from '../../context/AuthContext';

export const Navbar = () => {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  return (
    <header className="sticky top-0 z-40 bg-slate-950/80 backdrop-blur-md border-b border-slate-800/80 px-6 py-3.5 flex items-center justify-between">
      <div className="flex items-center gap-8">
        <Link to="/" className="flex items-center gap-2.5 group">
          <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-brand-600 to-brand-400 flex items-center justify-center shadow-lg shadow-brand-500/20 group-hover:scale-105 transition">
            <GraduationCap className="w-5 h-5 text-white" />
          </div>
          <div>
            <span className="font-extrabold text-lg tracking-tight text-white flex items-center gap-1.5">
              ADAPT <span className="text-[10px] px-1.5 py-0.5 bg-brand-500/20 text-brand-400 rounded-md font-mono font-medium border border-brand-500/30">AI OBE</span>
            </span>
          </div>
        </Link>

        {user && (
          <nav className="hidden md:flex items-center gap-1 text-sm font-medium">
            <Link
              to="/dashboard"
              className={`px-3 py-1.5 rounded-lg transition ${
                location.pathname === '/dashboard'
                  ? 'bg-slate-800 text-brand-400'
                  : 'text-slate-400 hover:text-white hover:bg-slate-900'
              }`}
            >
              Dashboard
            </Link>
            <Link
              to="/subjects"
              className={`px-3 py-1.5 rounded-lg transition ${
                location.pathname.startsWith('/subjects')
                  ? 'bg-slate-800 text-brand-400'
                  : 'text-slate-400 hover:text-white hover:bg-slate-900'
              }`}
            >
              Subjects
            </Link>
          </nav>
        )}
      </div>

      {user ? (
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2.5 px-3 py-1.5 rounded-xl bg-slate-900 border border-slate-800 text-xs">
            <div className="w-6 h-6 rounded-full bg-brand-500/20 text-brand-400 flex items-center justify-center font-bold">
              {user.full_name?.charAt(0) || 'F'}
            </div>
            <div className="hidden sm:block text-left">
              <p className="text-slate-200 font-medium leading-none">{user.full_name}</p>
              <p className="text-[10px] text-slate-500 font-mono mt-0.5">{user.role}</p>
            </div>
          </div>

          <button
            onClick={handleLogout}
            title="Log out"
            className="p-2 rounded-xl text-slate-400 hover:text-red-400 hover:bg-slate-900 transition"
          >
            <LogOut className="w-4 h-4" />
          </button>
        </div>
      ) : (
        <div className="flex items-center gap-3">
          <Link to="/login" className="text-xs font-semibold text-slate-300 hover:text-white px-3 py-2">
            Sign In
          </Link>
          <Link
            to="/register"
            className="text-xs font-semibold bg-brand-500 hover:bg-brand-600 text-white px-4 py-2 rounded-xl transition shadow-lg shadow-brand-500/20"
          >
            Get Started
          </Link>
        </div>
      )}
    </header>
  );
};
