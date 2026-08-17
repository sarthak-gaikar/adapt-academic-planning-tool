import React, { useState } from 'react';
import { Send, Bot, Sparkles, Terminal, CheckCircle2, ArrowRight } from 'lucide-react';
import api from '../../services/api';
import { TaskProgressModal } from '../common/TaskProgressModal';

export const AgentConsoleTab = ({ subject, onRefresh }) => {
  const [prompt, setPrompt] = useState('');
  const [taskId, setTaskId] = useState(null);
  const [history, setHistory] = useState([
    {
      role: 'assistant',
      text: `Hello Professor! I am your ADAPT Autonomous Agent for ${subject.name} (${subject.course_code}). You can give me natural language instructions like:
• "Generate 4 Course Outcomes for this syllabus"
• "Create an Academic Activity Plan for 15 weeks"
• "Generate a 30-mark MSE paper covering Units 1 to 3"
• "Generate 3 hard questions on Text Classification for Unit 2"`,
    },
  ]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!prompt.trim()) return;

    const userMsg = prompt;
    setPrompt('');
    setHistory((prev) => [...prev, { role: 'user', text: userMsg }]);

    try {
      const res = await api.post('/agent/execute', {
        subject_id: subject.id,
        prompt: userMsg,
      });
      setTaskId(res.data.task_id);
    } catch (err) {
      setHistory((prev) => [
        ...prev,
        { role: 'assistant', text: `Error: ${err.response?.data?.message || 'Failed to dispatch command.'}` },
      ]);
    }
  };

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <div className="bg-slate-900 border border-slate-800 rounded-3xl p-6 shadow-xl">
        <div className="flex items-center gap-3 mb-2">
          <div className="p-2 rounded-xl bg-brand-500/10 text-brand-400">
            <Bot className="w-5 h-5" />
          </div>
          <div>
            <h2 className="text-xl font-bold text-white">Autonomous Academic Supervisor Agent</h2>
            <p className="text-xs text-slate-400">Reasoning and multi-tool coordination engine</p>
          </div>
        </div>

        {/* Message Trace */}
        <div className="my-6 space-y-4 max-h-[450px] overflow-y-auto pr-2">
          {history.map((msg, idx) => (
            <div
              key={idx}
              className={`flex gap-3 text-xs leading-relaxed ${
                msg.role === 'user' ? 'justify-end' : 'justify-start'
              }`}
            >
              {msg.role === 'assistant' && (
                <div className="w-7 h-7 rounded-xl bg-brand-500/20 text-brand-400 flex items-center justify-center shrink-0 font-bold font-mono text-[10px]">
                  AI
                </div>
              )}
              <div
                className={`p-4 rounded-2xl max-w-xl whitespace-pre-wrap ${
                  msg.role === 'user'
                    ? 'bg-brand-500 text-white font-medium shadow-md shadow-brand-500/10'
                    : 'bg-slate-950 border border-slate-800 text-slate-200'
                }`}
              >
                {msg.text}
              </div>
            </div>
          ))}
        </div>

        {/* Prompt Input */}
        <form onSubmit={handleSubmit} className="relative mt-4">
          <input
            type="text"
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            placeholder="Instruct the agent (e.g. 'Generate a 30-mark MSE paper for Units 1-3')..."
            className="w-full bg-slate-950 border border-slate-800 rounded-2xl py-3.5 pl-4 pr-12 text-xs text-white focus:outline-none focus:border-brand-500 focus:ring-1 focus:ring-brand-500 transition shadow-inner"
          />
          <button
            type="submit"
            className="absolute right-2.5 top-1/2 -translate-y-1/2 p-2 rounded-xl bg-brand-500 hover:bg-brand-600 active:scale-95 text-white transition shadow-md shadow-brand-500/20"
          >
            <Send className="w-3.5 h-3.5" />
          </button>
        </form>
      </div>

      <TaskProgressModal
        taskId={taskId}
        title="Supervisor Agent Execution"
        onComplete={(result) => {
          setTaskId(null);
          setHistory((prev) => [
            ...prev,
            { role: 'assistant', text: `Success! Orchestrated ${result?.steps_executed || 1} tool operations:\n` + (result?.results?.map((r) => `✓ ${r.message}`).join('\n') || 'All tools finished successfully.') },
          ]);
          if (onRefresh) onRefresh();
        }}
        onClose={() => setTaskId(null)}
      />
    </div>
  );
};
