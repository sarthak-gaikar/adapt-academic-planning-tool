import React, { useState, useEffect } from 'react';
import { Download, FileText, CheckCircle2, FileCheck2, Calendar, KeyRound, Sparkles } from 'lucide-react';
import api from '../../services/api';

export const ExportTab = ({ subject }) => {
  const [exams, setExams] = useState([]);
  const [aap, setAap] = useState(null);
  const [loading, setLoading] = useState(true);
  const [exporting, setExporting] = useState(false);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [exRes, aapRes] = await Promise.all([
          api.get(`/subjects/${subject.id}/exams`),
          api.get(`/subjects/${subject.id}/aap`).catch(() => ({ data: null })),
        ]);
        setExams(exRes.data || []);
        setAap(aapRes.data);
      } catch (e) {
        console.error(e);
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, [subject.id]);

  const handleExport = async (sourceId, sourceType) => {
    setExporting(true);
    try {
      const res = await api.post('/export', {
        source_id: sourceId,
        source_type: sourceType,
        format: 'DOCX',
        include_co_bloom_tags: true,
      });

      // Trigger browser download
      window.open(res.data.download_url, '_blank');
    } catch (err) {
      alert('Export failed');
    } finally {
      setExporting(false);
    }
  };

  return (
    <div className="space-y-6 max-w-4xl mx-auto">
      <div className="bg-slate-900 border border-slate-800 rounded-3xl p-6 shadow-xl">
        <span className="text-xs font-mono font-semibold px-2.5 py-1 rounded-md bg-brand-500/10 text-brand-400 border border-brand-500/20 uppercase tracking-wider">
          University Document Publishing
        </span>
        <h2 className="text-xl font-bold text-white mt-2">Export Faculty-Ready Documents</h2>
        <p className="text-xs text-slate-400 mt-1">
          Generate print-ready Word (.docx) documents formatted with official university headers, OBE metadata tags, and clean tables.
        </p>
      </div>

      <div className="space-y-4">
        {/* AAP Export Card */}
        {aap && (
          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 flex items-center justify-between shadow-lg">
            <div className="flex items-center gap-4">
              <div className="p-3 rounded-xl bg-purple-500/10 text-purple-400">
                <Calendar className="w-6 h-6" />
              </div>
              <div>
                <h4 className="font-bold text-white text-sm">Academic Activity Plan (AAP) / Lesson Plan</h4>
                <p className="text-xs text-slate-400 mt-0.5">15-Week landscape tabular curriculum schedule</p>
              </div>
            </div>

            <button
              onClick={() => handleExport(aap.id, 'AAP')}
              disabled={exporting}
              className="inline-flex items-center gap-2 px-4 py-2 bg-slate-800 hover:bg-slate-750 text-white font-semibold text-xs rounded-xl border border-slate-700 transition"
            >
              <Download className="w-4 h-4 text-brand-400" /> Export DOCX
            </button>
          </div>
        )}

        {/* Exams Export Cards */}
        {exams.map((ex) => (
          <div key={ex.id} className="bg-slate-900 border border-slate-800 rounded-2xl p-5 flex items-center justify-between shadow-lg">
            <div className="flex items-center gap-4">
              <div className="p-3 rounded-xl bg-brand-500/10 text-brand-400">
                <FileText className="w-6 h-6" />
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <span className="px-2 py-0.5 rounded bg-brand-500/10 text-brand-400 font-mono text-[11px] font-bold">
                    {ex.exam_type}
                  </span>
                  <h4 className="font-bold text-white text-sm">{ex.title}</h4>
                </div>
                <p className="text-xs text-slate-400 mt-0.5">
                  Total Marks: {ex.total_marks}M • {ex.questions?.length || 0} Questions with CO & Bloom tags
                </p>
              </div>
            </div>

            <button
              onClick={() => handleExport(ex.id, 'EXAM')}
              disabled={exporting}
              className="inline-flex items-center gap-2 px-4 py-2 bg-slate-800 hover:bg-slate-750 text-white font-semibold text-xs rounded-xl border border-slate-700 transition"
            >
              <Download className="w-4 h-4 text-brand-400" /> Export DOCX
            </button>
          </div>
        ))}
      </div>
    </div>
  );
};
