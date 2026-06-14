import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { useState } from 'react';
import { ErrorBoundary } from './ErrorBoundary';

function Boom({ message }: { message: string }): never {
  throw new Error(message);
}

describe('ErrorBoundary', () => {
  beforeEach(() => {
    // React logs caught errors to console.error; silence the expected noise.
    vi.spyOn(console, 'error').mockImplementation(() => {});
  });
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('renders children when nothing throws', () => {
    render(
      <ErrorBoundary>
        <div>healthy</div>
      </ErrorBoundary>,
    );
    expect(screen.getByText('healthy')).toBeInTheDocument();
  });

  it('shows a labelled fallback with the error message when a child throws', () => {
    render(
      <ErrorBoundary label="Photos">
        <Boom message="kaboom" />
      </ErrorBoundary>,
    );
    expect(screen.getByRole('alert')).toHaveTextContent('Something went wrong in Photos.');
    expect(screen.getByText('kaboom')).toBeInTheDocument();
  });

  it('clears the error when resetKey changes', async () => {
    function Harness() {
      const [tab, setTab] = useState('a');
      return (
        <>
          <button onClick={() => setTab('b')}>switch</button>
          <ErrorBoundary resetKey={tab}>{tab === 'a' ? <Boom message="x" /> : <div>recovered</div>}</ErrorBoundary>
        </>
      );
    }
    render(<Harness />);
    expect(screen.getByRole('alert')).toBeInTheDocument();
    await userEvent.click(screen.getByText('switch'));
    expect(screen.getByText('recovered')).toBeInTheDocument();
    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
  });
});
