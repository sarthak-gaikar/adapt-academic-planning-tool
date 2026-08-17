import React, { useState, useEffect } from 'react';
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
} from 'lucide-react';
import api from '../../services/api';
import { TaskProgressModal } from '../common/TaskProgressModal';

export const ExamsTab = ({ subject }) => {
  const [exams, setExams] = useState([]);
  const [blueprints, setBlueprints] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedExam, setSelectedExam] = useState(null);
  const [taskId, setTaskId] = useState(null);
  const [answerKey, setAnswerKey] = useState(null);
  const [loadingKey, setLoadingKey] = useState(false);
  const [showAnswerKey, setShowAnswerKey] = useState(false);

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

  const handleGenerateMSE = async () => {
    try {
      const res = await api.post(`/subjects/${subject.id}/mse/generate`);
      setTaskId(res.data.task_id);
    } catch (err) {
      alert(err.response?.data?.detail || 'MSE generation failed');
    }
  };

  const handleGenerateESE = async () => {
    try {
      const res = await api.post(`/subjects/${subject.id}/ese/generate`);
      setTaskId(res.data.task_id);
    } catch (err) {
      alert(err.response?.data?.detail || 'ESE generation failed');
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
      {/* Header with generate options */}
      <div className="bg-slate-900 border border-slate-800 rounded-3xl p-6 flex flex-col md:flex-row items-center justify-between gap-4 shadow-xl">
        <div>
          <span className="text-xs font-mono font-semibold px-2.5 py-1 rounded-md bg-brand-500/10 text-brand-400 border border-brand-500/20 uppercase tracking-wider">
            Examinations & Assessments
          </span>
          <h2 className="text-xl font-bold text-white mt-2">MSE & ESE Paper Generator</h2>
          <p className="text-xs text-slate-400 mt-1 max-w-xl">
            Deterministic blueprint validation, marks arithmetic, section layouts, internal choices, and answer key rubrics.
          </p>
        </div>

        <div className="flex items-center gap-3 shrink-0">
          <button
            onClick={handleGenerateMSE}
            className="inline-flex items-center gap-2 px-4 py-2.5 rounded-xl bg-slate-800 hover:bg-slate-750 text-white font-semibold text-xs transition border border-slate-700 shadow-lg"
          >
            <Sparkles className="w-4 h-4 text-brand-400" />
            <span>Generate 30M MSE</span>
          </button>

          <button
            onClick={handleGenerateESE}
            className="inline-flex items-center gap-2 px-4 py-2.5 rounded-xl bg-brand-500 hover:bg-brand-600 active:scale-95 text-white font-semibold text-xs transition shadow-lg shadow-brand-500/20"
          >
            <Sparkles className="w-4 h-4" />
            <span>Generate 50M ESE</span>
          </button>
        </div>
      </div>

      {loading ? (
        <div className="text-center py-12 text-slate-500">Loading exam papers...</div>
      ) : exams.length === 0 ? (
        <div className="bg-slate-900 border border-dashed border-slate-800 rounded-3xl p-12 text-center">
          <FileText className="w-12 h-12 text-slate-600 mx-auto mb-3" />
          <h3 className="text-base font-semibold text-white">No Exam Papers Generated</h3>
          <p className="text-xs text-slate-400 max-w-sm mx-auto mt-1 mb-5">
            Generate an official Mid-Semester or End-Semester examination paper.
          </p>
          <div className="flex items-center justify-center gap-3">
            <button
              onClick={handleGenerateMSE}
              className="px-4 py-2 rounded-xl bg-slate-800 text-slate-200 text-xs font-semibold"
            >
              Generate MSE
            </button>
            <button
              onClick={handleGenerateESE}
              className="px-4 py-2 rounded-xl bg-brand-500 text-white text-xs font-semibold"
            >
              Generate ESE
            </button>
          </div>
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
                    <span className={`text-[10px] px-2 py-0.5 rounded font-mono ${ex.status === 'APPROVED' ? 'text-brand-400 bg-brand-500/10' : 'text-amber-400 bg-amber-500/10'}`}>
                      {ex.status}
                    </span>
                  </div>
                  <h4 className="font-semibold text-white text-sm line-clamp-1">{ex.title}</h4>
                  <p className="text-xs text-slate-400 mt-1">{ex.questions?.length || 0} Questions</p>
                </div>
              );
            })}
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
                    <p className="text-xs text-slate-400">Total Marks: {selectedExam.total_marks}M | Version {selectedExam.version}</p>
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
                        Paper Quality & Constraint Verification
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
                      <h4 className="font-bold text-white text-sm">Official Answer Key & Rubric</h4>
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
                            <span className="font-bold text-brand-400">Answer Q{ans.sequence_order} [{ans.marks}M]</span>
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
