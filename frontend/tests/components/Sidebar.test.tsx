import React from 'react'
import { render, screen } from '@testing-library/react'
import { Sidebar } from '../../src/components/layout/Sidebar'

describe('Sidebar', () => {
  it('renders the Agents menu item', () => {
    render(<Sidebar activePath="/agents" />)
    expect(screen.getByRole('link', { name: /agents/i })).toBeInTheDocument()
  })

  it('renders the Payments menu item', () => {
    render(<Sidebar activePath="/agents" />)
    expect(screen.getByRole('link', { name: /payments/i })).toBeInTheDocument()
  })

  it('renders the Reputation menu item', () => {
    render(<Sidebar activePath="/agents" />)
    expect(screen.getByRole('link', { name: /reputation/i })).toBeInTheDocument()
  })

  it('renders the Memory menu item', () => {
    render(<Sidebar activePath="/agents" />)
    expect(screen.getByRole('link', { name: /memory/i })).toBeInTheDocument()
  })

  it('renders the Analytics menu item', () => {
    render(<Sidebar activePath="/agents" />)
    expect(screen.getByRole('link', { name: /analytics/i })).toBeInTheDocument()
  })

  it('marks the active menu item with aria-current', () => {
    render(<Sidebar activePath="/payments" />)
    const paymentsLink = screen.getByRole('link', { name: /payments/i })
    expect(paymentsLink).toHaveAttribute('aria-current', 'page')
  })

  it('does not mark inactive items with aria-current', () => {
    render(<Sidebar activePath="/payments" />)
    const agentsLink = screen.getByRole('link', { name: /agents/i })
    expect(agentsLink).not.toHaveAttribute('aria-current', 'page')
  })

  it('has a complementary landmark element', () => {
    render(<Sidebar activePath="/agents" />)
    expect(screen.getByRole('complementary')).toBeInTheDocument()
  })
})
