import React, { useState, useEffect, useRef } from 'react';
import {
  Sparkles,
  FileCheck2,
  CheckCircle2,
  AlertTriangle,
  KeyRound,
  FileText,
  Clock,
  Layers,
  ChevronDown,
  ChevronUp,
  X,
  Upload,
  FileUp,
  Calculator,
  BookOpen,
  Zap,
} from 'lucide-react';
import api from '../../services/api';
import { TaskProgressModal } from '../common/TaskProgressModal';

// ─────────────────────────────────────────────
// Generate Paper Modal
// ─────────────────────────────────────────────
const GeneratePaperModal = ({ subject, onClose, onTaskStarted }) => {
  const fileInputRef = useRef(null);

  const [form, setForm] = useState({
    paper_type: 'MSE',
    unit_ids: [1, 2, 3],
    total_marks: 30,
    question_counts: { '2': 5, '5': 2, '10': 1 },
  });
  const [additionalFiles, setAdditionalFiles] = useState([]);
  const [uploading, setUploading] = useState(false);
  const [uploadedPaths, setUploadedPaths] = useState([]);
  const [generating, setGenerating] = useState(false);
  const [previewData, setPreviewData] = useState(null);

  // Get syllabus units for the subject (max 5 default)
  const availableUnits = [1, 2, 3, 4, 5];

  // Calculated marks
  const calcTotal = Object.entries(form.question_counts).reduce(
    (sum, [marks, count]) => sum + parseInt(marks) * count,
    0
  );
  const blueprintValid = calcTotal === form.total_marks && calcTotal > 0;

  const toggleUnit = (unit) => {
    setForm((f) => ({
      ...f,
      unit_ids: f.unit_ids.includes(unit)
        ? f.unit_ids.filter((u) => u !== unit)
        : [...f.unit_ids, unit].sort((a, b) => a - b),
    }));
  };

  const updateCount = (marks, value) => {
    setForm((f) => ({
      ...f,
      question_counts: { ...f.question_counts, [String(marks)]: Math.max(0, parseInt(value) || 0) },
    }));
  };

  const handleFileSelect = (e) => {
    const files = Array.from(e.target.files || []);
    setAdditionalFiles((prev) => [...prev, ...files]);
  };

  const removeFile = (idx) => {
    setAdditionalFiles((prev) => prev.filter((_, i) => i !== idx));
  };

  const uploadFiles = async () => {
    if (!additionalFiles.length) return [];
    setUploading(true);
    try {
      const fd = new FormData();
      additionalFiles.forEach((f) => fd.append('files', f));
      const res = await api.post('/upload/temp', fd, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
      return res.data.file_paths || [];
    } catch (err) {
      alert('File upload failed: ' + (err.response?.data?.detail || err.message));
      return [];
    } finally {
      setUploading(false);
    }
  };

  const handleGenerate = async () => {
    if (!blueprintValid) return;
    if (form.unit_ids.length === 0) {
      alert('Please select at least one unit.');
      return;
    }

    setGenerating(true);
    try {
      let filePaths = uploadedPaths;
      if (additionalFiles.length > 0 && uploadedPaths.length === 0) {
        filePaths = await uploadFiles();
        setUploadedPaths(filePaths);
      }

      const payload = {
        paper_type: form.paper_type,
        unit_ids: form.unit_ids,
        total_marks: form.total_marks,
        question_counts: form.question_counts,
        additional_file_paths: filePaths,
      };

      const res = await api.post(`/subjects/${subject.id}/papers/generate`, payload);
      onTaskStarted(res.data.task_id);
      onClose();
    } catch (err) {
      const detail = err.response?.data;
      if (detail?.error === 'BLUEPRINT_MISMATCH') {
        alert(
          `Blueprint Mismatch!\n\n${detail.message}\n\nRequested: ${detail.requested_total}M\nCalculated: ${detail.calculated_total}M`
        );
      } else {
        alert(detail?.message || detail?.detail || 'Generation failed. Please try again.');
      }
    } finally {
      setGenerating(false);
    }
  };

  const breakdownItems = Object.entries(form.question_counts).filter(([, c]) => c > 0);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 backdrop-blur-sm p-4 animate-in fade-in">
      <div className="bg-slate-900 border border-slate-700 rounded-3xl w-full max-w-xl shadow-2xl max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="sticky top-0 bg-slate-900 border-b border-slate-800 px-6 py-4 flex items-center justify-between rounded-t-3xl">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-brand-500/10 flex items-center justify-center">
              <Sparkles className="w-5 h-5 text-brand-400" />
            </div>
            <div>
              <h3 className="text-base font-bold text-white">Generate Paper</h3>
              <p className="text-xs text-slate-400">Configure exam blueprint</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-2 rounded-xl hover:bg-slate-800 text-slate-400 hover:text-white transition"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        <div className="p-6 space-y-5">
          {/* Paper Type */}
          <div>
            <label className="block text-xs font-semibold text-slate-300 mb-2 uppercase tracking-wider">
              Paper Type
            </label>
            <div className="flex gap-3">
              {['MSE', 'ESE'].map((type) => (
                <button
                  key={type}
                  onClick={() => setForm((f) => ({ ...f, paper_type: type, total_marks: type === 'MSE' ? 30 : 50 }))}
                  className={`flex-1 py-2.5 rounded-xl text-sm font-bold border transition-all ${
                    form.paper_type === type
                      ? 'bg-brand-500 border-brand-500 text-white shadow-lg shadow-brand-500/20'
                      : 'bg-slate-800 border-slate-700 text-slate-300 hover:border-slate-600'
                  }`}
                >
                  {type}
                  <span className="block text-[10px] font-normal opacity-70 mt-0.5">
                    {type === 'MSE' ? 'Mid-Semester' : 'End-Semester'}
                  </span>
                </button>
              ))}
            </div>
          </div>

          {/* Unit Selection */}
          <div>
            <label className="block text-xs font-semibold text-slate-300 mb-2 uppercase tracking-wider">
              Units to Cover
            </label>
            <div className="flex flex-wrap gap-2">
              {availableUnits.map((unit) => {
                const selected = form.unit_ids.includes(unit);
                return (
                  <button
                    key={unit}
                    onClick={() => toggleUnit(unit)}
                    className={`flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-semibold border transition-all ${
                      selected
                        ? 'bg-brand-500/10 border-brand-500/50 text-brand-400'
                        : 'bg-slate-800 border-slate-700 text-slate-400 hover:border-slate-600'
                    }`}
                  >
                    <span
                      className={`w-3.5 h-3.5 rounded border flex items-center justify-center ${
                        selected ? 'bg-brand-500 border-brand-500' : 'border-slate-600'
                      }`}
                    >
                      {selected && <CheckCircle2 className="w-2.5 h-2.5 text-white" />}
                    </span>
                    Unit {unit}
                  </button>
                );
              })}
            </div>
            {form.unit_ids.length === 0 && (
              <p className="text-xs text-red-400 mt-1">Select at least one unit.</p>
            )}
          </div>

          {/* Total Marks */}
          <div>
            <label className="block text-xs font-semibold text-slate-300 mb-1.5 uppercase tracking-wider">
              Total Marks (Requested)
            </label>
            <input
              type="number"
              min={10}
              max={150}
              value={form.total_marks}
              onChange={(e) => setForm((f) => ({ ...f, total_marks: parseInt(e.target.value) || 0 }))}
              className="w-full bg-slate-950 border border-slate-700 rounded-xl px-3 py-2 text-sm text-white focus:outline-none focus:border-brand-500 transition"
            />
          </div>

          {/* Question Counts */}
          <div>
            <label className="block text-xs font-semibold text-slate-300 mb-2 uppercase tracking-wider">
              Question Configuration
            </label>
            <div className="bg-slate-950/60 rounded-2xl p-4 border border-slate-800 space-y-3">
              {[
                { marks: 2, label: '2-Mark Questions (Short Answer)' },
                { marks: 5, label: '5-Mark Questions (Descriptive)' },
                { marks: 10, label: '10-Mark Questions (Long Answer)' },
              ].map(({ marks, label }) => (
                <div key={marks} className="flex items-center justify-between gap-4">
                  <label className="text-xs text-slate-300 flex-1">{label}</label>
                  <div className="flex items-center gap-2">
                    <input
                      type="number"
                      min={0}
                      max={20}
                      value={form.question_counts[String(marks)] || 0}
                      onChange={(e) => updateCount(marks, e.target.value)}
                      className="w-16 bg-slate-900 border border-slate-700 rounded-lg px-2 py-1 text-xs text-center text-white focus:outline-none focus:border-brand-500"
                    />
                    <span className="text-xs text-slate-500 font-mono w-16 text-right">
                      = {marks * (form.question_counts[String(marks)] || 0)}M
                    </span>
                  </div>
                </div>
              ))}

              {/* Calculated Total */}
              <div className="pt-3 mt-1 border-t border-slate-800 flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Calculator className="w-4 h-4 text-slate-400" />
                  <span className="text-xs font-semibold text-slate-300">Calculated Total</span>
                </div>
                <div className="flex items-center gap-2">
                  <span
                    className={`text-sm font-bold font-mono ${
                      blueprintValid ? 'text-brand-400' : 'text-red-400'
                    }`}
                  >
                    {calcTotal}M
                  </span>
                  {blueprintValid ? (
                    <span className="flex items-center gap-1 text-xs text-brand-400 bg-brand-500/10 px-2 py-0.5 rounded-lg border border-brand-500/20">
                      <CheckCircle2 className="w-3 h-3" /> Valid
                    </span>
                  ) : (
                    <span className="flex items-center gap-1 text-xs text-red-400 bg-red-500/10 px-2 py-0.5 rounded-lg border border-red-500/20">
                      <AlertTriangle className="w-3 h-3" /> Mismatch
                    </span>
                  )}
                </div>
              </div>

              {!blueprintValid && form.total_marks > 0 && (
                <div className="bg-red-950/40 border border-red-800/50 rounded-xl p-3 text-xs text-red-300">
                  <strong className="block mb-0.5">⚠ Blueprint Mismatch — Cannot Generate</strong>
                  Requested: <strong>{form.total_marks}M</strong> · Configured: <strong>{calcTotal}M</strong>
                  <br />
                  Adjust question counts until calculated total matches requested total.
                </div>
              )}
            </div>
          </div>

          {/* Optional Additional Files */}
          <div>
            <label className="block text-xs font-semibold text-slate-300 mb-1.5 uppercase tracking-wider">
              Additional Reference Files{' '}
              <span className="text-slate-500 font-normal normal-case">(Optional)</span>
            </label>
            <p className="text-xs text-slate-500 mb-2">
              Upload previous papers, notes, or reference material for this generation only. Not added to permanent knowledge base.
            </p>

            <div
              onClick={() => fileInputRef.current?.click()}
              className="border border-dashed border-slate-700 rounded-2xl p-4 text-center cursor-pointer hover:border-brand-500/50 hover:bg-brand-500/5 transition group"
            >
              <FileUp className="w-6 h-6 text-slate-500 group-hover:text-brand-400 mx-auto mb-1.5 transition" />
              <p className="text-xs text-slate-400 group-hover:text-slate-300">
                Click to browse PDF / DOCX files
              </p>
            </div>
            <input
              ref={fileInputRef}
              type="file"
              accept=".pdf,.docx,.doc"
              multiple
              onChange={handleFileSelect}
              className="hidden"
            />

            {additionalFiles.length > 0 && (
              <div className="mt-2 space-y-1.5">
                {additionalFiles.map((file, idx) => (
                  <div
                    key={idx}
                    className="flex items-center justify-between bg-slate-800/60 rounded-xl px-3 py-2 text-xs"
                  >
                    <span className="text-slate-300 truncate max-w-[260px]">{file.name}</span>
                    <button
                      onClick={() => removeFile(idx)}
                      className="ml-2 text-slate-500 hover:text-red-400 transition shrink-0"
                    >
                      <X className="w-3.5 h-3.5" />
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Action Buttons */}
          <div className="flex justify-end gap-3 pt-2">
            <button
              onClick={onClose}
              className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-medium rounded-xl transition"
            >
              Cancel
            </button>
            <button
              onClick={handleGenerate}
              disabled={!blueprintValid || form.unit_ids.length === 0 || generating || uploading}
              className="inline-flex items-center gap-2 px-5 py-2 bg-brand-500 hover:bg-brand-600 disabled:opacity-50 disabled:cursor-not-allowed active:scale-95 text-white text-xs font-semibold rounded-xl transition shadow-lg shadow-brand-500/20"
            >
              {generating || uploading ? (
                <>
                  <Clock className="w-4 h-4 animate-spin" />
                  {uploading ? 'Uploading...' : 'Starting...'}
                </>
              ) : (
                <>
                  <Zap className="w-4 h-4" />
                  Generate {form.paper_type} Paper
                </>
              )}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

// ─────────────────────────────────────────────
// Main ExamsTab Component
// ─────────────────────────────────────────────
export const ExamsTab = ({ subject }) => {
  const [exams, setExams] = useState([]);
  const [blueprints, setBlueprints] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedExam, setSelectedExam] = useState(null);
  const [taskId, setTaskId] = useState(null);
  const [answerKey, setAnswerKey] = useState(null);
  const [loadingKey, setLoadingKey] = useState(false);
  const [showAnswerKey, setShowAnswerKey] = useState(false);
  const [showGenModal, setShowGenModal] = useState(false);

  const fetchExamsAndBlueprints = async () => {
    try {
      const [exRes, bpRes] = await Promise.all([
        api.get(`/subjects/${subject.id}/exams`),
        api.get(`/subjects/${subject.id}/blueprints`),
      ]);
      setExams(exRes.data);
      setBlueprints(bpRes.data);
      if (exRes.data.length > 0 && !selectedExam) {
        setSelectedExam(exRes.data[0]);
      }
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchExamsAndBlueprints();
  }, [subject.id]);

  useEffect(() => {
    if (selectedExam) {
      fetchAnswerKey(selectedExam.id);
    }
  }, [selectedExam?.id]);

  const fetchAnswerKey = async (examId) => {
    setLoadingKey(true);
    try {
      const res = await api.get(`/exams/${examId}/answer-key`);
      setAnswerKey(res.data);
    } catch (e) {
      setAnswerKey(null);
    } finally {
      setLoadingKey(false);
    }
  };

  const handleGenerateAnswerKey = async (examId) => {
    try {
      const res = await api.post(`/exams/${examId}/answer-key/generate`);
      setTaskId(res.data.task_id);
    } catch (err) {
      alert('Answer key generation failed');
    }
  };

  const handleApproveExam = async (examId) => {
    try {
      await api.post(`/exams/${examId}/approve`);
      fetchExamsAndBlueprints();
    } catch (err) {
      alert('Approval failed');
    }
  };

  const handleValidate = async (examId) => {
    try {
      const res = await api.post(`/exams/${examId}/validate`);
      alert(`Validation Complete!\nScore: ${res.data.score}%\nChecks: ${res.data.checks?.length || 0}`);
      fetchExamsAndBlueprints();
    } catch (err) {
      alert('Validation error');
    }
  };

  const valReport = selectedExam?.validation_report || {};

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="bg-slate-900 border border-slate-800 rounded-3xl p-6 flex flex-col md:flex-row items-center justify-between gap-4 shadow-xl">
        <div>
          <span className="text-xs font-mono font-semibold px-2.5 py-1 rounded-md bg-brand-500/10 text-brand-400 border border-brand-500/20 uppercase tracking-wider">
            Examinations &amp; Assessments
          </span>
          <h2 className="text-xl font-bold text-white mt-2">Exam Paper Generator</h2>
          <p className="text-xs text-slate-400 mt-1 max-w-xl">
            Generate MSE or ESE papers with deterministic blueprint validation, marks arithmetic,
            section layouts, internal choices, and answer key rubrics.
          </p>
        </div>

        <button
          onClick={() => setShowGenModal(true)}
          className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-brand-500 hover:bg-brand-600 active:scale-95 text-white font-semibold text-sm transition shadow-lg shadow-brand-500/20 shrink-0"
        >
          <Sparkles className="w-4 h-4" />
          Generate Paper
        </button>
      </div>

      {loading ? (
        <div className="text-center py-12 text-slate-500">Loading exam papers...</div>
      ) : exams.length === 0 ? (
        <div className="bg-slate-900 border border-dashed border-slate-800 rounded-3xl p-12 text-center">
          <FileText className="w-12 h-12 text-slate-600 mx-auto mb-3" />
          <h3 className="text-base font-semibold text-white">No Exam Papers Generated</h3>
          <p className="text-xs text-slate-400 max-w-sm mx-auto mt-1 mb-5">
            Generate an official Mid-Semester or End-Semester examination paper with AI grounding.
          </p>
          <button
            onClick={() => setShowGenModal(true)}
            className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-brand-500 hover:bg-brand-600 text-white text-xs font-semibold transition shadow-lg shadow-brand-500/20"
          >
            <Sparkles className="w-4 h-4" />
            Generate Your First Paper
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Exam List Sidebar */}
          <div className="space-y-3">
            {exams.map((ex) => {
              const isSelected = selectedExam?.id === ex.id;
              return (
                <div
                  key={ex.id}
                  onClick={() => setSelectedExam(ex)}
                  className={`cursor-pointer p-4 rounded-2xl border transition-all duration-200 ${
                    isSelected
                      ? 'bg-slate-850 border-brand-500 shadow-lg shadow-brand-500/10'
                      : 'bg-slate-900 border-slate-800 hover:border-slate-700'
                  }`}
                >
                  <div className="flex items-center justify-between mb-1.5">
                    <span className="px-2 py-0.5 rounded bg-brand-500/10 text-brand-400 font-mono text-xs font-bold">
                      {ex.exam_type} • {ex.total_marks}M
                    </span>
                    <span
                      className={`text-[10px] px-2 py-0.5 rounded font-mono ${
                        ex.status === 'APPROVED'
                          ? 'text-brand-400 bg-brand-500/10'
                          : 'text-amber-400 bg-amber-500/10'
                      }`}
                    >
                      {ex.status}
                    </span>
                  </div>
                  <h4 className="font-semibold text-white text-sm line-clamp-1">{ex.title}</h4>
                  <p className="text-xs text-slate-400 mt-1">{ex.questions?.length || 0} Questions</p>
                </div>
              );
            })}

            {/* Quick re-generate button in sidebar */}
            <button
              onClick={() => setShowGenModal(true)}
              className="w-full flex items-center justify-center gap-2 p-3 rounded-2xl border border-dashed border-slate-700 hover:border-brand-500/50 text-slate-500 hover:text-brand-400 text-xs font-medium transition"
            >
              <Sparkles className="w-3.5 h-3.5" />
              Generate Another Paper
            </button>
          </div>

          {/* Paper Detail Column */}
          <div className="lg:col-span-2 space-y-6">
            {selectedExam && (
              <div className="bg-slate-900 border border-slate-800 rounded-3xl p-6 shadow-xl">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-6 mb-6 border-b border-slate-800 gap-4">
                  <div>
                    <div className="flex items-center gap-2 mb-1">
                      <span className="px-2.5 py-0.5 rounded-lg bg-brand-500/10 text-brand-400 font-mono text-xs font-bold border border-brand-500/20">
                        {selectedExam.exam_type}
                      </span>
                      <h3 className="text-lg font-bold text-white">{selectedExam.title}</h3>
                    </div>
                    <p className="text-xs text-slate-400">
                      Total Marks: {selectedExam.total_marks}M | Version {selectedExam.version}
                    </p>
                  </div>

                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => handleValidate(selectedExam.id)}
                      className="p-2 rounded-xl bg-slate-800 hover:bg-slate-750 text-slate-300 border border-slate-700 text-xs transition"
                      title="Validate Constraints"
                    >
                      <FileCheck2 className="w-4 h-4" />
                    </button>

                    {selectedExam.status !== 'APPROVED' && (
                      <button
                        onClick={() => handleApproveExam(selectedExam.id)}
                        className="inline-flex items-center gap-1.5 px-3.5 py-2 bg-brand-500 hover:bg-brand-600 text-white text-xs font-semibold rounded-xl transition shadow-lg shadow-brand-500/20"
                      >
                        <CheckCircle2 className="w-3.5 h-3.5" /> Approve Paper
                      </button>
                    )}
                  </div>
                </div>

                {/* Validation Report Banner */}
                {valReport?.checks && (
                  <div className="bg-slate-950/80 border border-slate-800 rounded-2xl p-4 mb-6">
                    <div className="flex items-center justify-between mb-3">
                      <span className="text-xs font-mono font-bold text-slate-400 uppercase">
                        Paper Quality &amp; Constraint Verification
                      </span>
                      <span className="text-xs font-mono font-bold text-brand-400">
                        Score: {valReport.score || 100}%
                      </span>
                    </div>

                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                      {valReport.checks.map((chk, idx) => (
                        <div key={idx} className="flex items-center gap-2 text-xs">
                          {chk.passed ? (
                            <CheckCircle2 className="w-3.5 h-3.5 text-brand-400 shrink-0" />
                          ) : (
                            <AlertTriangle className="w-3.5 h-3.5 text-red-400 shrink-0" />
                          )}
                          <span className="text-slate-300 truncate">{chk.message}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Instructions */}
                {selectedExam.instructions && (
                  <div className="bg-slate-950/60 rounded-xl p-3.5 border border-slate-800 text-xs text-slate-400 mb-6 italic whitespace-pre-wrap">
                    {selectedExam.instructions}
                  </div>
                )}

                {/* Questions */}
                <div className="space-y-4">
                  {(selectedExam.questions || []).map((eq, idx) => (
                    <div key={eq.id || idx} className="bg-slate-950/80 border border-slate-800 rounded-2xl p-4">
                      <div className="flex items-start justify-between gap-3">
                        <div>
                          <div className="flex items-center gap-2 mb-1.5 font-mono text-xs">
                            <span className="font-bold text-brand-400">Q{eq.sequence_order}.</span>
                            {eq.section && <span className="text-slate-500 font-semibold">{eq.section}</span>}
                            {eq.choice_group && (
                              <span className="px-1.5 py-0.5 rounded bg-amber-500/10 text-amber-400 text-[10px]">
                                Internal Choice ({eq.choice_group})
                              </span>
                            )}
                          </div>
                          <p className="text-sm text-white font-medium">{eq.question?.question_text}</p>
                        </div>

                        <div className="text-right shrink-0">
                          <span className="font-mono font-bold text-xs text-brand-400 bg-brand-500/10 px-2 py-1 rounded-lg border border-brand-500/20 block">
                            [{eq.marks}M]
                          </span>
                          <span className="text-[10px] text-slate-500 font-mono block mt-1">
                            {eq.question?.bloom_level}
                          </span>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>

                {/* Answer Key Section */}
                <div className="mt-8 pt-6 border-t border-slate-800">
                  <div className="flex items-center justify-between mb-4">
                    <div className="flex items-center gap-2">
                      <KeyRound className="w-5 h-5 text-amber-400" />
                      <h4 className="font-bold text-white text-sm">Official Answer Key &amp; Rubric</h4>
                    </div>

                    {answerKey ? (
                      <button
                        onClick={() => setShowAnswerKey(!showAnswerKey)}
                        className="text-xs text-brand-400 hover:underline font-semibold font-mono"
                      >
                        {showAnswerKey ? 'Hide Answer Key' : 'View Answer Key →'}
                      </button>
                    ) : (
                      <button
                        onClick={() => handleGenerateAnswerKey(selectedExam.id)}
                        className="inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-xl bg-slate-800 hover:bg-slate-750 text-amber-400 border border-slate-700 text-xs font-semibold transition"
                      >
                        <Sparkles className="w-3.5 h-3.5" /> Generate Answer Key
                      </button>
                    )}
                  </div>

                  {showAnswerKey && answerKey && (
                    <div className="space-y-3 bg-slate-950/90 rounded-2xl p-4 border border-slate-800 animate-in fade-in">
                      {(answerKey.answers || []).map((ans, idx) => (
                        <div key={idx} className="bg-slate-900 rounded-xl p-3 border border-slate-800 text-xs space-y-2">
                          <div className="flex items-center justify-between font-mono">
                            <span className="font-bold text-brand-400">
                              Answer Q{ans.sequence_order} [{ans.marks}M]
                            </span>
                          </div>
                          <p className="text-slate-200 whitespace-pre-wrap">{ans.model_answer}</p>
                          {ans.marking_scheme && (
                            <div className="text-[11px] font-mono text-purple-300 bg-slate-950 p-2 rounded-lg border border-slate-800">
                              <strong>Marking Breakdown:</strong> {ans.marking_scheme}
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Generate Paper Modal */}
      {showGenModal && (
        <GeneratePaperModal
          subject={subject}
          onClose={() => setShowGenModal(false)}
          onTaskStarted={(taskId) => {
            setTaskId(taskId);
            setShowGenModal(false);
          }}
        />
      )}

      <TaskProgressModal
        taskId={taskId}
        title="Processing Examination Paper"
        onComplete={() => {
          setTaskId(null);
          fetchExamsAndBlueprints();
        }}
        onClose={() => setTaskId(null)}
      />
    </div>
  );
};
