import React, { useState, useEffect } from 'react';
import { Layers, ChevronDown, ChevronRight, ArrowRight } from 'lucide-react';
import api from '../../services/api';

const BLOOM_COLORS = {
  Remember: 'text-slate-300',
  Understand: 'text-blue-300',
  Apply: 'text-green-300',
  Analyze: 'text-amber-300',
  Evaluate: 'text-purple-300',
  Create: 'text-rose-300',
};

const LEVEL_DOT = ['bg-slate-700', 'bg-amber-500', 'bg-blue-500', 'bg-emerald-500'];

export const OBEMatrixTab = ({ subject }) => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [expandedCOs, setExpandedCOs] = useState({});

  const fetchMatrix = async () => {
    try {
      const res = await api.get(`/subjects/${subject.id}/obe-matrix`);
      setData(res.data);
      const expanded = {};
      res.data.cos?.forEach(co => (expanded[co.co_code] = true));
      setExpandedCOs(expanded);
    } catch (e) { console.error(e); }
    finally { setLoading(false); }
  };

  useEffect(() => { fetchMatrix(); }, [subject.id]);

  const toggleCO = (coCode) => {
    setExpandedCOs(prev => ({ ...prev, [coCode]: !prev[coCode] }));
  };

  if (loading) return <div className="text-center py-12 text-slate-500">Loading OBE Matrix...</div>;
  if (!data || !data.cos?.length) {
    return (
      <div className="text-center py-16 text-slate-500">
        <Layers className="w-10 h-10 mx-auto mb-3 opacity-30" />
        <p className="font-semibold">No OBE traceability data</p>
        <p className="text-xs mt-1">Generate COs → LOs → CO-LO Mapping → LO-PI Mapping to see the full chain.</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h2 className="text-lg font-bold text-white flex items-center gap-2">
          <Layers className="w-5 h-5 text-brand-400" /> OBE Traceability Matrix
        </h2>
        <p className="text-xs text-slate-400 mt-1">
          CO → LO → PI → PO chain • {data.summary.total_cos} COs • {data.summary.total_los} LOs •
          {data.summary.total_pis_mapped} PIs mapped • {data.summary.total_pos_covered} POs covered
        </p>
      </div>

      {/* PO coverage summary bar */}
      <div className="bg-slate-900/60 border border-slate-800 rounded-2xl px-5 py-3">
        <p className="text-[10px] font-semibold text-slate-400 mb-2 uppercase tracking-wider">PO Coverage</p>
        <div className="flex flex-wrap gap-1.5">
          {data.po_list?.map(po => {
            const covered = data.cos?.some(co => co.derived_pos?.some(dp => dp.po_code === po));
            return (
              <span key={po} className={`text-[10px] font-mono font-bold px-2 py-0.5 rounded-lg ${covered ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' : 'bg-slate-800 text-slate-500 border border-slate-700'}`}>
                {po}
              </span>
            );
          })}
        </div>
      </div>

      {/* CO cards with nested LO→PI→PO chains */}
      {data.cos.map(co => (
        <div key={co.co_code} className="bg-slate-900/60 border border-slate-800 rounded-2xl overflow-hidden">
          <button onClick={() => toggleCO(co.co_code)}
            className="w-full flex items-center justify-between px-5 py-4 hover:bg-slate-800/50 transition">
            <div className="flex items-center gap-3">
              {expandedCOs[co.co_code] ? <ChevronDown className="w-4 h-4 text-slate-400" /> : <ChevronRight className="w-4 h-4 text-slate-400" />}
              <span className="font-mono text-xs font-bold text-brand-400">{co.co_code}</span>
              <span className={`text-[10px] font-semibold ${BLOOM_COLORS[co.bloom_level] || 'text-slate-300'}`}>
                [{co.bloom_level}]
              </span>
              <span className="text-sm text-slate-200 truncate max-w-[500px]">{co.statement}</span>
            </div>
            <div className="flex items-center gap-2">
              {co.derived_pos?.map(dp => (
                <span key={dp.po_code} className="text-[9px] font-mono bg-emerald-500/10 text-emerald-400 px-1.5 py-0.5 rounded border border-emerald-500/20">
                  {dp.po_code}:{dp.max_level}
                </span>
              ))}
            </div>
          </button>

          {expandedCOs[co.co_code] && (
            <div className="border-t border-slate-800 px-5 py-3 space-y-2">
              {co.los?.length === 0 ? (
                <p className="text-xs text-slate-500 py-2">No LOs mapped to this CO.</p>
              ) : (
                co.los.map(lo => (
                  <div key={lo.lo_code} className="bg-slate-800/40 rounded-xl px-4 py-2.5">
                    <div className="flex items-center gap-2 mb-1.5">
                      <span className="font-mono text-[10px] font-bold text-blue-400">{lo.lo_code}</span>
                      <ArrowRight className="w-3 h-3 text-slate-600" />
                      <span className="text-xs text-slate-300 truncate">{lo.statement}</span>
                      <span className={`text-[9px] ${BLOOM_COLORS[lo.bloom_level] || 'text-slate-400'} ml-auto flex-shrink-0`}>
                        {lo.bloom_level}
                      </span>
                    </div>
                    {lo.pis?.length > 0 && (
                      <div className="flex flex-wrap gap-1.5 ml-6">
                        {lo.pis.map((pi, idx) => (
                          <span key={idx} className="text-[9px] flex items-center gap-1 bg-slate-700/50 px-1.5 py-0.5 rounded">
                            <span className={`w-1.5 h-1.5 rounded-full ${LEVEL_DOT[pi.level] || LEVEL_DOT[0]}`}></span>
                            <span className="font-mono text-slate-300">{pi.pi_code}</span>
                            <span className="text-slate-500">→</span>
                            <span className="font-mono text-emerald-400">{pi.po_code}</span>
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                ))
              )}
            </div>
          )}
        </div>
      ))}
    </div>
  );
};
