import { Component, type ErrorInfo, type ReactNode } from 'react';

interface Props {
  children: ReactNode;
  /**
   * When this value changes the boundary clears any captured error. Pass the
   * active module/tab key so navigating away from a crashed view recovers it.
   */
  resetKey?: string | number;
  /** Short name of the wrapped area, used in the fallback message. */
  label?: string;
}

interface State {
  error: Error | null;
}

/**
 * Catches render-time errors in a subtree so one crashing artifact module
 * cannot white-screen the whole app. React error boundaries must be class
 * components.
 */
export class ErrorBoundary extends Component<Props, State> {
  state: State = { error: null };

  static getDerivedStateFromError(error: Error): State {
    return { error };
  }

  componentDidUpdate(prevProps: Props) {
    if (prevProps.resetKey !== this.props.resetKey && this.state.error) {
      this.setState({ error: null });
    }
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    // Personal/local tool: no remote logging, so surface to the console.
    console.error(`Unhandled error in ${this.props.label ?? 'component'}:`, error, info.componentStack);
  }

  handleReset = () => this.setState({ error: null });

  render() {
    if (this.state.error) {
      return (
        <div className="error-boundary" role="alert">
          <h3>Something went wrong{this.props.label ? ` in ${this.props.label}` : ''}.</h3>
          <pre className="error-boundary-detail">{this.state.error.message}</pre>
          <button className="download-btn" onClick={this.handleReset}>
            Try again
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}
