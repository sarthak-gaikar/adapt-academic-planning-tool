import React, { useState, useEffect } from 'react';
import { Sparkles, CheckCheck, Info, HelpCircle } from 'lucide-react';
import api from '../../services/api';
import { TaskProgressModal } from '../common/TaskProgressModal';

export const COPOMappingTab = ({ subject }) => {
  const [matrixData, setMatrixData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [taskId, setTaskId] = useState(null);
  const [selectedCell, setSelectedCell] = useState(null);

  const fetchMatrix = async () => {
    try {
      const res = await api.get(`/subjects/${subject.id}/co-po`);
      setMatrixData(res.data);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchMatrix();
  }, [subject.id]);

  const handleGenerate = async () => {
    try {
      const res = await api.post(`/subjects/${subject.id}/co-po/generate`);
      setTaskId(res.data.task_id);
    } catch (err) {
      alert(err.response?.data?.detail || 'Failed to start generation');
    }
  };

  const handleCellLevelChange = async (mappingId, newLevel) => {
    try {
      await api.put(`/co-po/${mappingId}`, { approved_level: parseInt(newLevel) });
      fetchMatrix();
    } catch (err) {
      alert('Failed to update mapping');
    }
  };

  const handleApproveAll = async () => {
    try {
      await api.post(`/subjects/${subject.id}/co-po/approve`);
      fetchMatrix();
    } catch (err) {
      alert('Failed to approve matrix');
    }
  };

  const getCellColor = (level) => {
    switch (parseInt(level)) {
      case 3: return 'bg-brand-500 text-white font-bold shadow-md shadow-brand-500/20';
      case 2: return 'bg-brand-500/40 text-brand-200 font-semibold';
      case 1: return 'bg-brand-500/20 text-brand-300 font-medium';
      default: return 'bg-slate-900 text-slate-600';
    }
  };

  return (
    <div className="space-y-6">
      {/* Action Header */}
      <div className="bg-slate-900 border border-slate-800 rounded-3xl p-6 flex flex-col sm:flex-row items-center justify-between gap-4 shadow-xl">
        <div>
          <span className="text-xs font-mono font-semibold px-2.5 py-1 rounded-md bg-brand-500/10 text-brand-400 border border-brand-500/20 uppercase tracking-wider">
            Accreditation Matrix
          </span>
          <h2 className="text-xl font-bold text-white mt-2">CO-PO Correlation Matrix</h2>
          <p className="text-xs text-slate-400 mt-1 max-w-xl">
            NBA / Washington Accord correlation: 0 (None), 1 (Low), 2 (Medium), 3 (High). Click any cell to customize.
          </p>
        </div>

        <div className="flex items-center gap-2">
          {matrixData && Object.keys(matrixData.matrix || {}).length > 0 && (
            <button
              onClick={handleApproveAll}
              className="inline-flex items-center gap-1.5 px-4 py-2.5 rounded-xl bg-slate-800 hover:bg-slate-750 text-brand-400 border border-slate-700 text-xs font-semibold transition"
            >
              <CheckCheck className="w-4 h-4" /> Approve Matrix
            </button>
          )}

          <button
            onClick={handleGenerate}
            className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-brand-500 hover:bg-brand-600 active:scale-95 text-white font-semibold text-xs transition shadow-lg shadow-brand-500/20"
          >
            <Sparkles className="w-4 h-4" />
            <span>Generate Matrix</span>
          </button>
        </div>
      </div>

      {/* Matrix Table */}
      {loading ? (
        <div className="text-center py-12 text-slate-500">Loading correlation matrix...</div>
      ) : !matrixData || Object.keys(matrixData.matrix || {}).length === 0 ? (
        <div className="bg-slate-900 border border-dashed border-slate-800 rounded-3xl p-12 text-center">
          <h3 className="text-base font-semibold text-white">No CO-PO Matrix Generated</h3>
          <p className="text-xs text-slate-400 max-w-sm mx-auto mt-1 mb-5">
            Click Generate Matrix to have AI suggest correlations between active COs and PO1-PO12.
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
          <table className="w-full text-center border-collapse">
            <thead>
              <tr>
                <th className="p-3 text-left text-xs font-mono font-bold text-slate-400 border-b border-slate-800 bg-slate-950/40 rounded-tl-xl">
                  CO / PO
                </th>
                {matrixData.po_list?.map((po) => (
                  <th
                    key={po}
                    className="p-3 text-xs font-mono font-bold text-slate-300 border-b border-slate-800 bg-slate-950/40"
                  >
                    {po}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {matrixData.co_list?.map((co) => (
                <tr key={co} className="hover:bg-slate-850/50 transition">
                  <td className="p-3 text-left font-mono font-bold text-brand-400 text-xs border-b border-slate-800/60 bg-slate-950/20">
                    {co}
                  </td>
                  {matrixData.po_list?.map((po) => {
                    const cell = matrixData.matrix[co]?.[po];
                    const level = cell ? cell.approved ?? cell.suggested : 0;
                    return (
                      <td key={po} className="p-2 border-b border-slate-800/60">
                        <select
                          value={level}
                          onChange={(e) => cell?.id && handleCellLevelChange(cell.id, e.target.value)}
                          className={`w-9 h-9 rounded-xl text-xs font-mono text-center cursor-pointer border border-slate-700/50 focus:outline-none focus:ring-1 focus:ring-brand-400 transition appearance-none ${getCellColor(
                            level
                          )}`}
                          title={cell?.rationale || `Correlation: ${level}`}
                        >
                          <option value="0" className="bg-slate-900 text-slate-400">0</option>
                          <option value="1" className="bg-slate-900 text-brand-300">1</option>
                          <option value="2" className="bg-slate-900 text-brand-400">2</option>
                          <option value="3" className="bg-slate-900 text-brand-500 font-bold">3</option>
                        </select>
                      </td>
                    );
                  })}
                </tr>
              ))}
            </tbody>
          </table>

          {/* Legend */}
          <div className="flex flex-wrap items-center justify-between gap-4 mt-6 pt-4 border-t border-slate-800 text-xs text-slate-400 font-mono">
            <div className="flex items-center gap-4">
              <span className="flex items-center gap-1.5"><span className="w-3 h-3 rounded bg-slate-900 border border-slate-700"></span> 0: None</span>
              <span className="flex items-center gap-1.5"><span className="w-3 h-3 rounded bg-brand-500/20 border border-brand-500/40"></span> 1: Low</span>
              <span className="flex items-center gap-1.5"><span className="w-3 h-3 rounded bg-brand-500/40 border border-brand-500/60"></span> 2: Medium</span>
              <span className="flex items-center gap-1.5"><span className="w-3 h-3 rounded bg-brand-500"></span> 3: High</span>
            </div>
            <span>Click any dropdown to modify institutional correlation level.</span>
          </div>
        </div>
      )}

      <TaskProgressModal
        taskId={taskId}
        title="Generating CO-PO Correlations"
        onComplete={() => {
          setTaskId(null);
          fetchMatrix();
        }}
        onClose={() => setTaskId(null)}
      />
    </div>
  );
};
