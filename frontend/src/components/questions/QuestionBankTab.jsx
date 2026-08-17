import React, { useState, useEffect } from 'react';
import {
  Sparkles,
  Search,
  Filter,
  CheckCircle2,
  Trash2,
  ChevronDown,
  ChevronUp,
  BookOpen,
  Plus,
  HelpCircle,
  Award,
} from 'lucide-react';
import api from '../../services/api';
import { TaskProgressModal } from '../common/TaskProgressModal';

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

  // Generation form
  const [genForm, setGenForm] = useState({
    unit_number: 1,
    topic: '',
    difficulty: 'MEDIUM',
    bloom_level: 'Apply',
    marks: 5,
    question_type: 'DESCRIPTIVE',
    count: 3,
  });

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

  const handleGenerate = async (e) => {
    e.preventDefault();
    try {
      const res = await api.post(`/subjects/${subject.id}/questions/generate`, genForm);
      setShowGenModal(false);
      setTaskId(res.data.task_id);
    } catch (err) {
      alert(err.response?.data?.detail || 'Generation failed');
    }
  };

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
            Generate your first batch of AI-curated questions for this subject.
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

      {/* Generate Questions Modal */}
      {showGenModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4 animate-in fade-in">
          <div className="bg-slate-900 border border-slate-800 rounded-3xl w-full max-w-lg p-6 shadow-2xl">
            <h3 className="text-lg font-bold text-white mb-1">Generate Questions with AI</h3>
            <p className="text-xs text-slate-400 mb-5">Configure specifications for RAG grounded question creation</p>

            <form onSubmit={handleGenerate} className="space-y-4">
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-slate-300 mb-1">Unit Number</label>
                  <select
                    value={genForm.unit_number}
                    onChange={(e) => setGenForm({ ...genForm, unit_number: parseInt(e.target.value) })}
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl p-2 text-xs text-white"
                  >
                    {[1, 2, 3, 4, 5].map((u) => (
                      <option key={u} value={u}>Unit {u}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block text-xs font-semibold text-slate-300 mb-1">Question Count</label>
                  <input
                    type="number"
                    min={1}
                    max={10}
                    value={genForm.count}
                    onChange={(e) => setGenForm({ ...genForm, count: parseInt(e.target.value) })}
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl p-2 text-xs text-white"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-slate-300 mb-1">Bloom Cognitive Level</label>
                  <select
                    value={genForm.bloom_level}
                    onChange={(e) => setGenForm({ ...genForm, bloom_level: e.target.value })}
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl p-2 text-xs text-white"
                  >
                    {['Remember', 'Understand', 'Apply', 'Analyze', 'Evaluate', 'Create'].map((b) => (
                      <option key={b} value={b}>{b}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block text-xs font-semibold text-slate-300 mb-1">Difficulty</label>
                  <select
                    value={genForm.difficulty}
                    onChange={(e) => setGenForm({ ...genForm, difficulty: e.target.value })}
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl p-2 text-xs text-white"
                  >
                    <option value="EASY">EASY</option>
                    <option value="MEDIUM">MEDIUM</option>
                    <option value="HARD">HARD</option>
                  </select>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-slate-300 mb-1">Marks per Question</label>
                  <input
                    type="number"
                    min={1}
                    max={20}
                    value={genForm.marks}
                    onChange={(e) => setGenForm({ ...genForm, marks: parseInt(e.target.value) })}
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl p-2 text-xs text-white"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-slate-300 mb-1">Question Type</label>
                  <select
                    value={genForm.question_type}
                    onChange={(e) => setGenForm({ ...genForm, question_type: e.target.value })}
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl p-2 text-xs text-white"
                  >
                    <option value="DESCRIPTIVE">DESCRIPTIVE</option>
                    <option value="SHORT">SHORT</option>
                    <option value="LONG">LONG</option>
                    <option value="NUMERICAL">NUMERICAL</option>
                    <option value="CODING">CODING</option>
                    <option value="MCQ">MCQ</option>
                  </select>
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">Specific Topic Focus (Optional)</label>
                <input
                  type="text"
                  placeholder="e.g. POS Tagging, Word Embeddings, Transformers"
                  value={genForm.topic}
                  onChange={(e) => setGenForm({ ...genForm, topic: e.target.value })}
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl p-2 text-xs text-white"
                />
              </div>

              <div className="flex justify-end gap-2 pt-4">
                <button
                  type="button"
                  onClick={() => setShowGenModal(false)}
                  className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-medium rounded-xl transition"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 bg-brand-500 hover:bg-brand-600 text-white text-xs font-semibold rounded-xl transition shadow-lg shadow-brand-500/20"
                >
                  Generate
                </button>
              </div>
            </form>
          </div>
        </div>
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
