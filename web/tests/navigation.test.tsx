import { render, screen } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import { Navigation } from '@/components/navigation'
import { axe } from 'jest-axe'

// Mock next/navigation
vi.mock('next/navigation', () => ({
  usePathname: () => '/dashboard',
}))

describe('Navigation component', () => {
  it('renders navigation links', () => {
    render(<Navigation />)
    expect(screen.getByText('GDSS')).toBeInTheDocument()
    expect(screen.getByText('Dashboard')).toBeInTheDocument()
    expect(screen.getByText('Semantic Graph')).toBeInTheDocument()
  })

  it('has no accessibility violations', async () => {
    const { container } = render(<Navigation />)
    const results = await axe(container)
    expect(results).toHaveNoViolations()
  })
})
