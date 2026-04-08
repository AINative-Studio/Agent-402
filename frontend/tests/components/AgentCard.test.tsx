import React from 'react'
import { render, screen } from '@testing-library/react'
import { AgentCard } from '../../src/components/agent/AgentCard'

const baseProps = {
  name: 'ResearchAgent',
  role: 'Researcher',
  did: 'did:hedera:testnet:z6Mk123',
  reputationTier: 'TRUSTED' as const,
  status: 'active' as const,
}

describe('AgentCard', () => {
  it('renders the agent name', () => {
    render(<AgentCard {...baseProps} />)
    expect(screen.getByText('ResearchAgent')).toBeInTheDocument()
  })

  it('renders the agent role', () => {
    render(<AgentCard {...baseProps} />)
    expect(screen.getByText('Researcher')).toBeInTheDocument()
  })

  it('renders the DID', () => {
    render(<AgentCard {...baseProps} />)
    expect(screen.getByText('did:hedera:testnet:z6Mk123')).toBeInTheDocument()
  })

  it('renders the reputation tier badge', () => {
    render(<AgentCard {...baseProps} />)
    expect(screen.getByText('TRUSTED')).toBeInTheDocument()
  })

  it('renders the active status badge', () => {
    render(<AgentCard {...baseProps} status="active" />)
    expect(screen.getByText('Active')).toBeInTheDocument()
  })

  it('renders the inactive status badge', () => {
    render(<AgentCard {...baseProps} status="inactive" />)
    expect(screen.getByText('Inactive')).toBeInTheDocument()
  })

  it('renders a NEW reputation tier badge', () => {
    render(<AgentCard {...baseProps} reputationTier="NEW" />)
    expect(screen.getByText('NEW')).toBeInTheDocument()
  })

  it('renders a VERIFIED reputation tier badge', () => {
    render(<AgentCard {...baseProps} reputationTier="VERIFIED" />)
    expect(screen.getByText('VERIFIED')).toBeInTheDocument()
  })

  it('renders an ESTABLISHED reputation tier badge', () => {
    render(<AgentCard {...baseProps} reputationTier="ESTABLISHED" />)
    expect(screen.getByText('ESTABLISHED')).toBeInTheDocument()
  })

  it('has accessible role landmark', () => {
    render(<AgentCard {...baseProps} />)
    expect(screen.getByRole('article')).toBeInTheDocument()
  })
})
