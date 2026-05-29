import '@testing-library/jest-dom';

// Mock ResizeObserver for Recharts ResponsiveContainer
class ResizeObserverMock {
  observe() {}
  unobserve() {}
  disconnect() {}
}
window.ResizeObserver = ResizeObserverMock;

// Mock Element.scrollIntoView since jsdom doesn't implement it
Element.prototype.scrollIntoView = function() {};

// Mock URL.createObjectURL and revokeObjectURL for download functionality
window.URL.createObjectURL = function() {
  return 'blob:mock-url';
};
window.URL.revokeObjectURL = function() {};
