import React, { useState, useEffect } from 'react';
import { Sparkles, Plus, FileText, CheckCircle2, CheckCheck, ChevronDown, ChevronUp } from 'lucide-react';
import api from '../../services/api';
import { TaskProgressModal } from '../common/TaskProgressModal';

export const AssignmentsTab = ({ subject }) => {
  const [assignments, setAssignments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [taskId, setTaskId] = useState(null);
  const [showModal, setShowModal] = useState(false);
  const [selectedAssignment, setSelectedAssignment] = useState(null);

  const [form, setForm] = useState({
    title: 'Assignment 1: Fundamentals & Text Processing',
    total_marks: 20,
    num_questions: 4,
    units: [1, 2],
    difficulty: 'MEDIUM',
  });

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
    try {
      const res = await api.post(`/subjects/${subject.id}/assignments/generate`, form);
      setShowModal(false);
      setTaskId(res.data.task_id);
    } catch (err) {
      alert(err.response?.data?.detail || 'Assignment generation failed');
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
            Create balanced problem sets with exact mark allocation, Bloom levels, and step rubrics.
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
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4 animate-in fade-in">
          <div className="bg-slate-900 border border-slate-800 rounded-3xl w-full max-w-lg p-6 shadow-2xl">
            <h3 className="text-lg font-bold text-white mb-1">Generate Assignment</h3>
            <p className="text-xs text-slate-400 mb-5">Specify title, marks budget, and modules</p>

            <form onSubmit={handleGenerate} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">Assignment Title</label>
                <input
                  type="text"
                  required
                  value={form.title}
                  onChange={(e) => setForm({ ...form, title: e.target.value })}
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl p-2 text-xs text-white"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-slate-300 mb-1">Total Marks</label>
                  <input
                    type="number"
                    value={form.total_marks}
                    onChange={(e) => setForm({ ...form, total_marks: parseInt(e.target.value) })}
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl p-2 text-xs text-white"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-slate-300 mb-1">Number of Questions</label>
                  <input
                    type="number"
                    value={form.num_questions}
                    onChange={(e) => setForm({ ...form, num_questions: parseInt(e.target.value) })}
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl p-2 text-xs text-white"
                  />
                </div>
              </div>

              <div className="flex justify-end gap-2 pt-4">
                <button
                  type="button"
                  onClick={() => setShowModal(false)}
                  className="px-4 py-2 bg-slate-800 hover:bg-slate-750 text-slate-300 text-xs font-medium rounded-xl"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 bg-brand-500 hover:bg-brand-600 text-white text-xs font-semibold rounded-xl shadow-lg shadow-brand-500/20"
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
