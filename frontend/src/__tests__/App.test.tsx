import React from 'react';
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import App from '../App';

// Mock Recharts to avoid rendering complexities and canvas errors in JSDOM
vi.mock('recharts', () => ({
  ResponsiveContainer: ({ children }: { children: React.ReactNode }) => <div data-testid="responsive-container">{children}</div>,
  ComposedChart: ({ children, data }: { children: React.ReactNode; data: any }) => (
    <div data-testid="composed-chart" data-chart-data={JSON.stringify(data)}>
      {children}
    </div>
  ),
  Line: () => <div data-testid="chart-line" />,
  Bar: () => <div data-testid="chart-bar" />,
  XAxis: () => null,
  YAxis: () => null,
  CartesianGrid: () => null,
  Tooltip: () => null,
  Legend: () => null,
}));

// Mock WebSocket class
class MockWebSocket {
  url: string;
  onopen: (() => void) | null = null;
  onmessage: ((event: { data: string }) => void) | null = null;
  onerror: ((err: any) => void) | null = null;
  onclose: (() => void) | null = null;
  static lastInstance: MockWebSocket | null = null;

  constructor(url: string) {
    this.url = url;
    MockWebSocket.lastInstance = this;
    setTimeout(() => {
      if (this.onopen) this.onopen();
    }, 10);
  }

  send = vi.fn();
  close = vi.fn();
}

globalThis.WebSocket = MockWebSocket as any;

describe('App Component', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    MockWebSocket.lastInstance = null;
    
    // Mock global fetch
    globalThis.fetch = vi.fn().mockImplementation((url: string) => {
      if (url.endsWith('/api/health')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({ llm_provider: 'mock', environment: 'development' }),
        });
      }
      if (url.endsWith('/api/requests')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve([
            { id: '1', query: 'Archived test query 1', status: 'completed', created_at: '2026-05-29T00:00:00Z' }
          ]),
        });
      }
      if (url.includes('/api/requests/1')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({
            id: '1',
            query: 'Archived test query 1',
            result: {
              report: '# Singapore Tech Sector\n* Growth was strong.',
              chart_spec: {
                title: 'Tech Salary Growth',
                data: [{ year: '2020', salary: 5000 }],
                xAxis: 'year',
                series: [{ type: 'bar', name: 'Salary', dataKey: 'salary' }],
                metrics: [{ label: 'Wage Growth', value: '10%' }]
              }
            },
            logs: [
              { agent: 'Coordinator', type: 'thought', content: 'Evaluating query...' }
            ],
            status: 'completed',
            created_at: '2026-05-29T00:00:00Z'
          }),
        });
      }
      return Promise.resolve({ ok: false });
    }) as any;
  });

  it('renders initial dashboard structure correctly', async () => {
    render(<App />);
    
    expect(screen.getByText('GovTech Agentic')).toBeInTheDocument();
    expect(screen.getByText('Policy Analytics Engine')).toBeInTheDocument();
    expect(screen.getByPlaceholderText(/Analyze employment trends/i)).toBeInTheDocument();
    expect(screen.getByText('Example Analytics Prompts')).toBeInTheDocument();
    
    await waitFor(() => {
      expect(screen.getByText('Online')).toBeInTheDocument();
    });
  });

  it('loads and displays historical queries from side drawer', async () => {
    render(<App />);
    
    // Toggle historical drawer
    const drawerBtn = screen.getByRole('button', { name: /View Query History/i });
    fireEvent.click(drawerBtn);
    
    await waitFor(() => {
      expect(screen.getByText('Archived Policy Analyses')).toBeInTheDocument();
      expect(screen.getByText('Archived test query 1')).toBeInTheDocument();
    });
  });

  it('selects and loads a historical query detail', async () => {
    render(<App />);
    
    // Toggle drawer
    fireEvent.click(screen.getByRole('button', { name: /View Query History/i }));
    
    await waitFor(() => {
      expect(screen.getByText('Archived test query 1')).toBeInTheDocument();
    });
    
    // Click the item
    fireEvent.click(screen.getByText('Archived test query 1'));
    
    await waitFor(() => {
      expect(screen.getByText('Singapore Tech Sector')).toBeInTheDocument();
      expect(screen.getByText('Growth was strong.')).toBeInTheDocument();
    });

    // Check report markdown parser output HTML
    const boldText = screen.getByText('Singapore Tech Sector');
    expect(boldText.tagName).toBe('H1');

    // Switch to Charts tab and inspect charted elements
    fireEvent.click(screen.getByRole('button', { name: /Interactive Charts/i }));
    expect(screen.getByText('Tech Salary Growth')).toBeInTheDocument();
    expect(screen.getByText('Wage Growth')).toBeInTheDocument();
  });

  it('handles query submission via form and establishes WebSocket connection', async () => {
    render(<App />);
    
    const textarea = screen.getByPlaceholderText(/Analyze employment trends/i);
    fireEvent.change(textarea, { target: { value: 'Test query submission' } });
    
    const submitBtn = screen.getByRole('button', { name: '' }); // Send button has no name text, but contains icon
    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(MockWebSocket.lastInstance).not.toBeNull();
      expect(MockWebSocket.lastInstance?.url).toBe('ws://localhost:8000/api/ws/analysis');
    });

    // Mock incoming WebSocket message sequence
    act(() => {
      // Step 1: thought
      MockWebSocket.lastInstance?.onmessage?.({
        data: JSON.stringify({
          agent: 'Coordinator',
          type: 'thought',
          content: 'Deciding execution plan...'
        })
      });
    });

    await waitFor(() => {
      expect(screen.getByText(/Deciding execution plan/i)).toBeInTheDocument();
    });

    act(() => {
      // Step 2: completion
      MockWebSocket.lastInstance?.onmessage?.({
        data: JSON.stringify({
          agent: 'Coordinator',
          type: 'completed',
          report: '# WS Brief\n- WS Success.',
          chart_spec: {
            title: 'WS Chart',
            data: [],
            metrics: []
          }
        })
      });
    });

    await waitFor(() => {
      expect(screen.getByText('WS Brief')).toBeInTheDocument();
    });
  });

  it('allows clicking sample prompt template triggers', async () => {
    render(<App />);
    
    const templateBtn = screen.getByText(/resident population median age trends/i);
    fireEvent.click(templateBtn);
    
    await waitFor(() => {
      expect(MockWebSocket.lastInstance).not.toBeNull();
    });
  });

  it('handles markdown exports safely', async () => {
    // Setup file download mocks
    const clickSpy = vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => {});
    
    render(<App />);
    
    // Load historical request to populate the report
    fireEvent.click(screen.getByRole('button', { name: /View Query History/i }));
    await waitFor(() => {
      expect(screen.getByText('Archived test query 1')).toBeInTheDocument();
    });
    fireEvent.click(screen.getByText('Archived test query 1'));
    
    await waitFor(() => {
      expect(screen.getByRole('button', { name: /Download Brief/i })).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole('button', { name: /Download Brief/i }));
    expect(clickSpy).toHaveBeenCalled();
  });

  it('allows changing settings and handles WebSocket error / connection failure', async () => {
    render(<App />);

    // Mock WebSocket to fail on connection
    const originalWebSocket = globalThis.WebSocket;
    class MockErrorWebSocket {
      url: string;
      onopen: (() => void) | null = null;
      onmessage: (() => void) | null = null;
      onerror: ((err: any) => void) | null = null;
      onclose: (() => void) | null = null;
      static lastInstance: MockErrorWebSocket | null = null;

      constructor(url: string) {
        this.url = url;
        MockErrorWebSocket.lastInstance = this;
        setTimeout(() => {
          if (this.onerror) this.onerror(new Error('WS Connection failed'));
        }, 10);
      }
      send = vi.fn();
      close = vi.fn();
    }
    globalThis.WebSocket = MockErrorWebSocket as any;

    const textarea = screen.getByPlaceholderText(/Analyze employment trends/i);
    fireEvent.change(textarea, { target: { value: 'Triggering connection failure' } });

    const submitBtn = screen.getByRole('button', { name: '' });
    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(screen.getByText(/Connection failed. Verify if python backend/i)).toBeInTheDocument();
    });

    globalThis.WebSocket = originalWebSocket;
  });

  it('handles backend url input change and closes history drawer', async () => {
    render(<App />);

    // Change Backend URL input
    const backendInput = screen.getByLabelText(/API REST Server/i);
    fireEvent.change(backendInput, { target: { value: 'http://localhost:9999' } });
    expect(backendInput).toHaveValue('http://localhost:9999');

    // Change WebSocket URL input
    const wsInput = screen.getByLabelText(/WebSocket Server/i);
    fireEvent.change(wsInput, { target: { value: 'ws://localhost:9999/ws' } });
    expect(wsInput).toHaveValue('ws://localhost:9999/ws');

    // Open drawer
    fireEvent.click(screen.getByRole('button', { name: /View Query History/i }));
    await waitFor(() => {
      expect(screen.getByText('Archived Policy Analyses')).toBeInTheDocument();
    });

    // Close drawer
    const closeBtn = screen.getByText('Close Drawer');
    fireEvent.click(closeBtn);
    expect(screen.queryByText('Archived Policy Analyses')).not.toBeInTheDocument();
  });
});

