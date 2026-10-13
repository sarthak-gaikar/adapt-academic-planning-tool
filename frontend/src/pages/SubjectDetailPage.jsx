import React, { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import {
  BookOpen,
  Layers,
  Table,
  Calendar,
  HelpCircle,
  FileText,
  FileCheck2,
  Download,
  Bot,
  ArrowLeft,
  GraduationCap,
  Sparkles,
  GitBranch,
  Network,
} from 'lucide-react';
import api from '../services/api';
import { SyllabusTab } from '../components/syllabus/SyllabusTab';
import { CourseOutcomesTab } from '../components/outcomes/CourseOutcomesTab';
import { LearningOutcomesTab } from '../components/outcomes/LearningOutcomesTab';
import { COPOMappingTab } from '../components/outcomes/COPOMappingTab';
import { COLOMappingTab } from '../components/mapping/COLOMappingTab';
import { LOPIMappingTab } from '../components/mapping/LOPIMappingTab';
import { OBEMatrixTab } from '../components/mapping/OBEMatrixTab';
import { AAPTab } from '../components/aap/AAPTab';
import { QuestionBankTab } from '../components/questions/QuestionBankTab';
import { AssignmentsTab } from '../components/assignments/AssignmentsTab';
import { ExamsTab } from '../components/exams/ExamsTab';
import { ExportTab } from '../components/export/ExportTab';
import { AgentConsoleTab } from '../components/agent/AgentConsoleTab';

export const SubjectDetailPage = () => {
  const { id } = useParams();
  const [subject, setSubject] = useState(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('syllabus');

  const fetchSubject = async () => {
    try {
      const res = await api.get(`/subjects/${id}`);
      setSubject(res.data);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchSubject();
  }, [id]);

  if (loading) {
    return <div className="text-center py-24 text-slate-500">Loading course workspace...</div>;
  }

  if (!subject) {
    return (
      <div className="text-center py-24">
        <h2 className="text-xl font-bold text-white mb-2">Subject Not Found</h2>
        <Link to="/dashboard" className="text-brand-400 text-sm hover:underline">
          Return to Dashboard
        </Link>
      </div>
    );
  }

  const tabs = [
    { id: 'syllabus', label: '1. Syllabus & RAG', icon: BookOpen },
    { id: 'outcomes', label: '2. Course Outcomes', icon: Layers },
    { id: 'los', label: '3. Learning Outcomes', icon: GraduationCap },
    { id: 'colo', label: '4. CO-LO Matrix', icon: GitBranch },
    { id: 'lopi', label: '5. LO-PI Matrix', icon: Network },
    { id: 'copo', label: '6. CO-PO Matrix', icon: Table },
    { id: 'obe', label: '7. OBE Matrix', icon: Sparkles },
    { id: 'aap', label: '8. Academic Plan', icon: Calendar },
    { id: 'questions', label: '9. Question Bank', icon: HelpCircle },
    { id: 'assignments', label: '10. Assignments', icon: FileText },
    { id: 'exams', label: '11. MSE & ESE', icon: FileCheck2 },
    { id: 'export', label: '12. Export', icon: Download },
    { id: 'agent', label: 'AI Agent', icon: Bot },
  ];

  return (
    <div className="max-w-7xl mx-auto px-6 py-6">
      {/* Top Header Breadcrumb */}
      <div className="mb-6 flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <Link
            to="/dashboard"
            className="inline-flex items-center gap-1.5 text-xs font-semibold text-slate-400 hover:text-white mb-2 transition"
          >
            <ArrowLeft className="w-3.5 h-3.5" /> Back to Dashboard
          </Link>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-black text-white tracking-tight">{subject.name}</h1>
            <span className="px-2.5 py-1 rounded-lg bg-brand-500/10 text-brand-400 font-mono text-xs font-bold border border-brand-500/20">
              {subject.course_code}
            </span>
          </div>
          <p className="text-xs text-slate-400 mt-1 font-mono">
            Credits: {subject.credits || 3} | Hours: {subject.teaching_hours || 45}h | Sem: {subject.semester || 'VI'} | {subject.department}
          </p>
        </div>
      </div>

      {/* Modern Navigation Tabs Bar */}
      <div className="flex items-center gap-1.5 overflow-x-auto pb-2 mb-8 border-b border-slate-800 no-scrollbar">
        {tabs.map((tab) => {
          const Icon = tab.icon;
          const isActive = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`inline-flex items-center gap-2 px-4 py-2.5 rounded-2xl text-xs font-semibold whitespace-nowrap transition-all duration-150 ${
                isActive
                  ? 'bg-brand-500 text-white shadow-lg shadow-brand-500/20'
                  : 'bg-slate-900/80 hover:bg-slate-850 text-slate-400 hover:text-slate-200 border border-slate-800/80'
              }`}
            >
              <Icon className="w-4 h-4" />
              <span>{tab.label}</span>
            </button>
          );
        })}
      </div>

      {/* Tab Content Render */}
      <div className="min-h-[500px]">
        {activeTab === 'syllabus' && <SyllabusTab subject={subject} onSyllabusUpdated={fetchSubject} />}
        {activeTab === 'outcomes' && <CourseOutcomesTab subject={subject} />}
        {activeTab === 'los' && <LearningOutcomesTab subject={subject} />}
        {activeTab === 'colo' && <COLOMappingTab subject={subject} />}
        {activeTab === 'lopi' && <LOPIMappingTab subject={subject} />}
        {activeTab === 'copo' && <COPOMappingTab subject={subject} />}
        {activeTab === 'obe' && <OBEMatrixTab subject={subject} />}
        {activeTab === 'aap' && <AAPTab subject={subject} />}
        {activeTab === 'questions' && <QuestionBankTab subject={subject} />}
        {activeTab === 'assignments' && <AssignmentsTab subject={subject} />}
        {activeTab === 'exams' && <ExamsTab subject={subject} />}
        {activeTab === 'export' && <ExportTab subject={subject} />}
        {activeTab === 'agent' && <AgentConsoleTab subject={subject} onRefresh={fetchSubject} />}
      </div>
    </div>
  );
};
