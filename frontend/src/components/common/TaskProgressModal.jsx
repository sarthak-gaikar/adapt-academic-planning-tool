import React, { useEffect, useState } from 'react';
import { Loader2, CheckCircle2, XCircle, Sparkles } from 'lucide-react';
import api from '../../services/api';

export const TaskProgressModal = ({ taskId, title, onComplete, onClose }) => {
  const [task, setTask] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!taskId) return;

    const interval = setInterval(async () => {
      try {
        const res = await api.get(`/tasks/${taskId}`);
        setTask(res.data);

        if (res.data.status === 'COMPLETED') {
          clearInterval(interval);
          if (onComplete) onComplete(res.data.result);
        } else if (res.data.status === 'FAILED') {
          clearInterval(interval);
          setError(res.data.error || 'Operation failed');
        }
      } catch (err) {
        clearInterval(interval);
        setError('Could not fetch task status');
      }
    }, 1500);

    return () => clearInterval(interval);
  }, [taskId]);

  if (!taskId) return null;

  const isCompleted = task?.status === 'COMPLETED';
  const isFailed = task?.status === 'FAILED' || error;
  const progress = task?.progress || 10;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4 animate-in fade-in duration-200">
      <div className="bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-md p-6 shadow-2xl relative overflow-hidden">
        {/* Ambient glow */}
        <div className="absolute -top-24 -right-24 w-48 h-48 bg-brand-500/10 rounded-full blur-3xl pointer-events-none" />

        <div className="flex items-center gap-3 mb-4">
          <div className={`p-2.5 rounded-xl ${isCompleted ? 'bg-brand-500/20 text-brand-400' : isFailed ? 'bg-red-500/20 text-red-400' : 'bg-brand-500/10 text-brand-400 animate-pulse'}`}>
            {isCompleted ? <CheckCircle2 className="w-6 h-6" /> : isFailed ? <XCircle className="w-6 h-6" /> : <Sparkles className="w-6 h-6" />}
          </div>
          <div>
            <h3 className="font-semibold text-white text-base">{title || 'AI Agent Operation'}</h3>
            <p className="text-xs text-slate-400">{task?.operation || 'Processing with RAG & LLM...'}</p>
          </div>
        </div>

        {/* Progress Bar */}
        <div className="my-5">
          <div className="flex justify-between text-xs text-slate-400 mb-1.5 font-mono">
            <span>{task?.message || 'Executing pipeline...'}</span>
            <span>{Math.round(progress)}%</span>
          </div>
          <div className="w-full bg-slate-800 rounded-full h-2.5 overflow-hidden p-0.5 border border-slate-700/50">
            <div
              className={`h-full rounded-full transition-all duration-500 ${
                isCompleted ? 'bg-brand-500' : isFailed ? 'bg-red-500' : 'bg-gradient-to-r from-brand-600 via-brand-400 to-emerald-300'
              }`}
              style={{ width: `${progress}%` }}
            />
          </div>
        </div>

        {/* Status Messages */}
        {isFailed && (
          <div className="bg-red-500/10 border border-red-500/20 rounded-xl p-3 mb-4 text-xs text-red-300">
            <strong>Error:</strong> {error}
          </div>
        )}

        {isCompleted && (
          <div className="bg-brand-500/10 border border-brand-500/20 rounded-xl p-3 mb-4 text-xs text-brand-300 flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4 shrink-0" />
            <span>Operation completed and validated successfully!</span>
          </div>
        )}

        {/* Actions */}
        <div className="flex justify-end gap-2 mt-4">
          {(isCompleted || isFailed) && (
            <button
              onClick={onClose}
              className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 text-sm font-medium rounded-xl transition"
            >
              Close
            </button>
          )}
        </div>
      </div>
    </div>
  );
};
