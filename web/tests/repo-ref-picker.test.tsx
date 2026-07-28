import { render, screen } from '@testing-library/react'
import { describe, it, expect } from 'vitest'
import { RepoRefPicker } from '@/components/repo-ref-picker'
import { axe } from 'jest-axe'
import { RepoProvider } from '@/context/RepoContext'

describe('RepoRefPicker component', () => {
  it('renders inputs', () => {
    render(
      <RepoProvider>
        <RepoRefPicker />
      </RepoProvider>
    )
    expect(screen.getByLabelText('Repo:')).toBeInTheDocument()
    expect(screen.getByLabelText('Ref:')).toBeInTheDocument()
  })

  it('has no accessibility violations', async () => {
    const { container } = render(
      <RepoProvider>
        <RepoRefPicker />
      </RepoProvider>
    )
    const results = await axe(container)
    expect(results).toHaveNoViolations()
  })
})
