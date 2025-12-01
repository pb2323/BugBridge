/**
 * Unit Tests for LoadingSpinner Component
 */

import { render, screen } from '@testing-library/react';
import { LoadingSpinner } from '../../../components/common/LoadingSpinner';

describe('LoadingSpinner', () => {
  it('should render the loading spinner', () => {
    render(<LoadingSpinner />);
    const spinner = screen.getByRole('status');
    expect(spinner).toBeInTheDocument();
    expect(spinner).toHaveAttribute('aria-label', 'Loading');
  });

  it('should render with custom size', () => {
    render(<LoadingSpinner size="lg" />);
    const spinner = screen.getByRole('status');
    expect(spinner).toBeInTheDocument();
  });

  it('should render with custom className', () => {
    const { container } = render(<LoadingSpinner className="custom-class" />);
    const wrapper = container.firstChild;
    expect(wrapper).toHaveClass('custom-class');
  });
});

