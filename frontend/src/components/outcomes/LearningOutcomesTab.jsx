import React, { useState, useEffect } from 'react';
import { Sparkles, Check, Edit3, ChevronDown, ChevronRight, BookOpen } from 'lucide-react';
import api from '../../services/api';

const BLOOM_COLORS = {
  Remember: 'bg-slate-500/20 text-slate-300 border-slate-500/30',
  Understand: 'bg-blue-500/20 text-blue-300 border-blue-500/30',
  Apply: 'bg-green-500/20 text-green-300 border-green-500/30',
  Analyze: 'bg-amber-500/20 text-amber-300 border-amber-500/30',
  Evaluate: 'bg-purple-500/20 text-purple-300 border-purple-500/30',
  Create: 'bg-rose-500/20 text-rose-300 border-rose-500/30',
};

export const LearningOutcomesTab = ({ subject }) => {
  const [units, setUnits] = useState([]);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [expandedUnits, setExpandedUnits] = useState({});

  const fetchLOs = async () => {
    try {
      const res = await api.get(`/subjects/${subject.id}/learning-outcomes/by-unit`);
      setUnits(res.data);
      const expanded = {};
      res.data.forEach((u) => (expanded[u.unit_number] = true));
      setExpandedUnits(expanded);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchLOs(); }, [subject.id]);

  const handleGenerate = async () => {
    setGenerating(true);
    try {
      await api.post(`/subjects/${subject.id}/learning-outcomes/generate`, {});
      setTimeout(fetchLOs, 3000);
    } catch (e) { console.error(e); }
    finally { setGenerating(false); }
  };

  const handleApproveAll = async () => {
    try {
      await api.post(`/subjects/${subject.id}/learning-outcomes/approve-all`);
      fetchLOs();
    } catch (e) { console.error(e); }
  };

  const handleApproveLO = async (loId) => {
    try {
      await api.post(`/learning-outcomes/${loId}/approve`);
      fetchLOs();
    } catch (e) { console.error(e); }
  };

  const toggleUnit = (unitNum) => {
    setExpandedUnits(prev => ({ ...prev, [unitNum]: !prev[unitNum] }));
  };

  if (loading) return <div className="text-center py-12 text-slate-500">Loading Learning Outcomes...</div>;

  const totalLOs = units.reduce((sum, u) => sum + u.learning_outcomes.length, 0);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-bold text-white flex items-center gap-2">
            <BookOpen className="w-5 h-5 text-brand-400" /> Learning Outcomes
          </h2>
          <p className="text-xs text-slate-400 mt-1">
            {totalLOs} LOs across {units.length} units • Bloom-ordered within each unit
          </p>
        </div>
        <div className="flex gap-2">
          <button onClick={handleGenerate} disabled={generating}
            className="px-4 py-2 bg-brand-500 hover:bg-brand-600 text-white text-xs font-semibold rounded-xl flex items-center gap-2 disabled:opacity-50 transition">
            <Sparkles className="w-4 h-4" /> {generating ? 'Generating...' : 'Generate LOs'}
          </button>
          {totalLOs > 0 && (
            <button onClick={handleApproveAll}
              className="px-4 py-2 bg-emerald-500/10 hover:bg-emerald-500/20 text-emerald-400 text-xs font-semibold rounded-xl border border-emerald-500/20 flex items-center gap-2 transition">
              <Check className="w-4 h-4" /> Approve All
            </button>
          )}
        </div>
      </div>

      {/* Units with LOs */}
      {units.map((unit) => (
        <div key={unit.unit_number} className="bg-slate-900/60 border border-slate-800 rounded-2xl overflow-hidden">
          <button onClick={() => toggleUnit(unit.unit_number)}
            className="w-full flex items-center justify-between px-5 py-4 hover:bg-slate-800/50 transition">
            <div className="flex items-center gap-3">
              {expandedUnits[unit.unit_number] ? <ChevronDown className="w-4 h-4 text-slate-400" /> : <ChevronRight className="w-4 h-4 text-slate-400" />}
              <span className="font-mono text-xs text-brand-400 font-bold">Unit {unit.unit_number}</span>
              <span className="text-sm font-semibold text-white">{unit.unit_title}</span>
            </div>
            <span className="text-xs text-slate-500">{unit.learning_outcomes.length} LOs</span>
          </button>

          {expandedUnits[unit.unit_number] && (
            <div className="border-t border-slate-800 divide-y divide-slate-800/50">
              {unit.learning_outcomes.length === 0 ? (
                <div className="px-5 py-6 text-center text-sm text-slate-500">No LOs generated for this unit yet.</div>
              ) : (
                unit.learning_outcomes.map((lo) => (
                  <div key={lo.id} className="px-5 py-3.5 flex items-start gap-4 group hover:bg-slate-800/30 transition">
                    <div className="flex-shrink-0">
                      <span className="font-mono text-xs font-bold text-brand-400 bg-brand-500/10 px-2 py-1 rounded-lg border border-brand-500/20">
                        {lo.lo_code}
                      </span>
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm text-slate-200">{lo.statement}</p>
                      <div className="flex items-center gap-2 mt-1.5">
                        <span className={`text-[10px] font-semibold px-2 py-0.5 rounded-lg border ${BLOOM_COLORS[lo.bloom_level] || BLOOM_COLORS.Understand}`}>
                          {lo.bloom_level} (L{lo.bloom_order})
                        </span>
                        {lo.mapped_cos?.map(co => (
                          <span key={co} className="text-[10px] font-mono text-slate-400 bg-slate-800 px-1.5 py-0.5 rounded">{co}</span>
                        ))}
                        <span className={`text-[10px] px-1.5 py-0.5 rounded ${lo.status === 'APPROVED' ? 'bg-emerald-500/10 text-emerald-400' : 'bg-amber-500/10 text-amber-400'}`}>
                          {lo.status}
                        </span>
                      </div>
                    </div>
                    {lo.status !== 'APPROVED' && (
                      <button onClick={() => handleApproveLO(lo.id)}
                        className="opacity-0 group-hover:opacity-100 p-1.5 rounded-lg bg-emerald-500/10 text-emerald-400 hover:bg-emerald-500/20 transition text-xs">
                        <Check className="w-3.5 h-3.5" />
                      </button>
                    )}
                  </div>
                ))
              )}
            </div>
          )}
        </div>
      ))}

      {units.length === 0 && (
        <div className="text-center py-16 text-slate-500">
          <BookOpen className="w-10 h-10 mx-auto mb-3 opacity-30" />
          <p className="font-semibold">No syllabus units found</p>
          <p className="text-xs mt-1">Upload a syllabus first, then generate Learning Outcomes.</p>
        </div>
      )}
    </div>
  );
};
