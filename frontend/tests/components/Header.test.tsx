import React from 'react'
import { render, screen } from '@testing-library/react'
import { Header } from '../../src/components/layout/Header'

describe('Header', () => {
  it('renders the app logo/brand name', () => {
    render(<Header walletConnected={false} />)
    expect(screen.getByText(/AIKit/i)).toBeInTheDocument()
  })

  it('renders the Agents navigation link', () => {
    render(<Header walletConnected={false} />)
    expect(screen.getByRole('link', { name: /agents/i })).toBeInTheDocument()
  })

  it('renders the Payments navigation link', () => {
    render(<Header walletConnected={false} />)
    expect(screen.getByRole('link', { name: /payments/i })).toBeInTheDocument()
  })

  it('renders the Reputation navigation link', () => {
    render(<Header walletConnected={false} />)
    expect(screen.getByRole('link', { name: /reputation/i })).toBeInTheDocument()
  })

  it('shows wallet disconnected state when walletConnected is false', () => {
    render(<Header walletConnected={false} />)
    expect(screen.getByText(/connect wallet/i)).toBeInTheDocument()
  })

  it('shows wallet connected state with address when walletConnected is true', () => {
    render(<Header walletConnected={true} walletAddress="0x1234...abcd" />)
    expect(screen.getByText(/0x1234...abcd/i)).toBeInTheDocument()
  })

  it('has a nav landmark element', () => {
    render(<Header walletConnected={false} />)
    expect(screen.getByRole('navigation')).toBeInTheDocument()
  })

  it('has a banner landmark element', () => {
    render(<Header walletConnected={false} />)
    expect(screen.getByRole('banner')).toBeInTheDocument()
  })
})
