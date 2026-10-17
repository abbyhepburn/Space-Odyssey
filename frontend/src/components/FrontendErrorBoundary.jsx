import React from 'react';

// Display unexpected React rendering failures instead of leaving a black/blank game window.
export default class FrontendErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { error: null };
  }

  static getDerivedStateFromError(error) {
    return { error };
  }

  componentDidCatch(error, details) {
    console.error('Space Odyssey frontend error:', error, details);
  }

  render() {
    if (!this.state.error) return this.props.children;
    return (
      <main style={{ minHeight: '100vh', padding: 'clamp(24px,5vw,72px)',
        background: '#081421', color: '#f8ede0', fontFamily: 'system-ui,sans-serif' }}>
        <p style={{ color: '#e0af70', letterSpacing: '0.2em' }}>SPACE ODYSSEY — DIAGNOSTICS</p>
        <h1 style={{ margin: '20px 0', fontSize: 'clamp(28px,5vw,46px)' }}>The game hit a frontend error</h1>
        <p>Copy the error below and send it here. Your save files and planet models are unchanged.</p>
        <pre style={{ maxWidth: 900, overflowX: 'auto', whiteSpace: 'pre-wrap',
          margin: '24px 0', padding: '20px', border: '1px solid #a97b4c',
          borderRadius: 12, background: '#172536' }}>
          {String(this.state.error?.stack || this.state.error?.message || this.state.error)}
        </pre>
        <button onClick={() => window.location.reload()} style={{ padding: '12px 24px',
          background: '#ba8e54', color: '#07111b', border: 'none', borderRadius: 8,
          cursor: 'pointer', fontWeight: 700 }}>Reload Space Odyssey</button>
      </main>
    );
  }
}
