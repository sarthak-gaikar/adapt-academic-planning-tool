import React, { useState, useEffect } from 'react';
import {
  UploadCloud,
  FileText,
  CheckCircle2,
  AlertCircle,
  Sparkles,
  BookOpen,
  Layers,
  Clock,
  Edit2,
  Save,
  Plus,
  Trash2,
} from 'lucide-react';
import api from '../../services/api';
import { TaskProgressModal } from '../common/TaskProgressModal';

export const SyllabusTab = ({ subject, onSyllabusUpdated }) => {
  const [syllabus, setSyllabus] = useState(null);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [taskId, setTaskId] = useState(null);
  const [isEditing, setIsEditing] = useState(false);
  const [editUnits, setEditUnits] = useState([]);

  const fetchSyllabus = async () => {
    try {
      const res = await api.get(`/subjects/${subject.id}/syllabus`);
      setSyllabus(res.data);
      setEditUnits(res.data.units || []);
    } catch (e) {
      setSyllabus(null);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchSyllabus();
  }, [subject.id]);

  const handleFileUpload = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;

    const formData = new FormData();
    formData.append('file', file);
    formData.append('document_type', 'SYLLABUS');

    setUploading(true);
    try {
      const res = await api.post(`/subjects/${subject.id}/documents`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
      if (res.data.task_id) {
        setTaskId(res.data.task_id);
      }
    } catch (err) {
      alert(err.response?.data?.detail || 'Upload failed');
    } finally {
      setUploading(false);
    }
  };

  const handleConfirmSyllabus = async () => {
    try {
      await api.post(`/subjects/${subject.id}/syllabus/confirm`);
      fetchSyllabus();
      if (onSyllabusUpdated) onSyllabusUpdated();
    } catch (err) {
      alert('Failed to confirm syllabus');
    }
  };

  const handleSaveEdit = async () => {
    try {
      const payload = {
        structured_data: {
          subject_name: subject.name,
          course_code: subject.course_code,
          credits: subject.credits,
          teaching_hours: subject.teaching_hours,
          units: editUnits.map((u) => ({
            unit_number: u.unit_number,
            title: u.title,
            hours: u.hours,
            topics: (u.topics || []).map((t) => ({
              name: t.name,
              subtopics: t.subtopics || [],
            })),
          })),
        },
      };
      await api.put(`/subjects/${subject.id}/syllabus`, payload);
      setIsEditing(false);
      fetchSyllabus();
      if (onSyllabusUpdated) onSyllabusUpdated();
    } catch (err) {
      alert('Failed to save edits');
    }
  };

  return (
    <div className="space-y-6">
      {/* Upload Banner */}
      <div className="bg-slate-900 border border-slate-800 rounded-3xl p-6 relative overflow-hidden shadow-xl">
        <div className="flex flex-col md:flex-row items-center justify-between gap-6">
          <div>
            <span className="text-xs font-mono font-semibold px-2.5 py-1 rounded-md bg-brand-500/10 text-brand-400 border border-brand-500/20 uppercase tracking-wider">
              Document Ingestion & RAG
            </span>
            <h2 className="text-xl font-bold text-white mt-2">Upload Subject Syllabus (PDF / DOCX)</h2>
            <p className="text-xs text-slate-400 mt-1 max-w-xl">
              Upload your complete course syllabus. ADAPT will parse the document, extract semantic chunks, generate pgvector embeddings, and construct structured units and topics.
            </p>
          </div>

          <div className="shrink-0">
            <label className="cursor-pointer inline-flex items-center gap-2.5 px-5 py-3 rounded-2xl bg-brand-500 hover:bg-brand-600 active:scale-95 text-white font-semibold text-xs transition shadow-lg shadow-brand-500/20">
              <UploadCloud className="w-4 h-4" />
              <span>{uploading ? 'Uploading...' : 'Upload PDF / DOCX'}</span>
              <input
                type="file"
                accept=".pdf,.docx,.doc"
                onChange={handleFileUpload}
                disabled={uploading}
                className="hidden"
              />
            </label>
          </div>
        </div>
      </div>

      {/* Structured Syllabus Content */}
      {loading ? (
        <div className="text-center py-12 text-slate-500">Loading syllabus...</div>
      ) : !syllabus ? (
        <div className="bg-slate-900 border border-dashed border-slate-800 rounded-3xl p-12 text-center">
          <BookOpen className="w-12 h-12 text-slate-600 mx-auto mb-3" />
          <h3 className="text-base font-semibold text-white">No Syllabus Uploaded</h3>
          <p className="text-xs text-slate-400 max-w-sm mx-auto mt-1">
            Please upload the PDF/DOCX syllabus document above to analyze the course modules.
          </p>
        </div>
      ) : (
        <div className="bg-slate-900 border border-slate-800 rounded-3xl p-6 shadow-xl">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-6 mb-6 border-b border-slate-800 gap-4">
            <div>
              <div className="flex items-center gap-3">
                <h3 className="text-lg font-bold text-white">Structured Course Representation</h3>
                <span
                  className={`text-xs px-2.5 py-0.5 rounded-full font-mono font-medium border ${
                    syllabus.status === 'CONFIRMED'
                      ? 'bg-brand-500/10 text-brand-400 border-brand-500/30'
                      : 'bg-amber-500/10 text-amber-400 border-amber-500/30'
                  }`}
                >
                  {syllabus.status}
                </span>
              </div>
              <p className="text-xs text-slate-400 mt-1">
                Version {syllabus.version} • {syllabus.units?.length || 0} Modules extracted via LLM
              </p>
            </div>

            <div className="flex items-center gap-2">
              {isEditing ? (
                <>
                  <button
                    onClick={() => setIsEditing(false)}
                    className="px-3.5 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-medium rounded-xl transition"
                  >
                    Cancel
                  </button>
                  <button
                    onClick={handleSaveEdit}
                    className="inline-flex items-center gap-1.5 px-4 py-2 bg-brand-500 hover:bg-brand-600 text-white text-xs font-semibold rounded-xl transition"
                  >
                    <Save className="w-3.5 h-3.5" /> Save Changes
                  </button>
                </>
              ) : (
                <>
                  <button
                    onClick={() => setIsEditing(true)}
                    className="inline-flex items-center gap-1.5 px-3.5 py-2 bg-slate-800 hover:bg-slate-750 text-slate-200 text-xs font-medium rounded-xl transition border border-slate-700"
                  >
                    <Edit2 className="w-3.5 h-3.5" /> Edit Units
                  </button>
                  {syllabus.status !== 'CONFIRMED' && (
                    <button
                      onClick={handleConfirmSyllabus}
                      className="inline-flex items-center gap-1.5 px-4 py-2 bg-brand-500 hover:bg-brand-600 text-white text-xs font-semibold rounded-xl transition shadow-lg shadow-brand-500/20"
                    >
                      <CheckCircle2 className="w-3.5 h-3.5" /> Confirm Syllabus
                    </button>
                  )}
                </>
              )}
            </div>
          </div>

          {/* Units Breakdown */}
          <div className="space-y-4">
            {editUnits.map((u, uIdx) => (
              <div key={u.id || uIdx} className="bg-slate-950/80 border border-slate-800/80 rounded-2xl p-5">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 mb-3">
                  <div className="flex items-center gap-3">
                    <span className="w-7 h-7 rounded-xl bg-brand-500/20 text-brand-400 flex items-center justify-center font-bold text-xs font-mono">
                      U{u.unit_number}
                    </span>
                    {isEditing ? (
                      <input
                        type="text"
                        value={u.title}
                        onChange={(e) => {
                          const updated = [...editUnits];
                          updated[uIdx].title = e.target.value;
                          setEditUnits(updated);
                        }}
                        className="bg-slate-900 border border-slate-700 rounded-lg px-2.5 py-1 text-sm text-white focus:outline-none focus:border-brand-500 font-semibold"
                      />
                    ) : (
                      <h4 className="font-semibold text-white text-sm">{u.title}</h4>
                    )}
                  </div>

                  <div className="flex items-center gap-2 text-xs text-slate-400 font-mono">
                    <Clock className="w-3.5 h-3.5" />
                    {isEditing ? (
                      <input
                        type="number"
                        value={u.hours || 0}
                        onChange={(e) => {
                          const updated = [...editUnits];
                          updated[uIdx].hours = parseInt(e.target.value) || 0;
                          setEditUnits(updated);
                        }}
                        className="w-16 bg-slate-900 border border-slate-700 rounded-lg px-2 py-0.5 text-xs text-white"
                      />
                    ) : (
                      <span>{u.hours || 8} Hours</span>
                    )}
                  </div>
                </div>

                {/* Topics / Subtopics */}
                <div className="pl-10 space-y-2.5">
                  {(u.topics || []).map((t, tIdx) => (
                    <div key={t.id || tIdx} className="bg-slate-900/60 rounded-xl p-3 border border-slate-800/60">
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-medium text-slate-200">{t.name}</span>
                      </div>
                      {t.subtopics && t.subtopics.length > 0 && (
                        <div className="flex flex-wrap gap-1.5 mt-2">
                          {t.subtopics.map((st, stIdx) => (
                            <span
                              key={stIdx}
                              className="text-[11px] px-2 py-0.5 rounded-md bg-slate-800 text-slate-400 border border-slate-750 font-mono"
                            >
                              {st}
                            </span>
                          ))}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Task polling modal */}
      <TaskProgressModal
        taskId={taskId}
        title="Ingesting & Indexing Syllabus"
        onComplete={() => {
          setTaskId(null);
          fetchSyllabus();
          if (onSyllabusUpdated) onSyllabusUpdated();
        }}
        onClose={() => setTaskId(null)}
      />
    </div>
  );
};
