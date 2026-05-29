import React, { useState, useEffect, useRef } from 'react';
import {
  Shield,
  Send,
  Terminal,
  FileText,
  BarChart3,
  History,
  Sparkles,
  Download,
  Activity,
  ChevronRight,
  Database,
  RefreshCw
} from 'lucide-react';
import {
  ResponsiveContainer,
  ComposedChart,
  Line,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend
} from 'recharts';

interface AgentStep {
  agent: string;
  type: string; // thought, action, observation, status, result, completed, error
  content?: string;
  report?: string;
  chart_spec?: any;
}

interface HistoricalRequest {
  id: string;
  query: string;
  status: string;
  created_at: string;
}

export default function App() {
  // Query States
  const [query, setQuery] = useState('');
  const [isAnalyzing, setIsAnalyzing] = useState(false);

  // Real-time Agent Log States
  const [agentSteps, setAgentSteps] = useState<AgentStep[]>([]);
  const [currentStatus, setCurrentStatus] = useState('Idle. Ready for policy query.');

  // Analytical Output States
  const [report, setReport] = useState<string | null>(null);
  const [chartSpec, setChartSpec] = useState<any | null>(null);
  const [activeTab, setActiveTab] = useState<'report' | 'charts'>('report');

  // Historical Drawer States
  const [history, setHistory] = useState<HistoricalRequest[]>([]);
  const [selectedHistoryId, setSelectedHistoryId] = useState<string | null>(null);
  const [showHistory, setShowHistory] = useState(false);

  // Server Config/Connection info
  const [backendUrl, setBackendUrl] = useState('http://localhost:8000');
  const [wsUrl, setWsUrl] = useState('ws://localhost:8000/api/ws/analysis');
  const [llmProvider, setLlmProvider] = useState('mock');
  const [apiHealth, setApiHealth] = useState<'healthy' | 'unhealthy' | 'connecting'>('connecting');

  // Ref for auto-scrolling terminal
  const terminalEndRef = useRef<HTMLDivElement>(null);

  // Template queries
  const templates = [
    "Analyze employment trends in the technology sector from 2020-2024 and compare with inflation.",
    "Evaluate resident population median age trends and demographic dependency ratios (2020-2024).",
    "Investigate tourism sector recovery post-pandemic and check wage growth indices compared to CPI."
  ];

  const fetchHealthAndHistory = async () => {
    setApiHealth('connecting');
    try {
      // 1. Fetch Health Check
      const healthRes = await fetch(`${backendUrl}/api/health`);
      if (healthRes.ok) {
        const data = await healthRes.json();
        setApiHealth('healthy');
        setLlmProvider(data.llm_provider || (data.environment === 'production' ? 'fallback' : 'mock'));
      } else {
        setApiHealth('unhealthy');
      }

      // 2. Fetch history
      const historyRes = await fetch(`${backendUrl}/api/requests`);
      if (historyRes.ok) {
        const data = await historyRes.json();
        setHistory(data);
      }
    } catch (e) {
      setApiHealth('unhealthy');
      console.error(e);
    }
  };

  // Check backend health and load historical queries
  useEffect(() => {
    fetchHealthAndHistory();
  }, [backendUrl]);

  // Scroll to bottom of terminal whenever agent steps update
  useEffect(() => {
    terminalEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [agentSteps]);

  const handleQuerySubmit = (event?: React.FormEvent, selectedQuery?: string) => {
    if (event) event.preventDefault();
    const finalQuery = selectedQuery || query;
    if (!finalQuery.trim() || isAnalyzing) return;

    // Reset layouts
    setQuery(finalQuery);
    setIsAnalyzing(true);
    setAgentSteps([]);
    setReport(null);
    setChartSpec(null);
    setActiveTab('report');
    setCurrentStatus('Establishing real-time orchestration WebSocket...');

    // Initialize WebSockets
    const socket = new WebSocket(wsUrl);

    socket.onopen = () => {
      setCurrentStatus('WebSocket connected. Registering pipeline plan...');
      socket.send(JSON.stringify({ query: finalQuery }));
    };

    socket.onmessage = (event) => {
      const data: AgentStep = JSON.parse(event.data);
      console.log(data);

      // Update intermediate status text
      if (data.type === 'status' && data.content) {
        setCurrentStatus(data.content);
      }

      // Capture final report and chart specs
      if (data.type === 'completed') {
        setIsAnalyzing(false);
        setReport(data.report || null);
        setChartSpec(data.chart_spec || null);
        setCurrentStatus('Analysis completed. Visualizing report.');
        fetchHealthAndHistory(); // Reload history side-drawer
        socket.close();
      } else if (data.type === 'error') {
        setIsAnalyzing(false);
        setCurrentStatus(`Error: ${data.content}`);
        setAgentSteps(prev => [...prev, { agent: 'System', type: 'error', content: data.content }]);
        socket.close();
      } else {
        // Standard intermediate ReAct step (thought, action, observation, result)
        setAgentSteps(prev => [...prev, data]);
      }
    };

    socket.onerror = (err) => {
      console.error(err);
      setIsAnalyzing(false);
      setCurrentStatus('Connection failed. Verify if python backend is running on port 8000.');
      setApiHealth('unhealthy');
    };

    socket.onclose = () => {
      console.log("WebSocket Closed");
    };
  };

  // Load an earlier research query from database history
  const loadHistoricalRequest = async (id: string) => {
    setSelectedHistoryId(id);
    setShowHistory(false);
    setCurrentStatus(`Loading previous analysis request [${id}]...`);

    try {
      const res = await fetch(`${backendUrl}/api/requests/${id}`);
      if (res.ok) {
        const data = await res.json();
        setQuery(data.query);
        setReport(data.result?.report || null);
        setChartSpec(data.result?.chart_spec || null);
        setActiveTab('report');

        // Reconstruct console step log sequence
        if (data.logs) {
          setAgentSteps(data.logs);
          setCurrentStatus('Loaded archived policy brief.');
        }
      }
    } catch (e) {
      setCurrentStatus('Failed to retrieve request details.');
      console.error(e);
    }
  };

  // Simple Markdown Parsing to raw HTML to present beautiful structured reports
  const parseMarkdownToHtml = (md: string) => {
    if (!md) return '';
    let html = md;

    // Headings
    html = html.replace(/^# (.*?)$/gm, '<h1 class="text-4xl font-bold text-[#f1f5f9] mt-6 mb-4 border-b border-slate-700 pb-2.5">$1</h1>');
    html = html.replace(/^## (.*?)$/gm, '<h2 class="text-3xl font-semibold text-indigo-400 mt-6 mb-3">$1</h2>');
    html = html.replace(/^### (.*?)$/gm, '<h3 class="text-2xl font-medium text-indigo-300 mt-5 mb-2">$1</h3>');

    // Bold text
    html = html.replace(/\*\*(.*?)\*\*/g, '<strong class="font-semibold text-white">$1</strong>');

    // Tables parsing
    const tableRegex = /\|([\s\S]*?)\|\r?\n\|[ :-|\t]*?\|\r?\n((?:\|.*?\r?\n)+)/g;
    html = html.replace(tableRegex, (_match, header, rows) => {
      const headers = header.split('|').map((h: string) => h.trim()).filter((h: string) => h);
      const headerHtml = `<thead><tr class="bg-slate-800 text-slate-200 border-b border-slate-700">${headers.map((h: string) => `<th class="p-3 text-left font-medium text-sm uppercase tracking-wider">${h}</th>`).join('')}</tr></thead>`;

      const parsedRows = rows.split('\n').filter((r: string) => r.trim()).map((row: string) => {
        const cols = row.split('|').map((c: string) => c.trim()).filter((c: string) => c);
        // Avoid separator row
        if (cols[0]?.includes('---') || cols[0]?.includes(':---')) return '';
        return `<tr class="border-b border-slate-800 hover:bg-slate-900/30">${cols.map((c: string) => `<td class="p-3 text-base text-slate-300">${c}</td>`).join('')}</tr>`;
      }).filter((r: string) => r).join('');

      return `<div class="overflow-x-auto my-5 rounded-lg border border-slate-800"><table class="min-w-full divide-y divide-slate-800 text-left bg-slate-900/10">${headerHtml}<tbody>${parsedRows}</tbody></table></div>`;
    });

    // Unordered Lists
    html = html.replace(/^\* (.*?)$/gm, '<li class="ml-5 list-disc text-slate-300 my-1 text-base">$1</li>');
    html = html.replace(/^- (.*?)$/gm, '<li class="ml-5 list-disc text-slate-300 my-1 text-base">$1</li>');

    // Paragraphs
    html = html.replace(/^(?!<h|<table|<thead|<tr|<td|<th|<li|<div)(.*?)$/gm, '<p class="text-slate-300 my-3 leading-relaxed text-base">$1</p>');

    return html;
  };

  // Export report to Markdown File
  const handleExportMarkdown = () => {
    if (!report) return;
    const element = document.createElement("a");
    const file = new Blob([report], { type: 'text/markdown' });
    element.href = URL.createObjectURL(file);
    element.download = `Singapore_Policy_Brief_${selectedHistoryId || 'New'}.md`;
    document.body.appendChild(element);
    element.click();
    document.body.removeChild(element);
  };

  return (
    <div className="flex h-screen bg-[#070b13] font-sans">

      {/* Sidebar - Quick Brand and Server Stats */}
      <div className="w-64 border-r border-slate-900 bg-[#090e17] flex flex-col justify-between">
        <div>
          {/* Logo Header */}
          <div className="p-5 border-b border-slate-900 flex items-center gap-3">
            <div className="bg-indigo-600/10 p-2.5 rounded-lg border border-indigo-500/30">
              <Shield className="h-5.5 w-5.5 text-indigo-400" />
            </div>
            <div>
              <h1 className="font-bold text-base tracking-tight text-white">GovTech Agentic</h1>
              <p className="text-xs text-slate-400 font-medium">Policy Analytics Engine</p>
            </div>
          </div>

          {/* Configuration and Environment Stats */}
          <div className="p-4 space-y-4">
            <div className="bg-slate-900/50 p-3.5 rounded-lg border border-slate-800/40">
              <div className="flex items-center justify-between mb-2.5">
                <span className="text-xs text-slate-300 font-semibold tracking-wider uppercase">Backend Status</span>
                <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-semibold border ${apiHealth === 'healthy'
                  ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20'
                  : apiHealth === 'connecting'
                    ? 'bg-amber-500/10 text-amber-400 border-amber-500/20 animate-pulse'
                    : 'bg-rose-500/10 text-rose-400 border-rose-500/20'
                  }`}>
                  {apiHealth === 'healthy' ? 'Online' : apiHealth === 'connecting' ? 'Connecting' : 'Offline'}
                </span>
              </div>

              <div className="space-y-3.5 mt-3">
                <div>
                  <label htmlFor="api-rest-server" className="text-xs text-slate-400 block mb-1">API REST Server</label>
                  <input
                    id="api-rest-server"
                    type="text"
                    value={backendUrl}
                    onChange={(e) => setBackendUrl(e.target.value)}
                    className="w-full text-xs bg-slate-950 text-slate-200 border border-slate-800 rounded px-2.5 py-1.5 focus:outline-none focus:border-slate-700 font-mono"
                  />
                </div>
                <div>
                  <label htmlFor="websocket-server" className="text-xs text-slate-400 block mb-1">WebSocket Server</label>
                  <input
                    id="websocket-server"
                    type="text"
                    value={wsUrl}
                    onChange={(e) => setWsUrl(e.target.value)}
                    className="w-full text-xs bg-slate-950 text-slate-200 border border-slate-800 rounded px-2.5 py-1.5 focus:outline-none focus:border-slate-700 font-mono"
                  />
                </div>
              </div>
            </div>

            {/* Orchestrator Insights */}
            <div className="bg-[#0f172a]/30 p-3.5 rounded-lg border border-indigo-500/5">
              <span className="text-xs text-slate-300 font-semibold tracking-wider uppercase block mb-1.5">Active Architecture</span>
              <div className="space-y-2 mt-2">
                <div className="flex items-center justify-between text-xs">
                  <span className="text-slate-400">Framework</span>
                  <span className="text-indigo-400 font-medium font-mono">Custom ReAct</span>
                </div>
                <div className="flex items-center justify-between text-xs">
                  <span className="text-slate-400">LLM Mode</span>
                  <span className="text-indigo-400 font-medium font-mono capitalize">{llmProvider}</span>
                </div>
                <div className="flex items-center justify-between text-xs">
                  <span className="text-slate-400">Cooperating Agents</span>
                  <span className="text-indigo-400 font-semibold">3 Nodes</span>
                </div>
              </div>
            </div>

            {/* Quick Action Drawer Toggle */}
            <button
              onClick={() => { setShowHistory(true); fetchHealthAndHistory(); }}
              className="w-full bg-slate-900 hover:bg-slate-800 text-slate-200 border border-slate-800 hover:border-slate-700 rounded-lg p-2.5 flex items-center justify-center gap-2 text-sm transition duration-200 font-medium"
            >
              <History className="h-4.5 w-4.5" />
              View Query History ({history.length})
            </button>
          </div>
        </div>

        {/* Brand Footer */}
        <div className="p-4 border-t border-slate-900 text-center">
          <p className="text-xs text-slate-500">&copy; 2026 GovTech Singapore</p>
        </div>
      </div>

      {/* Main Core Dashboard Layout */}
      <div className="flex-1 flex flex-col overflow-hidden">

        {/* Top Header stats */}
        <div className="h-14 border-b border-slate-900 bg-[#090e17] px-6 flex items-center justify-between">
          <div className="flex items-center gap-2 text-sm">
            <span className="text-slate-400 font-medium">Active Task State:</span>
            <span className="bg-slate-950 text-indigo-400 border border-slate-850 px-2.5 py-1 rounded flex items-center gap-2 font-mono text-xs">
              <Activity className="h-4 w-4 animate-pulse text-indigo-400" />
              {currentStatus}
            </span>
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={fetchHealthAndHistory}
              className="p-1.5 hover:bg-slate-900 rounded border border-slate-800 hover:border-slate-700 text-slate-400 hover:text-slate-200 transition"
              title="Refresh Health Stats"
            >
              <RefreshCw className="h-4 w-4" />
            </button>
          </div>
        </div>

        {/* Dashboard Split Sections */}
        <div className="flex-1 flex overflow-hidden">

          {/* Left Block: Query Inputs & Real-time Console */}
          <div className="w-1/2 flex flex-col p-6 gap-6 border-r border-slate-900 overflow-y-auto">

            {/* Natural Language Query Panel */}
            <div className="glass-panel rounded-xl p-5 shadow-lg border border-slate-800/80">
              <div className="flex items-center gap-2 mb-3.5">
                <Sparkles className="h-4.5 w-4.5 text-indigo-400" />
                <h2 className="text-base font-semibold text-white">Policy Research Query</h2>
              </div>

              <form onSubmit={handleQuerySubmit} className="relative">
                <textarea
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  placeholder="e.g. Analyze employment trends in the tech sector from 2020 to 2024 and compare with domestic CPI inflation."
                  className="w-full h-28 bg-slate-950 text-slate-200 border border-slate-800 rounded-lg p-3.5 pr-12 focus:outline-none focus:ring-1 focus:ring-indigo-500 text-sm font-sans resize-none leading-relaxed"
                  disabled={isAnalyzing}
                />
                <button
                  type="submit"
                  className={`absolute right-3.5 bottom-3.5 p-2 rounded-md transition duration-200 ${isAnalyzing
                    ? 'bg-slate-900 text-slate-600 cursor-not-allowed'
                    : 'bg-indigo-600 hover:bg-indigo-500 text-white'
                    }`}
                  disabled={isAnalyzing}
                >
                  <Send className="h-4.5 w-4.5" />
                </button>
              </form>

              {/* Template Prompts */}
              <div className="mt-5">
                <span className="text-xs text-slate-400 font-semibold tracking-wider uppercase block mb-2.5">Example Analytics Prompts</span>
                <div className="flex flex-col gap-2">
                  {templates.map((t, idx) => (
                    <button
                      key={idx}
                      onClick={() => handleQuerySubmit(undefined, t)}
                      className="text-left text-xs bg-slate-900/60 hover:bg-slate-800/60 border border-slate-900 hover:border-slate-800 text-slate-300 hover:text-slate-100 rounded p-2.5 transition duration-200 truncate flex items-center gap-2 font-medium"
                      disabled={isAnalyzing}
                    >
                      <ChevronRight className="h-4 w-4 text-indigo-500/70" />
                      {t}
                    </button>
                  ))}
                </div>
              </div>
            </div>

            {/* Agent monologue real-time WebSocket console */}
            <div className="flex-1 glass-panel rounded-xl flex flex-col border border-slate-800/80 overflow-hidden shadow-lg">
              {/* Terminal Header */}
              <div className="bg-slate-950/80 px-4 py-3 border-b border-slate-900 flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Terminal className="h-4.5 w-4.5 text-indigo-400" />
                  <span className="text-sm font-semibold text-white tracking-wide font-mono">Agent Collaborative Log</span>
                </div>
                <div className="flex items-center gap-1.5">
                  <div className={`h-2.5 w-2.5 rounded-full ${isAnalyzing ? 'bg-indigo-500 animate-pulse' : 'bg-slate-700'}`} />
                  <span className="text-[10px] text-slate-400 font-mono font-medium tracking-wider uppercase">
                    {isAnalyzing ? 'Running ReAct Loop' : 'Idle'}
                  </span>
                </div>
              </div>

              {/* Terminal Body */}
              <div className="flex-1 p-4 overflow-y-auto space-y-4 font-mono text-sm bg-slate-950/50">
                {agentSteps.length === 0 ? (
                  <div className="h-full flex flex-col items-center justify-center text-center p-8 opacity-40">
                    <Database className="h-10 w-10 text-slate-600 mb-2.5" />
                    <p className="text-xs text-slate-500 font-medium">Submit a policy query to view the agentic thought workflow steps.</p>
                  </div>
                ) : (
                  agentSteps.map((step, idx) => {
                    // Decide badge and styling based on agent
                    let badgeColor = 'bg-slate-800 text-slate-400 border-slate-700';
                    if (step.agent === 'Coordinator') badgeColor = 'bg-rose-500/10 text-rose-400 border-rose-500/20';
                    else if (step.agent === 'Extractor') badgeColor = 'bg-blue-500/10 text-blue-400 border-blue-500/20';
                    else if (step.agent === 'Analyst') badgeColor = 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20';
                    else if (step.agent === 'System') badgeColor = 'bg-purple-500/10 text-purple-400 border-purple-500/20';

                    // Format step types nicely
                    return (
                      <div key={idx} className="border border-slate-900/60 bg-slate-950/40 p-3 rounded-lg space-y-1.5 terminal-glow">
                        <div className="flex items-center gap-2">
                          <span className={`px-2 py-0.5 text-[10px] font-bold tracking-wider uppercase rounded border ${badgeColor}`}>
                            [{step.agent}]
                          </span>
                          <span className="text-xs text-slate-400 font-semibold tracking-wider uppercase">
                            {step.type}
                          </span>
                        </div>

                        {/* Custom content display based on step type */}
                        <div className="pl-2 border-l-2 border-slate-800 text-slate-200 font-sans leading-relaxed text-sm">
                          {step.type === 'thought' ? (
                            <p className="italic text-slate-400 leading-relaxed">"{step.content}"</p>
                          ) : step.type === 'action' ? (
                            <div className="bg-slate-950 p-2.5 rounded border border-slate-800 text-indigo-400 font-mono text-xs whitespace-pre-wrap leading-relaxed">
                              {step.content}
                            </div>
                          ) : step.type === 'observation' ? (
                            <div className="bg-slate-950/60 p-2.5 rounded text-slate-400 font-mono text-xs max-h-48 overflow-y-auto whitespace-pre-wrap leading-relaxed">
                              {step.content}
                            </div>
                          ) : (
                            <p className="leading-relaxed">{step.content}</p>
                          )}
                        </div>
                      </div>
                    );
                  })
                )}
                <div ref={terminalEndRef} />
              </div>
            </div>
          </div>

          {/* Right Block: Charts and Formatted Markdown Reports */}
          <div className="w-1/2 flex flex-col p-6 overflow-y-auto bg-[#070b13]/60">

            {/* Header Tabs */}
            <div className="flex items-center justify-between mb-4 border-b border-slate-900 pb-2">
              <div className="flex items-center gap-1.5">
                <button
                  onClick={() => setActiveTab('report')}
                  className={`px-4 py-2 rounded-lg text-sm font-semibold flex items-center gap-2 transition ${activeTab === 'report'
                    ? 'bg-indigo-600 text-white shadow-md'
                    : 'hover:bg-slate-900 text-slate-400 hover:text-slate-200'
                    }`}
                >
                  <FileText className="h-4 w-4" />
                  Policy Brief
                </button>
                <button
                  onClick={() => setActiveTab('charts')}
                  className={`px-4 py-2 rounded-lg text-sm font-semibold flex items-center gap-2 transition ${activeTab === 'charts'
                    ? 'bg-indigo-600 text-white shadow-md'
                    : 'hover:bg-slate-900 text-slate-400 hover:text-slate-200'
                    }`}
                >
                  <BarChart3 className="h-4 w-4" />
                  Interactive Charts
                </button>
              </div>

              {/* Action Tools */}
              {report && (
                <button
                  onClick={handleExportMarkdown}
                  className="bg-slate-900 hover:bg-slate-800 text-slate-200 border border-slate-800 hover:border-slate-700 px-3.5 py-2 rounded-lg text-sm flex items-center gap-2 transition duration-200 font-medium"
                >
                  <Download className="h-4 w-4" />
                  Download Brief (.md)
                </button>
              )}
            </div>

            {/* Display Body */}
            <div className="flex-1 flex flex-col">
              {isAnalyzing && !report ? (
                <div className="flex-1 flex flex-col items-center justify-center text-center p-8">
                  <div className="relative mb-4">
                    <div className="h-12 w-12 rounded-full border-t-2 border-b-2 border-indigo-500 animate-spin" />
                    <Shield className="absolute inset-0 m-auto h-5 w-5 text-indigo-400" />
                  </div>
                  <h3 className="text-base font-semibold text-white">Multi-Agent Engine Running</h3>
                  <p className="text-sm text-slate-400 mt-1.5 max-w-sm leading-relaxed">Data Coordinator is planning work and delegating tasks to Extractor and Analyst agents...</p>
                </div>
              ) : !report ? (
                <div className="flex-1 flex flex-col items-center justify-center text-center p-8 opacity-40">
                  <FileText className="h-12 w-12 text-slate-600 mb-2.5" />
                  <p className="text-sm text-slate-400 font-medium">Waiting for analytical task to complete...</p>
                </div>
              ) : activeTab === 'report' ? (
                // Markdown Reader Panel
                <div className="glass-panel rounded-xl p-6 shadow-lg border border-slate-800/80 prose prose-invert max-w-none">
                  <div
                    dangerouslySetInnerHTML={{ __html: parseMarkdownToHtml(report) }}
                    className="space-y-4"
                  />
                </div>
              ) : (
                // Recharts Visual Dashboard
                <div className="glass-panel rounded-xl p-5 shadow-lg border border-slate-800/80 space-y-4">
                  <div>
                    <h3 className="text-base font-semibold text-white">{chartSpec?.title || "Analytical Metrics Visualizer"}</h3>
                    <p className="text-xs text-slate-400 mt-1">Dynamically configured by the Analytics Agent.</p>
                  </div>

                  {chartSpec?.data && chartSpec.data.length > 0 ? (
                    <div className="h-72 w-full mt-4">
                      <ResponsiveContainer width="100%" height="100%">
                        <ComposedChart data={chartSpec.data} margin={{ top: 10, right: 10, left: -10, bottom: 0 }}>
                          <defs>
                            <linearGradient id="colorSalary" x1="0" y1="0" x2="0" y2="1">
                              <stop offset="5%" stopColor="#6366f1" stopOpacity={0.8} />
                              <stop offset="95%" stopColor="#6366f1" stopOpacity={0.1} />
                            </linearGradient>
                          </defs>
                          <CartesianGrid stroke="#1e293b" strokeDasharray="3 3" />
                          <XAxis
                            dataKey={chartSpec.xAxis || "year"}
                            stroke="#64748b"
                            fontSize={12}
                            tickLine={false}
                          />
                          <YAxis
                            yAxisId="left"
                            stroke="#6366f1"
                            fontSize={12}
                            tickLine={false}
                            axisLine={false}
                          />
                          <YAxis
                            yAxisId="right"
                            orientation="right"
                            stroke="#f43f5e"
                            fontSize={12}
                            tickLine={false}
                            axisLine={false}
                          />
                          <Tooltip
                            contentStyle={{ backgroundColor: '#0f172a', border: '1px solid #1e293b', borderRadius: '8px' }}
                            labelStyle={{ color: '#94a3b8', fontSize: '12px', fontWeight: 'bold' }}
                            itemStyle={{ fontSize: '13px' }}
                          />
                          <Legend wrapperStyle={{ fontSize: '12px', paddingTop: '10px' }} />

                          {/* Dynamically draw series based on specifications */}
                          {chartSpec.series?.map((s: any, idx: number) => {
                            if (s.type === 'bar') {
                              return (
                                <Bar
                                  key={idx}
                                  yAxisId={s.yAxisId || "left"}
                                  name={s.name}
                                  dataKey={s.dataKey}
                                  fill="url(#colorSalary)"
                                  stroke="#6366f1"
                                  strokeWidth={1}
                                  radius={[4, 4, 0, 0]}
                                  barSize={30}
                                />
                              );
                            }
                            return (
                              <Line
                                key={idx}
                                yAxisId={s.yAxisId || "right"}
                                type="monotone"
                                name={s.name}
                                dataKey={s.dataKey}
                                stroke={s.color || "#f43f5e"}
                                strokeWidth={2}
                                dot={{ r: 3, fill: '#0f172a', stroke: s.color || "#f43f5e", strokeWidth: 2 }}
                              />
                            );
                          })}
                        </ComposedChart>
                      </ResponsiveContainer>
                    </div>
                  ) : (
                    <div className="h-72 flex flex-col items-center justify-center text-center border border-dashed border-slate-800 rounded-lg">
                      <BarChart3 className="h-8 w-8 text-slate-600 mb-1" />
                      <p className="text-xs text-slate-500">No chart coordinates extracted for this dataset.</p>
                    </div>
                  )}

                  {/* Dynamic Metrics Cards */}
                  <div className="grid grid-cols-3 gap-4 mt-5">
                    {chartSpec?.metrics && chartSpec.metrics.length > 0 ? (
                      chartSpec.metrics.slice(0, 3).map((m: any, idx: number) => (
                        <div key={idx} className="bg-[#1e293b]/20 border border-slate-800 p-3.5 rounded-lg text-center">
                          <span className="text-[11px] text-slate-400 font-semibold block uppercase truncate" title={m.label}>{m.label}</span>
                          <span className="text-lg font-bold text-indigo-400 block mt-1.5 truncate" title={m.value}>{m.value}</span>
                          <span className="text-[10px] text-slate-500 block mt-1 truncate" title={m.description}>{m.description}</span>
                        </div>
                      ))
                    ) : (
                      <>
                        <div className="bg-[#1e293b]/20 border border-slate-800 p-3.5 rounded-lg text-center">
                          <span className="text-[11px] text-slate-400 font-semibold block uppercase">Tech Wage Growth</span>
                          <span className="text-lg font-bold text-indigo-400 block mt-1.5">+26.15%</span>
                          <span className="text-[10px] text-slate-500 block mt-1">2020-2024 (CAGR: 5.9%)</span>
                        </div>
                        <div className="bg-[#1e293b]/20 border border-slate-800 p-3.5 rounded-lg text-center">
                          <span className="text-[11px] text-slate-400 font-semibold block uppercase">Wage-CPI Correlation</span>
                          <span className="text-lg font-bold text-indigo-400 block mt-1.5">0.8934</span>
                          <span className="text-[10px] text-slate-500 block mt-1">Strong Positive Shift</span>
                        </div>
                        <div className="bg-[#1e293b]/20 border border-slate-800 p-3.5 rounded-lg text-center">
                          <span className="text-[11px] text-slate-400 font-semibold block uppercase">Post-Consolidation</span>
                          <span className="text-lg font-bold text-indigo-400 block mt-1.5">Rebounding</span>
                          <span className="text-[10px] text-slate-500 block mt-1">+6,800 headcounts (2024)</span>
                        </div>
                      </>
                    )}
                  </div>
                </div>
              )}
            </div>
          </div>

        </div>

      </div>

      {/* Historical Queries Sliding Drawer */}
      {showHistory && (
        <div className="fixed inset-0 z-50 flex justify-end bg-black/60 backdrop-blur-sm transition duration-300">
          <div className="w-96 bg-[#090e17] border-l border-slate-900 h-full flex flex-col shadow-2xl p-6 relative">
            <button
              onClick={() => setShowHistory(false)}
              className="absolute top-4 left-4 text-slate-300 hover:text-slate-100 text-sm font-semibold hover:bg-slate-950 p-1.5 px-3 rounded border border-slate-800"
            >
              Close Drawer
            </button>

            <div className="mt-10 flex-1 flex flex-col overflow-hidden">
              <div className="flex items-center gap-2 mb-4 border-b border-slate-900 pb-2.5">
                <History className="h-4.5 w-4.5 text-indigo-400" />
                <h3 className="text-base font-bold text-white">Archived Policy Analyses</h3>
              </div>

              <div className="flex-1 overflow-y-auto space-y-2.5 pr-1">
                {history.length === 0 ? (
                  <p className="text-sm text-slate-500 text-center py-10">No archived queries found in database.</p>
                ) : (
                  history.map((req) => (
                    <button
                      key={req.id}
                      onClick={() => loadHistoricalRequest(req.id)}
                      className={`w-full text-left bg-slate-950/40 hover:bg-slate-900 border text-sm p-3.5 rounded-lg transition duration-200 flex flex-col gap-2 ${selectedHistoryId === req.id
                        ? 'border-indigo-500/50 bg-[#1e293b]/10'
                        : 'border-slate-800/60 hover:border-slate-800'
                        }`}
                    >
                      <p className="font-semibold text-slate-200 truncate">{req.query}</p>
                      <div className="flex items-center justify-between text-[11px] text-slate-500">
                        <span>{new Date(req.created_at).toLocaleDateString()}</span>
                        <span className={`px-1.5 py-0.5 rounded font-mono uppercase ${req.status === 'completed'
                          ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/15'
                          : 'bg-rose-500/10 text-rose-400 border border-rose-500/15'
                          }`}>
                          {req.status}
                        </span>
                      </div>
                    </button>
                  ))
                )}
              </div>
            </div>
          </div>
        </div>
      )}

    </div>
  );
}
