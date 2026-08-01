import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { axe } from 'jest-axe';
import React from 'react';
import { SymbolSearchPicker } from '../../components/constellation/symbol-search-picker';

const mockSymbols = [
  { id: 'app.py::run_app', name: 'run_app', type: 'function', location: 'app.py' },
  { id: 'utils.py::parse_args', name: 'parse_args', type: 'function', location: 'utils.py' },
  { id: 'auth.py::AuthService', name: 'AuthService', type: 'class', location: 'auth.py' },
];

describe('SymbolSearchPicker', () => {
  it('renders input field with placeholder', () => {
    render(
      <SymbolSearchPicker
        symbols={mockSymbols}
        onSelectSymbol={vi.fn()}
        placeholder="Search symbols..."
      />
    );
    expect(screen.getByPlaceholderText('Search symbols...')).toBeInTheDocument();
  });

  it('shows matching symbols dropdown when typing query', () => {
    render(
      <SymbolSearchPicker
        symbols={mockSymbols}
        onSelectSymbol={vi.fn()}
      />
    );
    const input = screen.getByRole('combobox');
    fireEvent.change(input, { target: { value: 'auth' } });
    expect(screen.getByText('AuthService')).toBeInTheDocument();
    expect(screen.getByText('auth.py')).toBeInTheDocument();
    expect(screen.queryByText('run_app')).not.toBeInTheDocument();
  });

  it('calls onSelectSymbol when clicking a symbol option', () => {
    const handleSelect = vi.fn();
    render(
      <SymbolSearchPicker
        symbols={mockSymbols}
        onSelectSymbol={handleSelect}
      />
    );
    const input = screen.getByRole('combobox');
    fireEvent.change(input, { target: { value: 'parse' } });
    const option = screen.getByRole('option', { name: /parse_args/i });
    fireEvent.click(option);
    expect(handleSelect).toHaveBeenCalledWith('utils.py::parse_args', 'parse_args');
  });

  it('has no accessibility violations', async () => {
    const { container } = render(
      <SymbolSearchPicker
        symbols={mockSymbols}
        onSelectSymbol={vi.fn()}
      />
    );
    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });
});
