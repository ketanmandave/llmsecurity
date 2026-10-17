import { Component, type ErrorInfo, type ReactNode } from 'react';

interface Props {
  children: ReactNode;
}

interface State {
  hasError: boolean;
}

export default class ErrorBoundary extends Component<Props, State> {
  state: State = { hasError: false };

  static getDerivedStateFromError() {
    return { hasError: true };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('Unhandled error:', error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="flex min-h-screen items-center justify-center bg-slate-950 p-4 text-center text-slate-100">
          <div className="rounded-3xl border border-slate-800 bg-slate-900/80 p-8 shadow-glow">
            <h1 className="text-3xl font-semibold">Something went wrong</h1>
            <p className="mt-2 text-slate-400">The application encountered an unexpected error.</p>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}
