import React, { useState, useEffect } from 'react';
import { Sparkles, CheckCircle2, Edit2, Save, Layers, Plus, CheckCheck, RefreshCw } from 'lucide-react';
import api from '../../services/api';
import { TaskProgressModal } from '../common/TaskProgressModal';

export const CourseOutcomesTab = ({ subject }) => {
  const [cos, setCos] = useState([]);
  const [loading, setLoading] = useState(true);
  const [taskId, setTaskId] = useState(null);
  const [editingId, setEditingId] = useState(null);
  const [editForm, setEditForm] = useState({ statement: '', bloom_level: 'Apply' });

  const fetchCOs = async () => {
    try {
      const res = await api.get(`/subjects/${subject.id}/course-outcomes`);
      setCos(res.data);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchCOs();
  }, [subject.id]);

  const handleGenerate = async () => {
    try {
      const res = await api.post(`/subjects/${subject.id}/course-outcomes/generate`, { num_cos: 5 });
      setTaskId(res.data.task_id);
    } catch (err) {
      alert(err.response?.data?.detail || 'Failed to start generation');
    }
  };

  const handleApprove = async (coId) => {
    try {
      await api.post(`/course-outcomes/${coId}/approve`);
      fetchCOs();
    } catch (err) {
      alert('Approval failed');
    }
  };

  const handleApproveAll = async () => {
    try {
      await api.post(`/subjects/${subject.id}/course-outcomes/approve-all`);
      fetchCOs();
    } catch (err) {
      alert('Approval failed');
    }
  };

  const handleSaveEdit = async (coId) => {
    try {
      await api.put(`/course-outcomes/${coId}`, editForm);
      setEditingId(null);
      fetchCOs();
    } catch (err) {
      alert('Failed to save CO');
    }
  };

  const getBloomBadgeColor = (level) => {
    switch (level?.toLowerCase()) {
      case 'remember': return 'bg-blue-500/10 text-blue-400 border-blue-500/20';
      case 'understand': return 'bg-cyan-500/10 text-cyan-400 border-cyan-500/20';
      case 'apply': return 'bg-brand-500/10 text-brand-400 border-brand-500/20';
      case 'analyze': return 'bg-purple-500/10 text-purple-400 border-purple-500/20';
      case 'evaluate': return 'bg-amber-500/10 text-amber-400 border-amber-500/20';
      case 'create': return 'bg-rose-500/10 text-rose-400 border-rose-500/20';
      default: return 'bg-slate-800 text-slate-300 border-slate-700';
    }
  };

  return (
    <div className="space-y-6">
      {/* Header action bar */}
      <div className="bg-slate-900 border border-slate-800 rounded-3xl p-6 flex flex-col sm:flex-row items-center justify-between gap-4 shadow-xl">
        <div>
          <span className="text-xs font-mono font-semibold px-2.5 py-1 rounded-md bg-brand-500/10 text-brand-400 border border-brand-500/20 uppercase tracking-wider">
            Outcome-Based Education
          </span>
          <h2 className="text-xl font-bold text-white mt-2">Course Outcomes (COs)</h2>
          <p className="text-xs text-slate-400 mt-1 max-w-xl">
            Measurable, action-verb driven competencies with progressive Bloom taxonomy cognitive levels.
          </p>
        </div>

        <div className="flex items-center gap-2">
          {cos.length > 0 && cos.some((c) => c.status === 'DRAFT') && (
            <button
              onClick={handleApproveAll}
              className="inline-flex items-center gap-1.5 px-4 py-2.5 rounded-xl bg-slate-800 hover:bg-slate-750 text-brand-400 border border-slate-700 text-xs font-semibold transition"
            >
              <CheckCheck className="w-4 h-4" /> Approve All
            </button>
          )}

          <button
            onClick={handleGenerate}
            className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-brand-500 hover:bg-brand-600 active:scale-95 text-white font-semibold text-xs transition shadow-lg shadow-brand-500/20"
          >
            <Sparkles className="w-4 h-4" />
            <span>{cos.length === 0 ? 'Generate COs' : 'Regenerate COs'}</span>
          </button>
        </div>
      </div>

      {/* CO List */}
      {loading ? (
        <div className="text-center py-12 text-slate-500">Loading outcomes...</div>
      ) : cos.length === 0 ? (
        <div className="bg-slate-900 border border-dashed border-slate-800 rounded-3xl p-12 text-center">
          <Layers className="w-12 h-12 text-slate-600 mx-auto mb-3" />
          <h3 className="text-base font-semibold text-white">No Course Outcomes Generated</h3>
          <p className="text-xs text-slate-400 max-w-sm mx-auto mt-1 mb-5">
            Generate 4-6 measurable Course Outcomes mapped to syllabus units and Bloom levels.
          </p>
          <button
            onClick={handleGenerate}
            className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-brand-500 hover:bg-brand-600 text-white text-xs font-semibold"
          >
            <Sparkles className="w-3.5 h-3.5" /> Generate Now
          </button>
        </div>
      ) : (
        <div className="space-y-4">
          {cos.map((co) => (
            <div
              key={co.id}
              className="bg-slate-900 border border-slate-800 rounded-2xl p-5 shadow-lg relative overflow-hidden group hover:border-slate-700 transition"
            >
              <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-4">
                <div className="flex items-start gap-3.5 flex-1">
                  <span className="w-10 h-10 rounded-xl bg-brand-500/10 border border-brand-500/20 text-brand-400 font-mono font-extrabold text-sm flex items-center justify-center shrink-0">
                    {co.co_code}
                  </span>

                  <div className="flex-1">
                    {editingId === co.id ? (
                      <div className="space-y-3">
                        <textarea
                          value={editForm.statement}
                          onChange={(e) => setEditForm({ ...editForm, statement: e.target.value })}
                          rows={2}
                          className="w-full bg-slate-950 border border-slate-700 rounded-xl p-2.5 text-sm text-white focus:outline-none focus:border-brand-500"
                        />
                        <div className="flex items-center gap-3">
                          <label className="text-xs text-slate-400">Bloom Level:</label>
                          <select
                            value={editForm.bloom_level}
                            onChange={(e) => setEditForm({ ...editForm, bloom_level: e.target.value })}
                            className="bg-slate-950 border border-slate-700 rounded-lg px-2.5 py-1 text-xs text-white"
                          >
                            {['Remember', 'Understand', 'Apply', 'Analyze', 'Evaluate', 'Create'].map((lvl) => (
                              <option key={lvl} value={lvl}>{lvl}</option>
                            ))}
                          </select>
                        </div>
                      </div>
                    ) : (
                      <>
                        <p className="text-sm font-medium text-white leading-relaxed">{co.statement}</p>
                        {co.rationale && (
                          <p className="text-xs text-slate-400 mt-2 italic bg-slate-950/50 rounded-lg p-2 border border-slate-800/60">
                            Rationale: {co.rationale}
                          </p>
                        )}
                      </>
                    )}

                    <div className="flex flex-wrap items-center gap-2 mt-3 text-xs">
                      <span className={`px-2.5 py-0.5 rounded-full font-mono text-[11px] font-semibold border ${getBloomBadgeColor(co.bloom_level)}`}>
                        {co.bloom_level} ({co.bloom_confidence ? `${Math.round(co.bloom_confidence * 100)}%` : 'Verified'})
                      </span>

                      {co.supporting_units && co.supporting_units.length > 0 && (
                        <span className="px-2.5 py-0.5 rounded-full bg-slate-800 text-slate-300 font-mono text-[11px] border border-slate-700">
                          Units {co.supporting_units.join(', ')}
                        </span>
                      )}

                      <span className={`text-[10px] px-2 py-0.5 rounded font-mono font-medium ${co.status === 'APPROVED' ? 'text-brand-400 bg-brand-500/10' : 'text-amber-400 bg-amber-500/10'}`}>
                        {co.status}
                      </span>
                    </div>
                  </div>
                </div>

                {/* Card Actions */}
                <div className="flex items-center gap-2 shrink-0">
                  {editingId === co.id ? (
                    <button
                      onClick={() => handleSaveEdit(co.id)}
                      className="p-2 rounded-xl bg-brand-500 hover:bg-brand-600 text-white transition"
                    >
                      <Save className="w-4 h-4" />
                    </button>
                  ) : (
                    <button
                      onClick={() => {
                        setEditingId(co.id);
                        setEditForm({ statement: co.statement, bloom_level: co.bloom_level });
                      }}
                      className="p-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 transition"
                      title="Edit Course Outcome"
                    >
                      <Edit2 className="w-4 h-4" />
                    </button>
                  )}

                  {co.status !== 'APPROVED' && (
                    <button
                      onClick={() => handleApprove(co.id)}
                      className="inline-flex items-center gap-1 px-3 py-1.5 rounded-xl bg-brand-500/10 hover:bg-brand-500 text-brand-400 hover:text-white border border-brand-500/20 text-xs font-semibold transition"
                    >
                      <CheckCircle2 className="w-3.5 h-3.5" /> Approve
                    </button>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      <TaskProgressModal
        taskId={taskId}
        title="Generating Course Outcomes"
        onComplete={() => {
          setTaskId(null);
          fetchCOs();
        }}
        onClose={() => setTaskId(null)}
      />
    </div>
  );
};
