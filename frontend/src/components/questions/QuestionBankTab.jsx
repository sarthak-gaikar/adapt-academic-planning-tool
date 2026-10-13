import React, { useState, useEffect, useRef } from 'react';
import {
  Sparkles,
  Search,
  CheckCircle2,
  Trash2,
  ChevronDown,
  ChevronUp,
  BookOpen,
  Plus,
  X,
  Upload,
  FileUp,
  Calculator,
  AlertTriangle,
  Zap,
  Clock,
} from 'lucide-react';
import api from '../../services/api';
import { TaskProgressModal } from '../common/TaskProgressModal';

// ─────────────────────────────────────────────
// Blueprint Question Bank Generation Modal
// ─────────────────────────────────────────────
const GenerateQBModal = ({ subject, onClose, onTaskStarted }) => {
  const fileInputRef = useRef(null);

  // Unit selection
  const availableUnits = [1, 2, 3, 4, 5];
  const [selectedUnits, setSelectedUnits] = useState([1, 2, 3]);

  // Mark configs: 2M, 5M, 10M
  const [markCounts, setMarkCounts] = useState({ 2: 10, 5: 5, 10: 2 });

  // Optional files
  const [additionalFiles, setAdditionalFiles] = useState([]);
  const [uploading, setUploading] = useState(false);
  const [generating, setGenerating] = useState(false);

  // Calculated totals
  const totalMarks = Object.entries(markCounts).reduce(
    (sum, [marks, count]) => sum + parseInt(marks) * count,
    0
  );
  const totalQuestions = Object.values(markCounts).reduce((sum, c) => sum + c, 0);

  const toggleUnit = (unit) => {
    setSelectedUnits((prev) =>
      prev.includes(unit) ? prev.filter((u) => u !== unit) : [...prev, unit].sort((a, b) => a - b)
    );
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
    if (selectedUnits.length === 0) {
      alert('Please select at least one unit.');
      return;
    }
    if (totalQuestions === 0) {
      alert('Please configure at least one question.');
      return;
    }

    setGenerating(true);
    try {
      let filePaths = [];
      if (additionalFiles.length > 0) {
        filePaths = await uploadFiles();
      }

      const markConfigsArr = Object.entries(markCounts)
        .filter(([, count]) => count > 0)
        .map(([marks, count]) => ({ marks: parseInt(marks), count }));

      const payload = {
        units: selectedUnits,
        mark_configs: markConfigsArr,
        additional_file_paths: filePaths,
        difficulty: 'MIXED',
      };

      const res = await api.post(`/subjects/${subject.id}/question-bank/generate`, payload);
      onTaskStarted(res.data.task_id);
      onClose();
    } catch (err) {
      alert(err.response?.data?.detail || err.response?.data?.message || 'Generation failed.');
    } finally {
      setGenerating(false);
    }
  };

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
              <h3 className="text-base font-bold text-white">Generate Question Bank</h3>
              <p className="text-xs text-slate-400">Configure units &amp; blueprint</p>
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
          {/* Unit Selection */}
          <div>
            <label className="block text-xs font-semibold text-slate-300 mb-2 uppercase tracking-wider">
              Units to Generate From
            </label>
            <div className="flex flex-wrap gap-2">
              {availableUnits.map((unit) => {
                const selected = selectedUnits.includes(unit);
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
                      className={`w-3.5 h-3.5 rounded border flex items-center justify-center shrink-0 ${
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
            {selectedUnits.length === 0 && (
              <p className="text-xs text-red-400 mt-1">Select at least one unit.</p>
            )}
            {selectedUnits.length > 1 && (
              <p className="text-xs text-slate-500 mt-1">
                Questions will be distributed across {selectedUnits.length} units.
              </p>
            )}
          </div>

          {/* Question Blueprint */}
          <div>
            <label className="block text-xs font-semibold text-slate-300 mb-2 uppercase tracking-wider">
              Question Blueprint
            </label>
            <div className="bg-slate-950/60 rounded-2xl p-4 border border-slate-800 space-y-3">
              {[
                { marks: 2, label: '2-Mark Questions (Short Answer)' },
                { marks: 5, label: '5-Mark Questions (Descriptive)' },
                { marks: 10, label: '10-Mark Questions (Long Answer)' },
              ].map(({ marks, label }) => (
                <div key={marks} className="flex items-center justify-between gap-3">
                  <label className="text-xs text-slate-300 flex-1">{label}</label>
                  <div className="flex items-center gap-2">
                    <input
                      type="number"
                      min={0}
                      max={50}
                      value={markCounts[marks]}
                      onChange={(e) =>
                        setMarkCounts((prev) => ({ ...prev, [marks]: Math.max(0, parseInt(e.target.value) || 0) }))
                      }
                      className="w-16 bg-slate-900 border border-slate-700 rounded-lg px-2 py-1 text-xs text-center text-white focus:outline-none focus:border-brand-500"
                    />
                    <span className="text-xs text-slate-500 font-mono w-16 text-right">
                      = {marks * markCounts[marks]}M
                    </span>
                  </div>
                </div>
              ))}

              {/* Summary */}
              <div className="pt-3 mt-1 border-t border-slate-800">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Calculator className="w-4 h-4 text-slate-400" />
                    <span className="text-xs font-semibold text-slate-300">Calculated Total</span>
                  </div>
                  <div className="text-right">
                    <span className="text-sm font-bold font-mono text-brand-400">{totalMarks}M</span>
                    <span className="text-xs text-slate-500 font-mono ml-2">/ {totalQuestions} Qs</span>
                  </div>
                </div>

                {/* Breakdown */}
                {totalMarks > 0 && (
                  <div className="mt-2 space-y-1">
                    {Object.entries(markCounts)
                      .filter(([, c]) => c > 0)
                      .map(([marks, count]) => (
                        <div key={marks} className="flex justify-between text-[11px] text-slate-500 font-mono">
                          <span>{count} × {marks}M</span>
                          <span>= {parseInt(marks) * count}M</span>
                        </div>
                      ))}
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* Optional Additional Files */}
          <div>
            <label className="block text-xs font-semibold text-slate-300 mb-1.5 uppercase tracking-wider">
              Additional Reference Files{' '}
              <span className="text-slate-500 font-normal normal-case">(Optional)</span>
            </label>
            <p className="text-xs text-slate-500 mb-2">
              Upload previous papers, notes, or material for this generation only. Not added to permanent knowledge base.
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
                    <span className="text-slate-300 truncate max-w-[280px]">{file.name}</span>
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
              disabled={selectedUnits.length === 0 || totalQuestions === 0 || generating || uploading}
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
                  Generate {totalQuestions} Questions ({totalMarks}M)
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
// Main QuestionBankTab Component
// ─────────────────────────────────────────────
export const QuestionBankTab = ({ subject }) => {
  const [questions, setQuestions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [taskId, setTaskId] = useState(null);
  const [showGenModal, setShowGenModal] = useState(false);
  const [expandedId, setExpandedId] = useState(null);

  // Filters
  const [unitFilter, setUnitFilter] = useState('');
  const [bloomFilter, setBloomFilter] = useState('');
  const [diffFilter, setDiffFilter] = useState('');
  const [search, setSearch] = useState('');

  const fetchQuestions = async () => {
    try {
      const params = {};
      if (unitFilter) params.unit_number = parseInt(unitFilter);
      if (bloomFilter) params.bloom_level = bloomFilter;
      if (diffFilter) params.difficulty = diffFilter;
      if (search) params.search = search;

      const res = await api.get(`/subjects/${subject.id}/questions`, { params });
      setQuestions(res.data);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchQuestions();
  }, [subject.id, unitFilter, bloomFilter, diffFilter, search]);

  const handleApprove = async (qid) => {
    try {
      await api.post(`/questions/${qid}/approve`);
      fetchQuestions();
    } catch (err) {
      alert('Approval failed');
    }
  };

  const handleArchive = async (qid) => {
    try {
      await api.delete(`/questions/${qid}`);
      fetchQuestions();
    } catch (err) {
      alert('Archive failed');
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
      {/* Action Bar */}
      <div className="bg-slate-900 border border-slate-800 rounded-3xl p-6 flex flex-col sm:flex-row items-center justify-between gap-4 shadow-xl">
        <div>
          <span className="text-xs font-mono font-semibold px-2.5 py-1 rounded-md bg-brand-500/10 text-brand-400 border border-brand-500/20 uppercase tracking-wider">
            Assessment Repository
          </span>
          <h2 className="text-xl font-bold text-white mt-2">Subject Question Bank</h2>
          <p className="text-xs text-slate-400 mt-1 max-w-xl">
            Syllabus-grounded, duplicate-checked questions with model answers and step marking schemes.
            Select specific units and configure marks blueprint before generating.
          </p>
        </div>

        <button
          onClick={() => setShowGenModal(true)}
          className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-brand-500 hover:bg-brand-600 active:scale-95 text-white font-semibold text-xs transition shadow-lg shadow-brand-500/20"
        >
          <Plus className="w-4 h-4" />
          <span>Generate Questions</span>
        </button>
      </div>

      {/* Filter Bar */}
      <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-4 flex flex-wrap items-center gap-3 shadow-lg">
        <div className="relative flex-1 min-w-[200px]">
          <Search className="w-4 h-4 text-slate-500 absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            placeholder="Search questions by keyword..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full bg-slate-950 border border-slate-800 rounded-xl py-1.5 pl-9 pr-3 text-xs text-white focus:outline-none focus:border-brand-500"
          />
        </div>

        <select
          value={unitFilter}
          onChange={(e) => setUnitFilter(e.target.value)}
          className="bg-slate-950 border border-slate-800 rounded-xl px-3 py-1.5 text-xs text-slate-300 focus:outline-none focus:border-brand-500"
        >
          <option value="">All Units</option>
          {[1, 2, 3, 4, 5].map((u) => (
            <option key={u} value={u}>Unit {u}</option>
          ))}
        </select>

        <select
          value={bloomFilter}
          onChange={(e) => setBloomFilter(e.target.value)}
          className="bg-slate-950 border border-slate-800 rounded-xl px-3 py-1.5 text-xs text-slate-300 focus:outline-none focus:border-brand-500"
        >
          <option value="">All Bloom Levels</option>
          {['Remember', 'Understand', 'Apply', 'Analyze', 'Evaluate', 'Create'].map((b) => (
            <option key={b} value={b}>{b}</option>
          ))}
        </select>

        <select
          value={diffFilter}
          onChange={(e) => setDiffFilter(e.target.value)}
          className="bg-slate-950 border border-slate-800 rounded-xl px-3 py-1.5 text-xs text-slate-300 focus:outline-none focus:border-brand-500"
        >
          <option value="">All Difficulties</option>
          {['EASY', 'MEDIUM', 'HARD'].map((d) => (
            <option key={d} value={d}>{d}</option>
          ))}
        </select>
      </div>

      {/* Questions List */}
      {loading ? (
        <div className="text-center py-12 text-slate-500">Loading question bank...</div>
      ) : questions.length === 0 ? (
        <div className="bg-slate-900 border border-dashed border-slate-800 rounded-3xl p-12 text-center">
          <BookOpen className="w-12 h-12 text-slate-600 mx-auto mb-3" />
          <h3 className="text-base font-semibold text-white">No Questions in Bank</h3>
          <p className="text-xs text-slate-400 max-w-sm mx-auto mt-1 mb-5">
            Generate your first batch of AI-curated questions by selecting units and configuring a marks blueprint.
          </p>
          <button
            onClick={() => setShowGenModal(true)}
            className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-brand-500 hover:bg-brand-600 text-white text-xs font-semibold"
          >
            <Plus className="w-3.5 h-3.5" /> Generate Now
          </button>
        </div>
      ) : (
        <div className="space-y-4">
          {questions.map((q, idx) => {
            const isExpanded = expandedId === q.id;
            return (
              <div
                key={q.id}
                className="bg-slate-900 border border-slate-800 hover:border-slate-700 rounded-2xl p-5 shadow-lg transition"
              >
                <div className="flex items-start justify-between gap-4">
                  <div className="flex items-start gap-3 flex-1">
                    <span className="w-8 h-8 rounded-xl bg-slate-800 text-slate-300 font-mono font-bold text-xs flex items-center justify-center shrink-0">
                      #{idx + 1}
                    </span>

                    <div className="flex-1">
                      <p className="text-sm font-medium text-white leading-relaxed">{q.question_text}</p>

                      <div className="flex flex-wrap items-center gap-2 mt-3 text-xs">
                        <span className="px-2.5 py-0.5 rounded-full bg-brand-500/10 text-brand-400 font-mono font-bold border border-brand-500/20 text-[11px]">
                          {q.marks} Marks
                        </span>

                        <span className={`px-2.5 py-0.5 rounded-full font-mono text-[11px] font-semibold border ${getBloomBadgeColor(q.bloom_level)}`}>
                          {q.bloom_level}
                        </span>

                        <span className="px-2.5 py-0.5 rounded-full bg-slate-800 text-slate-300 font-mono text-[11px] border border-slate-700">
                          Unit {q.unit_number || 1}
                        </span>

                        {q.co_code && (
                          <span className="px-2.5 py-0.5 rounded-full bg-purple-500/10 text-purple-400 font-mono text-[11px] border border-purple-500/20">
                            {q.co_code}
                          </span>
                        )}

                        <span className="text-[10px] text-slate-500 font-mono uppercase">
                          {q.difficulty} • {q.question_type}
                        </span>

                        <span className={`text-[10px] px-2 py-0.5 rounded font-mono ${q.status === 'APPROVED' ? 'text-brand-400 bg-brand-500/10' : 'text-amber-400 bg-amber-500/10'}`}>
                          {q.status}
                        </span>
                      </div>
                    </div>
                  </div>

                  <div className="flex items-center gap-1.5 shrink-0">
                    <button
                      onClick={() => setExpandedId(isExpanded ? null : q.id)}
                      className="p-2 rounded-xl bg-slate-800 hover:bg-slate-750 text-slate-300 transition"
                      title="View Model Answer & Scheme"
                    >
                      {isExpanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                    </button>

                    {q.status !== 'APPROVED' && (
                      <button
                        onClick={() => handleApprove(q.id)}
                        className="p-2 rounded-xl bg-brand-500/10 hover:bg-brand-500 text-brand-400 hover:text-white transition"
                        title="Approve Question"
                      >
                        <CheckCircle2 className="w-4 h-4" />
                      </button>
                    )}

                    <button
                      onClick={() => handleArchive(q.id)}
                      className="p-2 rounded-xl hover:bg-red-500/10 text-slate-500 hover:text-red-400 transition"
                      title="Archive Question"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                </div>

                {/* Collapsible Model Answer & Scheme */}
                {isExpanded && (
                  <div className="mt-4 pt-4 border-t border-slate-800 space-y-3 animate-in fade-in duration-150">
                    {q.reference_answer && (
                      <div className="bg-slate-950/80 rounded-xl p-3.5 border border-slate-800 text-xs">
                        <strong className="block text-brand-400 mb-1 font-mono uppercase tracking-wider text-[10px]">
                          Model Answer / Solution
                        </strong>
                        <p className="text-slate-200 whitespace-pre-wrap">{q.reference_answer}</p>
                      </div>
                    )}

                    {q.marking_scheme && (
                      <div className="bg-slate-950/80 rounded-xl p-3.5 border border-slate-800 text-xs">
                        <strong className="block text-purple-400 mb-1 font-mono uppercase tracking-wider text-[10px]">
                          Step-by-Step Marking Scheme
                        </strong>
                        <p className="text-slate-300 font-mono text-[11px] whitespace-pre-wrap">{q.marking_scheme}</p>
                      </div>
                    )}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}

      {/* Generate Modal */}
      {showGenModal && (
        <GenerateQBModal
          subject={subject}
          onClose={() => setShowGenModal(false)}
          onTaskStarted={(tid) => {
            setTaskId(tid);
            setShowGenModal(false);
          }}
        />
      )}

      <TaskProgressModal
        taskId={taskId}
        title="Generating Question Bank"
        onComplete={() => {
          setTaskId(null);
          fetchQuestions();
        }}
        onClose={() => setTaskId(null)}
      />
    </div>
  );
};
