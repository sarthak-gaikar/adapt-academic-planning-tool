import React, { useState, useEffect } from 'react';
import { Sparkles, Check, GitBranch } from 'lucide-react';
import api from '../../services/api';

const STRENGTH_LABELS = ['—', 'Low', 'Medium', 'High'];
const STRENGTH_COLORS = [
  'bg-slate-800 text-slate-500',
  'bg-amber-500/10 text-amber-400 border border-amber-500/20',
  'bg-blue-500/10 text-blue-400 border border-blue-500/20',
  'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20',
];

export const COLOMappingTab = ({ subject }) => {
  const [matrix, setMatrix] = useState(null);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);

  const fetchMatrix = async () => {
    try {
      const res = await api.get(`/subjects/${subject.id}/co-lo-mappings`);
      setMatrix(res.data);
    } catch (e) { console.error(e); }
    finally { setLoading(false); }
  };

  useEffect(() => { fetchMatrix(); }, [subject.id]);

  const handleGenerate = async () => {
    setGenerating(true);
    try {
      await api.post(`/subjects/${subject.id}/co-lo-mappings/generate`);
      setTimeout(fetchMatrix, 3000);
    } catch (e) { console.error(e); }
    finally { setGenerating(false); }
  };

  const handleCellClick = async (loCode, coCode, cell) => {
    if (!cell?.id) return;
    const newStrength = ((cell.strength || 0) + 1) % 4;
    try {
      await api.put(`/co-lo-mappings/${cell.id}`, { mapping_strength: newStrength });
      fetchMatrix();
    } catch (e) { console.error(e); }
  };

  if (loading) return <div className="text-center py-12 text-slate-500">Loading CO-LO mapping...</div>;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-bold text-white flex items-center gap-2">
            <GitBranch className="w-5 h-5 text-brand-400" /> CO-LO Mapping Matrix
          </h2>
          <p className="text-xs text-slate-400 mt-1">Click cells to cycle mapping strength (0→1→2→3→0)</p>
        </div>
        <button onClick={handleGenerate} disabled={generating}
          className="px-4 py-2 bg-brand-500 hover:bg-brand-600 text-white text-xs font-semibold rounded-xl flex items-center gap-2 disabled:opacity-50 transition">
          <Sparkles className="w-4 h-4" /> {generating ? 'Generating...' : 'AI Suggest'}
        </button>
      </div>

      {matrix && matrix.co_list?.length > 0 && matrix.lo_list?.length > 0 ? (
        <div className="overflow-x-auto">
          <table className="w-full text-xs border-collapse">
            <thead>
              <tr>
                <th className="sticky left-0 z-10 bg-slate-900 px-3 py-2 text-left text-slate-400 font-semibold border-b border-slate-700">LO \\ CO</th>
                {matrix.co_list.map(co => (
                  <th key={co} className="px-3 py-2 text-center text-slate-400 font-mono font-bold border-b border-slate-700 min-w-[60px]">{co}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {matrix.lo_list.map(lo => (
                <tr key={lo} className="hover:bg-slate-800/30 transition">
                  <td className="sticky left-0 z-10 bg-slate-900 px-3 py-2 font-mono font-bold text-brand-400 border-b border-slate-800">{lo}</td>
                  {matrix.co_list.map(co => {
                    const cell = matrix.matrix?.[lo]?.[co];
                    const strength = cell?.strength || 0;
                    return (
                      <td key={co} className="px-1 py-1 text-center border-b border-slate-800">
                        <button onClick={() => handleCellClick(lo, co, cell)}
                          className={`w-full px-2 py-1.5 rounded-lg text-[10px] font-bold cursor-pointer transition ${STRENGTH_COLORS[strength]}`}>
                          {strength > 0 ? strength : '—'}
                        </button>
                      </td>
                    );
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <div className="text-center py-16 text-slate-500">
          <GitBranch className="w-10 h-10 mx-auto mb-3 opacity-30" />
          <p className="font-semibold">No CO-LO mapping data</p>
          <p className="text-xs mt-1">Generate COs and LOs first, then create mappings.</p>
        </div>
      )}

      {/* Legend */}
      <div className="flex items-center gap-4 text-[10px] text-slate-500">
        <span className="font-semibold">Legend:</span>
        {STRENGTH_LABELS.map((label, i) => (
          <span key={i} className={`px-2 py-0.5 rounded ${STRENGTH_COLORS[i]}`}>{i}: {label}</span>
        ))}
      </div>
    </div>
  );
};
