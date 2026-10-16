import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { axe } from 'jest-axe';
import React from 'react';
import { ConstellationLegend } from '@/components/constellation/constellation-legend';

describe('ConstellationLegend', () => {
  it('renders Deterministic Brain title in graph mode', () => {
    render(<ConstellationLegend mode="graph" />);
    expect(screen.getByText(/DETERMINISTIC BRAIN/i)).toBeInTheDocument();
    expect(screen.getByText(/Structural AST Dependencies/i)).toBeInTheDocument();
  });

  it('renders Probabilistic Brain title in similar mode', () => {
    render(<ConstellationLegend mode="similar" />);
    expect(screen.getByText(/PROBABILISTIC BRAIN/i)).toBeInTheDocument();
    expect(screen.getByText(/AI Vector Embeddings/i)).toBeInTheDocument();
  });

  it('opens Two Brains comparison guide modal on button click', () => {
    render(<ConstellationLegend mode="graph" />);
    const guideBtn = screen.getByRole('button', { name: /Understand the Two Brains/i });
    fireEvent.click(guideBtn);
    expect(screen.getByText(/Why Two Different Pages\?/i)).toBeInTheDocument();
    expect(screen.getByText(/Exact AST call & import edges/i)).toBeInTheDocument();
    expect(screen.getByText(/Semantic vector similarity/i)).toBeInTheDocument();
  });

  it('has no accessibility violations', async () => {
    const { container } = render(<ConstellationLegend mode="graph" />);
    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });
});
