import React, { useState, useEffect } from 'react';
import { Sparkles, Network } from 'lucide-react';
import api from '../../services/api';

const LEVEL_LABELS = ['—', 'Low', 'Medium', 'High'];
const LEVEL_COLORS = [
  'bg-slate-800 text-slate-500',
  'bg-amber-500/10 text-amber-400 border border-amber-500/20',
  'bg-blue-500/10 text-blue-400 border border-blue-500/20',
  'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20',
];

export const LOPIMappingTab = ({ subject }) => {
  const [matrix, setMatrix] = useState(null);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);

  const fetchMatrix = async () => {
    try {
      const res = await api.get(`/subjects/${subject.id}/lo-pi-mappings`);
      setMatrix(res.data);
    } catch (e) { console.error(e); }
    finally { setLoading(false); }
  };

  useEffect(() => { fetchMatrix(); }, [subject.id]);

  const handleGenerate = async () => {
    setGenerating(true);
    try {
      await api.post(`/subjects/${subject.id}/lo-pi-mappings/generate`);
      setTimeout(fetchMatrix, 3000);
    } catch (e) { console.error(e); }
    finally { setGenerating(false); }
  };

  const handleCellClick = async (loCode, piCode, cell) => {
    if (!cell?.id) return;
    const newLevel = ((cell.level || 0) + 1) % 4;
    try {
      await api.put(`/lo-pi-mappings/${cell.id}`, { mapping_level: newLevel });
      fetchMatrix();
    } catch (e) { console.error(e); }
  };

  if (loading) return <div className="text-center py-12 text-slate-500">Loading LO-PI mapping...</div>;

  // Group PIs by PO prefix for header rendering
  const pisByPO = {};
  if (matrix?.pi_list) {
    matrix.pi_list.forEach(pi => {
      const po = pi.split('.')[0].replace('PI', 'PO');
      if (!pisByPO[po]) pisByPO[po] = [];
      pisByPO[po].push(pi);
    });
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-bold text-white flex items-center gap-2">
            <Network className="w-5 h-5 text-brand-400" /> LO-PI Mapping Matrix
          </h2>
          <p className="text-xs text-slate-400 mt-1">Maps Learning Outcomes to Performance Indicators → derives PO attainment</p>
        </div>
        <button onClick={handleGenerate} disabled={generating}
          className="px-4 py-2 bg-brand-500 hover:bg-brand-600 text-white text-xs font-semibold rounded-xl flex items-center gap-2 disabled:opacity-50 transition">
          <Sparkles className="w-4 h-4" /> {generating ? 'Generating...' : 'AI Suggest'}
        </button>
      </div>

      {matrix && matrix.lo_list?.length > 0 && matrix.pi_list?.length > 0 ? (
        <div className="overflow-x-auto max-h-[600px] overflow-y-auto">
          <table className="w-full text-xs border-collapse">
            <thead className="sticky top-0 z-20">
              {/* PO group header */}
              <tr className="bg-slate-900">
                <th className="sticky left-0 z-30 bg-slate-900 px-3 py-1 border-b border-slate-700"></th>
                {Object.entries(pisByPO).map(([po, pis]) => (
                  <th key={po} colSpan={pis.length} className="px-2 py-1.5 text-center text-[10px] font-bold text-slate-300 border-b border-slate-700 bg-slate-800/50">
                    {po}
                  </th>
                ))}
              </tr>
              {/* PI code header */}
              <tr className="bg-slate-900">
                <th className="sticky left-0 z-30 bg-slate-900 px-3 py-2 text-left text-slate-400 font-semibold border-b border-slate-700">LO \\ PI</th>
                {matrix.pi_list.map(pi => (
                  <th key={pi} className="px-1 py-2 text-center text-[10px] text-slate-400 font-mono border-b border-slate-700 min-w-[45px]"
                    style={{ writingMode: 'vertical-lr', textOrientation: 'mixed' }}>
                    {pi}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {matrix.lo_list.map(lo => (
                <tr key={lo} className="hover:bg-slate-800/30 transition">
                  <td className="sticky left-0 z-10 bg-slate-900 px-3 py-1.5 font-mono font-bold text-brand-400 text-[10px] border-b border-slate-800 whitespace-nowrap">{lo}</td>
                  {matrix.pi_list.map(pi => {
                    const cell = matrix.matrix?.[lo]?.[pi];
                    const level = cell?.level || 0;
                    return (
                      <td key={pi} className="px-0.5 py-0.5 text-center border-b border-slate-800">
                        <button onClick={() => handleCellClick(lo, pi, cell)}
                          className={`w-full px-1 py-1 rounded text-[9px] font-bold cursor-pointer transition ${LEVEL_COLORS[level]}`}>
                          {level > 0 ? level : ''}
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
          <Network className="w-10 h-10 mx-auto mb-3 opacity-30" />
          <p className="font-semibold">No LO-PI mapping data</p>
          <p className="text-xs mt-1">Generate LOs and ensure PIs are seeded, then create mappings.</p>
        </div>
      )}

      {/* Legend */}
      <div className="flex items-center gap-4 text-[10px] text-slate-500">
        <span className="font-semibold">Legend:</span>
        {LEVEL_LABELS.map((label, i) => (
          <span key={i} className={`px-2 py-0.5 rounded ${LEVEL_COLORS[i]}`}>{i}: {label}</span>
        ))}
      </div>
    </div>
  );
};
