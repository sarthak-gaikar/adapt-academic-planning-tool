import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import {
  BookOpen,
  Plus,
  ArrowUpRight,
  FileCheck2,
  Sparkles,
  Layers,
  HelpCircle,
  FileText,
  Calendar,
  CheckCircle2,
} from 'lucide-react';
import api from '../services/api';
import { useAuth } from '../context/AuthContext';

export const DashboardPage = () => {
  const { user } = useAuth();
  const [subjects, setSubjects] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [newSubj, setNewSubj] = useState({
    name: 'Natural Language Processing',
    course_code: 'CS602',
    credits: 4,
    teaching_hours: 45,
    semester: 'VI',
    academic_year: '2024-25',
    department: 'Department of Computer Science & Engineering',
  });

  const fetchSubjects = async () => {
    try {
      const res = await api.get('/subjects');
      setSubjects(res.data);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchSubjects();
  }, []);

  const handleCreateSubject = async (e) => {
    e.preventDefault();
    try {
      await api.post('/subjects', newSubj);
      setShowCreateModal(false);
      fetchSubjects();
    } catch (err) {
      alert(err.response?.data?.detail || 'Failed to create subject');
    }
  };

  return (
    <div className="max-w-7xl mx-auto px-6 py-8">
      {/* Hero Welcome */}
      <div className="relative overflow-hidden rounded-3xl bg-gradient-to-r from-slate-900 via-slate-850 to-slate-900 border border-slate-800 p-8 shadow-2xl mb-10">
        <div className="absolute top-0 right-0 w-96 h-96 bg-brand-500/10 rounded-full blur-3xl pointer-events-none" />
        <div className="relative z-10 flex flex-col md:flex-row md:items-center justify-between gap-6">
          <div>
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-brand-500/10 border border-brand-500/20 text-brand-400 text-xs font-mono font-medium mb-3">
              <Sparkles className="w-3.5 h-3.5" /> Outcomes-Based Education Engine
            </div>
            <h1 className="text-3xl font-extrabold text-white tracking-tight">
              Welcome back, {user?.full_name || 'Professor'}
            </h1>
            <p className="text-slate-400 text-sm mt-1.5 max-w-2xl">
              Transform syllabus documents into fully mapped Course Outcomes, 15-week Academic Activity Plans, validated MSE/ESE papers, and export-ready DOCX assessments.
            </p>
          </div>

          <button
            onClick={() => setShowCreateModal(true)}
            className="inline-flex items-center gap-2 px-5 py-3 rounded-2xl bg-brand-500 hover:bg-brand-600 active:scale-95 text-white font-semibold text-sm transition shadow-lg shadow-brand-500/25 shrink-0"
          >
            <Plus className="w-5 h-5" />
            Add New Subject
          </button>
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5 mb-10">
        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 shadow-lg">
          <div className="flex items-center justify-between mb-3">
            <span className="text-xs font-medium text-slate-400">Total Subjects</span>
            <div className="p-2 rounded-xl bg-blue-500/10 text-blue-400"><BookOpen className="w-5 h-5" /></div>
          </div>
          <div className="text-2xl font-bold text-white">{subjects.length}</div>
          <p className="text-[11px] text-slate-500 mt-1">Active OBE Courses</p>
        </div>

        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 shadow-lg">
          <div className="flex items-center justify-between mb-3">
            <span className="text-xs font-medium text-slate-400">OBE Mapping Status</span>
            <div className="p-2 rounded-xl bg-brand-500/10 text-brand-400"><Layers className="w-5 h-5" /></div>
          </div>
          <div className="text-2xl font-bold text-white">NBA/AICTE</div>
          <p className="text-[11px] text-brand-400/80 mt-1 flex items-center gap-1">
            <CheckCircle2 className="w-3.5 h-3.5" /> 12 POs & 6 Bloom Levels
          </p>
        </div>

        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 shadow-lg">
          <div className="flex items-center justify-between mb-3">
            <span className="text-xs font-medium text-slate-400">Deterministic Engine</span>
            <div className="p-2 rounded-xl bg-purple-500/10 text-purple-400"><FileCheck2 className="w-5 h-5" /></div>
          </div>
          <div className="text-2xl font-bold text-white">Active</div>
          <p className="text-[11px] text-slate-500 mt-1">Marks, Bloom & Duplicate Checks</p>
        </div>

        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 shadow-lg">
          <div className="flex items-center justify-between mb-3">
            <span className="text-xs font-medium text-slate-400">Export Ready</span>
            <div className="p-2 rounded-xl bg-amber-500/10 text-amber-400"><FileText className="w-5 h-5" /></div>
          </div>
          <div className="text-2xl font-bold text-white">DOCX / PDF</div>
          <p className="text-[11px] text-slate-500 mt-1">Official University Templates</p>
        </div>
      </div>

      {/* Course List Section */}
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold text-white tracking-tight">Your Academic Subjects</h2>
          <p className="text-xs text-slate-400 mt-0.5">Select a course to access its syllabus, question bank, and exam generation</p>
        </div>
      </div>

      {loading ? (
        <div className="text-center py-16 text-slate-500">Loading courses...</div>
      ) : subjects.length === 0 ? (
        <div className="bg-slate-900 border border-dashed border-slate-800 rounded-3xl p-12 text-center">
          <BookOpen className="w-12 h-12 text-slate-600 mx-auto mb-4" />
          <h3 className="text-base font-semibold text-white">No Subjects Added Yet</h3>
          <p className="text-xs text-slate-400 max-w-sm mx-auto mt-1 mb-6">
            Create your first university subject to upload a syllabus and automatically generate curriculum artifacts.
          </p>
          <button
            onClick={() => setShowCreateModal(true)}
            className="inline-flex items-center gap-2 px-4 py-2.5 rounded-xl bg-brand-500 hover:bg-brand-600 text-white text-xs font-semibold shadow-lg shadow-brand-500/20"
          >
            <Plus className="w-4 h-4" /> Create Course
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {subjects.map((sub) => (
            <Link
              key={sub.id}
              to={`/subjects/${sub.id}`}
              className="group bg-slate-900 hover:bg-slate-850 border border-slate-800 hover:border-slate-700 rounded-3xl p-6 transition-all duration-200 shadow-xl hover:-translate-y-1 relative flex flex-col justify-between"
            >
              <div>
                <div className="flex items-center justify-between mb-4">
                  <span className="px-2.5 py-1 rounded-lg bg-brand-500/10 text-brand-400 font-mono text-xs font-semibold border border-brand-500/20">
                    {sub.course_code}
                  </span>
                  <div className="p-2 rounded-xl bg-slate-800 group-hover:bg-brand-500 group-hover:text-white text-slate-400 transition">
                    <ArrowUpRight className="w-4 h-4" />
                  </div>
                </div>

                <h3 className="text-lg font-bold text-white group-hover:text-brand-300 transition line-clamp-1">
                  {sub.name}
                </h3>
                <p className="text-xs text-slate-400 mt-1 line-clamp-1">{sub.department || 'Computer Engineering'}</p>

                <div className="grid grid-cols-3 gap-2 mt-6 pt-4 border-t border-slate-800/80 text-center">
                  <div className="bg-slate-950/60 rounded-xl p-2">
                    <span className="block text-[10px] text-slate-500 uppercase font-mono">Credits</span>
                    <span className="font-semibold text-xs text-slate-200">{sub.credits || 3}</span>
                  </div>
                  <div className="bg-slate-950/60 rounded-xl p-2">
                    <span className="block text-[10px] text-slate-500 uppercase font-mono">Hours</span>
                    <span className="font-semibold text-xs text-slate-200">{sub.teaching_hours || 45}h</span>
                  </div>
                  <div className="bg-slate-950/60 rounded-xl p-2">
                    <span className="block text-[10px] text-slate-500 uppercase font-mono">Semester</span>
                    <span className="font-semibold text-xs text-slate-200">{sub.semester || 'VI'}</span>
                  </div>
                </div>
              </div>

              <div className="mt-5 pt-3 flex items-center justify-between text-[11px] text-slate-500">
                <span>Academic Year: {sub.academic_year || '2024-25'}</span>
                <span className="text-brand-400 font-medium group-hover:underline">Open Workspace →</span>
              </div>
            </Link>
          ))}
        </div>
      )}

      {/* Create Subject Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4 animate-in fade-in">
          <div className="bg-slate-900 border border-slate-800 rounded-3xl w-full max-w-lg p-6 shadow-2xl">
            <h3 className="text-lg font-bold text-white mb-1">Create New Subject</h3>
            <p className="text-xs text-slate-400 mb-6">Enter academic course specifications</p>

            <form onSubmit={handleCreateSubject} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">Course Name</label>
                <input
                  type="text"
                  required
                  value={newSubj.name}
                  onChange={(e) => setNewSubj({ ...newSubj, name: e.target.value })}
                  placeholder="e.g. Natural Language Processing"
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl py-2 px-3 text-sm text-white focus:outline-none focus:border-brand-500"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-slate-300 mb-1">Course Code</label>
                  <input
                    type="text"
                    required
                    value={newSubj.course_code}
                    onChange={(e) => setNewSubj({ ...newSubj, course_code: e.target.value })}
                    placeholder="e.g. CS602"
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl py-2 px-3 text-sm text-white focus:outline-none focus:border-brand-500"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-slate-300 mb-1">Credits</label>
                  <input
                    type="number"
                    value={newSubj.credits}
                    onChange={(e) => setNewSubj({ ...newSubj, credits: parseInt(e.target.value) })}
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl py-2 px-3 text-sm text-white focus:outline-none focus:border-brand-500"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-slate-300 mb-1">Teaching Hours</label>
                  <input
                    type="number"
                    value={newSubj.teaching_hours}
                    onChange={(e) => setNewSubj({ ...newSubj, teaching_hours: parseInt(e.target.value) })}
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl py-2 px-3 text-sm text-white focus:outline-none focus:border-brand-500"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-slate-300 mb-1">Semester</label>
                  <input
                    type="text"
                    value={newSubj.semester}
                    onChange={(e) => setNewSubj({ ...newSubj, semester: e.target.value })}
                    placeholder="e.g. VI"
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl py-2 px-3 text-sm text-white focus:outline-none focus:border-brand-500"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">Department</label>
                <input
                  type="text"
                  value={newSubj.department}
                  onChange={(e) => setNewSubj({ ...newSubj, department: e.target.value })}
                  placeholder="Department of Computer Science & Engineering"
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl py-2 px-3 text-sm text-white focus:outline-none focus:border-brand-500"
                />
              </div>

              <div className="flex justify-end gap-2 pt-4">
                <button
                  type="button"
                  onClick={() => setShowCreateModal(false)}
                  className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-medium rounded-xl transition"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 bg-brand-500 hover:bg-brand-600 text-white text-xs font-semibold rounded-xl transition shadow-lg shadow-brand-500/20"
                >
                  Create Subject
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
