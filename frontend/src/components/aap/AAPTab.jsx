import React, { useState, useEffect } from 'react';
import { Sparkles, Calendar, CheckCircle2, AlertTriangle, CheckCheck, Clock, Layers } from 'lucide-react';
import api from '../../services/api';
import { TaskProgressModal } from '../common/TaskProgressModal';

export const AAPTab = ({ subject }) => {
  const [aap, setAap] = useState(null);
  const [loading, setLoading] = useState(true);
  const [taskId, setTaskId] = useState(null);

  const fetchAAP = async () => {
    try {
      const res = await api.get(`/subjects/${subject.id}/aap`);
      setAap(res.data);
    } catch (e) {
      setAap(null);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAAP();
  }, [subject.id]);

  const handleGenerate = async () => {
    try {
      const res = await api.post(`/subjects/${subject.id}/aap/generate`, {
        total_weeks: 15,
        hours_per_week: 3,
      });
      setTaskId(res.data.task_id);
    } catch (err) {
      alert(err.response?.data?.detail || 'Failed to start generation');
    }
  };

  const handleApprove = async () => {
    try {
      await api.post(`/subjects/${subject.id}/aap/approve`);
      fetchAAP();
    } catch (err) {
      alert('Approval failed');
    }
  };

  const weeks = aap?.plan_data?.weeks || [];
  const valReport = aap?.validation_report || {};

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="bg-slate-900 border border-slate-800 rounded-3xl p-6 flex flex-col sm:flex-row items-center justify-between gap-4 shadow-xl">
        <div>
          <span className="text-xs font-mono font-semibold px-2.5 py-1 rounded-md bg-brand-500/10 text-brand-400 border border-brand-500/20 uppercase tracking-wider">
            Curriculum Delivery Plan
          </span>
          <h2 className="text-xl font-bold text-white mt-2">Academic Activity Plan (AAP)</h2>
          <p className="text-xs text-slate-400 mt-1 max-w-xl">
            Week-by-week instructional roadmap matching teaching hours, topics, pedagogical methods, and CO mapping.
          </p>
        </div>

        <div className="flex items-center gap-2">
          {aap && aap.status !== 'APPROVED' && (
            <button
              onClick={handleApprove}
              className="inline-flex items-center gap-1.5 px-4 py-2.5 rounded-xl bg-slate-800 hover:bg-slate-750 text-brand-400 border border-slate-700 text-xs font-semibold transition"
            >
              <CheckCheck className="w-4 h-4" /> Approve Plan
            </button>
          )}

          <button
            onClick={handleGenerate}
            className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-brand-500 hover:bg-brand-600 active:scale-95 text-white font-semibold text-xs transition shadow-lg shadow-brand-500/20"
          >
            <Sparkles className="w-4 h-4" />
            <span>{aap ? 'Regenerate AAP' : 'Generate 15-Week AAP'}</span>
          </button>
        </div>
      </div>

      {/* Validation Checklist Banner */}
      {valReport?.checks && (
        <div className="bg-slate-900 border border-slate-800 rounded-3xl p-5 shadow-lg">
          <h4 className="text-xs font-mono font-bold text-slate-400 uppercase tracking-wider mb-3">
            Deterministic Constraint Validation
          </h4>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
            {valReport.checks.map((chk, idx) => (
              <div
                key={idx}
                className={`p-3 rounded-2xl border text-xs flex items-start gap-2.5 ${
                  chk.passed
                    ? 'bg-brand-500/10 border-brand-500/20 text-brand-300'
                    : 'bg-red-500/10 border-red-500/20 text-red-300'
                }`}
              >
                {chk.passed ? <CheckCircle2 className="w-4 h-4 text-brand-400 shrink-0 mt-0.5" /> : <AlertTriangle className="w-4 h-4 text-red-400 shrink-0 mt-0.5" />}
                <div>
                  <strong className="block text-white font-medium">{chk.name}</strong>
                  <span className="text-[11px] opacity-80">{chk.message}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Plan Table */}
      {loading ? (
        <div className="text-center py-12 text-slate-500">Loading activity plan...</div>
      ) : !aap || weeks.length === 0 ? (
        <div className="bg-slate-900 border border-dashed border-slate-800 rounded-3xl p-12 text-center">
          <Calendar className="w-12 h-12 text-slate-600 mx-auto mb-3" />
          <h3 className="text-base font-semibold text-white">No Academic Activity Plan</h3>
          <p className="text-xs text-slate-400 max-w-sm mx-auto mt-1 mb-5">
            Generate a constraint-checked semester lesson plan covering all syllabus units.
          </p>
          <button
            onClick={handleGenerate}
            className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-brand-500 hover:bg-brand-600 text-white text-xs font-semibold"
          >
            <Sparkles className="w-3.5 h-3.5" /> Generate Now
          </button>
        </div>
      ) : (
        <div className="bg-slate-900 border border-slate-800 rounded-3xl p-6 shadow-xl overflow-x-auto">
          <table className="w-full text-left border-collapse text-xs">
            <thead>
              <tr className="border-b border-slate-800 bg-slate-950/60 font-mono text-slate-400">
                <th className="p-3.5 font-bold rounded-tl-xl w-16">Week</th>
                <th className="p-3.5 font-bold w-20">Unit</th>
                <th className="p-3.5 font-bold">Planned Topics</th>
                <th className="p-3.5 font-bold">Pedagogical Method</th>
                <th className="p-3.5 font-bold w-20">CO</th>
                <th className="p-3.5 font-bold w-16 text-center">Hours</th>
                <th className="p-3.5 font-bold rounded-tr-xl">Activity</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60">
              {weeks.map((w, idx) => (
                <tr key={idx} className="hover:bg-slate-850/50 transition">
                  <td className="p-3.5 font-mono font-bold text-brand-400">W{w.week_number}</td>
                  <td className="p-3.5 font-mono font-semibold text-slate-300">Unit {w.unit_number}</td>
                  <td className="p-3.5 text-slate-200">
                    {Array.isArray(w.topics_covered) ? w.topics_covered.join(', ') : w.topics_covered}
                  </td>
                  <td className="p-3.5">
                    <span className="px-2.5 py-1 rounded-lg bg-slate-800 border border-slate-700 text-slate-300 font-mono text-[11px]">
                      {w.teaching_method}
                    </span>
                  </td>
                  <td className="p-3.5 font-mono font-bold text-brand-400">{w.co_mapped}</td>
                  <td className="p-3.5 font-mono text-center text-slate-300 font-semibold">{w.planned_hours}h</td>
                  <td className="p-3.5 text-slate-400 font-medium">{w.activity_type || 'Lecture'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <TaskProgressModal
        taskId={taskId}
        title="Generating Academic Activity Plan"
        onComplete={() => {
          setTaskId(null);
          fetchAAP();
        }}
        onClose={() => setTaskId(null)}
      />
    </div>
  );
};
