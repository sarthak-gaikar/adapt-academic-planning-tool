import React, { useState, useEffect } from 'react';
import { Sparkles, Plus, FileText, CheckCircle2, X } from 'lucide-react';
import api from '../../services/api';
import { TaskProgressModal } from '../common/TaskProgressModal';

export const AssignmentsTab = ({ subject }) => {
  const [assignments, setAssignments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [taskId, setTaskId] = useState(null);
  const [showModal, setShowModal] = useState(false);
  const [selectedAssignment, setSelectedAssignment] = useState(null);

  const [form, setForm] = useState({
    units: [1, 2],
    difficulty: 'MEDIUM',
    total_marks: 20,
    question_counts: { '2': 5, '5': 2, '10': 0 },
  });

  const availableUnits = [1, 2, 3, 4, 5];

  // Calculated total marks from question breakdown
  const calcTotal = Object.entries(form.question_counts).reduce(
    (sum, [marks, count]) => sum + parseInt(marks) * count,
    0
  );
  const totalQuestions = Object.values(form.question_counts).reduce(
    (sum, count) => sum + count,
    0
  );
  const blueprintValid = calcTotal === form.total_marks && calcTotal > 0;

  const toggleUnit = (unit) => {
    setForm((f) => ({
      ...f,
      units: f.units.includes(unit)
        ? f.units.filter((u) => u !== unit)
        : [...f.units, unit].sort((a, b) => a - b),
    }));
  };

  const updateCount = (marks, value) => {
    const newCounts = { ...form.question_counts, [String(marks)]: Math.max(0, parseInt(value) || 0) };
    const newTotal = Object.entries(newCounts).reduce(
      (sum, [m, c]) => sum + parseInt(m) * c,
      0
    );
    setForm((f) => ({
      ...f,
      question_counts: newCounts,
      total_marks: newTotal,
    }));
  };

  const fetchAssignments = async () => {
    try {
      const res = await api.get(`/subjects/${subject.id}/assignments`);
      setAssignments(res.data);
      if (res.data.length > 0 && !selectedAssignment) {
        setSelectedAssignment(res.data[0]);
      }
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAssignments();
  }, [subject.id]);

  const handleGenerate = async (e) => {
    e.preventDefault();
    if (!blueprintValid) {
      alert(`Question marks breakdown sum (${calcTotal}M) must equal requested total (${form.total_marks}M).`);
      return;
    }
    if (form.units.length === 0) {
      alert('Please select at least one unit.');
      return;
    }

    try {
      const payload = {
        units: form.units,
        difficulty: form.difficulty,
        total_marks: form.total_marks,
        question_counts: form.question_counts,
      };
      const res = await api.post(`/subjects/${subject.id}/assignments/generate`, payload);
      setShowModal(false);
      setTaskId(res.data.task_id);
    } catch (err) {
      const detail = err.response?.data?.detail;
      if (detail?.error === 'BLUEPRINT_MISMATCH') {
        alert(`Blueprint Mismatch!\n\n${detail.message}`);
      } else {
        alert(detail?.message || detail || 'Assignment generation failed');
      }
    }
  };

  const handleApprove = async (aid) => {
    try {
      await api.post(`/assignments/${aid}/approve`);
      fetchAssignments();
    } catch (err) {
      alert('Approval failed');
    }
  };

  return (
    <div className="space-y-6">
      {/* Action Header */}
      <div className="bg-slate-900 border border-slate-800 rounded-3xl p-6 flex flex-col sm:flex-row items-center justify-between gap-4 shadow-xl">
        <div>
          <span className="text-xs font-mono font-semibold px-2.5 py-1 rounded-md bg-brand-500/10 text-brand-400 border border-brand-500/20 uppercase tracking-wider">
            Coursework & Homework
          </span>
          <h2 className="text-xl font-bold text-white mt-2">Continuous Assessment Assignments</h2>
          <p className="text-xs text-slate-400 mt-1 max-w-xl">
            Configure marks breakdown (2M, 5M, 10M) and target modules. The LLM automatically crafts an optimal title and questions.
          </p>
        </div>

        <button
          onClick={() => setShowModal(true)}
          className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-brand-500 hover:bg-brand-600 active:scale-95 text-white font-semibold text-xs transition shadow-lg shadow-brand-500/20"
        >
          <Plus className="w-4 h-4" />
          <span>Generate Assignment</span>
        </button>
      </div>

      {loading ? (
        <div className="text-center py-12 text-slate-500">Loading assignments...</div>
      ) : assignments.length === 0 ? (
        <div className="bg-slate-900 border border-dashed border-slate-800 rounded-3xl p-12 text-center">
          <FileText className="w-12 h-12 text-slate-600 mx-auto mb-3" />
          <h3 className="text-base font-semibold text-white">No Assignments Generated</h3>
          <p className="text-xs text-slate-400 max-w-sm mx-auto mt-1 mb-5">
            Generate balanced homework sets mapped to specific course modules.
          </p>
          <button
            onClick={() => setShowModal(true)}
            className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-brand-500 hover:bg-brand-600 text-white text-xs font-semibold"
          >
            <Plus className="w-3.5 h-3.5" /> Generate Assignment
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Assignment List Column */}
          <div className="space-y-3">
            {assignments.map((asg) => {
              const isSelected = selectedAssignment?.id === asg.id;
              return (
                <div
                  key={asg.id}
                  onClick={() => setSelectedAssignment(asg)}
                  className={`cursor-pointer p-4 rounded-2xl border transition-all duration-200 ${
                    isSelected
                      ? 'bg-slate-850 border-brand-500 shadow-lg shadow-brand-500/10'
                      : 'bg-slate-900 border-slate-800 hover:border-slate-700'
                  }`}
                >
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-xs font-mono font-bold text-brand-400">{asg.total_marks} Marks</span>
                    <span className={`text-[10px] px-2 py-0.5 rounded font-mono ${asg.status === 'APPROVED' ? 'text-brand-400 bg-brand-500/10' : 'text-amber-400 bg-amber-500/10'}`}>
                      {asg.status}
                    </span>
                  </div>
                  <h4 className="font-semibold text-white text-sm line-clamp-1">{asg.title}</h4>
                  <p className="text-xs text-slate-400 mt-1">{asg.questions?.length || 0} Questions</p>
                </div>
              );
            })}
          </div>

          {/* Selected Assignment Detail View */}
          <div className="lg:col-span-2 bg-slate-900 border border-slate-800 rounded-3xl p-6 shadow-xl">
            {selectedAssignment ? (
              <div>
                <div className="flex items-center justify-between pb-4 mb-4 border-b border-slate-800">
                  <div>
                    <h3 className="text-lg font-bold text-white">{selectedAssignment.title}</h3>
                    <p className="text-xs text-slate-400 mt-0.5">Total Marks: {selectedAssignment.total_marks}M</p>
                  </div>

                  {selectedAssignment.status !== 'APPROVED' && (
                    <button
                      onClick={() => handleApprove(selectedAssignment.id)}
                      className="inline-flex items-center gap-1.5 px-4 py-2 bg-brand-500 hover:bg-brand-600 text-white text-xs font-semibold rounded-xl transition shadow-lg shadow-brand-500/20"
                    >
                      <CheckCircle2 className="w-3.5 h-3.5" /> Approve Assignment
                    </button>
                  )}
                </div>

                {/* Question List */}
                <div className="space-y-4">
                  {(selectedAssignment.questions || []).map((aq, idx) => (
                    <div key={aq.id || idx} className="bg-slate-950/80 border border-slate-800 rounded-2xl p-4">
                      <div className="flex items-start justify-between gap-3">
                        <div>
                          <span className="text-xs font-mono font-bold text-brand-400 block mb-1">
                            Q{aq.sequence_order}. [{aq.marks} Marks]
                          </span>
                          <p className="text-sm text-white font-medium">{aq.question?.question_text}</p>
                        </div>
                      </div>

                      {aq.question?.reference_answer && (
                        <div className="mt-3 pt-3 border-t border-slate-800/80 text-xs text-slate-300">
                          <strong className="text-[10px] font-mono uppercase text-brand-400 block mb-0.5">Model Answer:</strong>
                          <p className="text-slate-300">{aq.question.reference_answer}</p>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            ) : (
              <div className="text-center py-12 text-slate-500">Select an assignment to view questions.</div>
            )}
          </div>
        </div>
      )}

      {/* Modal */}
      {showModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 backdrop-blur-sm p-4 animate-in fade-in">
          <div className="bg-slate-900 border border-slate-700 rounded-3xl w-full max-w-xl p-6 shadow-2xl max-h-[90vh] overflow-y-auto">
            {/* Modal Header */}
            <div className="flex items-center justify-between pb-4 mb-4 border-b border-slate-800">
              <div className="flex items-center gap-3">
                <div className="w-9 h-9 rounded-xl bg-brand-500/10 flex items-center justify-center">
                  <Sparkles className="w-5 h-5 text-brand-400" />
                </div>
                <div>
                  <h3 className="text-base font-bold text-white">Generate Assignment</h3>
                  <p className="text-xs text-slate-400">Configure questions breakdown; title chosen by LLM</p>
                </div>
              </div>
              <button
                onClick={() => setShowModal(false)}
                className="p-2 rounded-xl hover:bg-slate-800 text-slate-400 hover:text-white transition"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <form onSubmit={handleGenerate} className="space-y-5">
              {/* Units to Cover */}
              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-2 uppercase tracking-wider">
                  Units to Cover
                </label>
                <div className="flex flex-wrap gap-2">
                  {availableUnits.map((unit) => {
                    const selected = form.units.includes(unit);
                    return (
                      <button
                        key={unit}
                        type="button"
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
                {form.units.length === 0 && (
                  <p className="text-xs text-red-400 mt-1">Select at least one unit.</p>
                )}
              </div>

              {/* Total Marks */}
              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1.5 uppercase tracking-wider">
                  Total Marks
                </label>
                <input
                  type="number"
                  min={1}
                  max={150}
                  value={form.total_marks}
                  onChange={(e) => setForm((f) => ({ ...f, total_marks: parseInt(e.target.value) || 0 }))}
                  className="w-full bg-slate-950 border border-slate-700 rounded-xl px-3 py-2 text-sm text-white focus:outline-none focus:border-brand-500 transition"
                />
              </div>

              {/* Question Configuration (2M, 5M, 10M) */}
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

                  {/* Calculated Total & Validation */}
                  <div className="pt-3 mt-1 border-t border-slate-800 flex items-center justify-between text-xs">
                    <span className="text-slate-400">
                      Total: <strong className="text-white">{totalQuestions} questions</strong>
                    </span>
                    <div className="flex items-center gap-2">
                      <span className="text-slate-400 font-mono">
                        Calculated: <strong className={blueprintValid ? 'text-brand-400' : 'text-amber-400'}>{calcTotal}M</strong> / {form.total_marks}M
                      </span>
                      {blueprintValid ? (
                        <span className="text-[10px] px-1.5 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 font-mono font-semibold">
                          MATCH
                        </span>
                      ) : (
                        <span className="text-[10px] px-1.5 py-0.5 rounded bg-amber-500/10 text-amber-400 border border-amber-500/20 font-mono font-semibold">
                          MISMATCH
                        </span>
                      )}
                    </div>
                  </div>
                </div>
              </div>

              {/* Title Notice */}
              <div className="bg-brand-500/5 border border-brand-500/20 rounded-2xl p-3 flex items-start gap-2.5">
                <Sparkles className="w-4 h-4 text-brand-400 mt-0.5 shrink-0" />
                <p className="text-xs text-brand-300/90 leading-relaxed">
                  <strong>AI Smart Title:</strong> The assignment title is automatically formulated by the LLM based on the questions and concepts generated.
                </p>
              </div>

              <div className="flex justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setShowModal(false)}
                  className="px-4 py-2 bg-slate-800 hover:bg-slate-750 text-slate-300 text-xs font-medium rounded-xl"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={!blueprintValid || form.units.length === 0}
                  className="px-5 py-2.5 bg-brand-500 hover:bg-brand-600 disabled:opacity-40 disabled:cursor-not-allowed text-white text-xs font-semibold rounded-xl shadow-lg shadow-brand-500/20 flex items-center gap-1.5 transition"
                >
                  <Sparkles className="w-3.5 h-3.5" />
                  <span>Generate Assignment</span>
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      <TaskProgressModal
        taskId={taskId}
        title="Generating Assignment"
        onComplete={() => {
          setTaskId(null);
          fetchAssignments();
        }}
        onClose={() => setTaskId(null)}
      />
    </div>
  );
};
