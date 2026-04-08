import React, { useState } from 'react'
import { Input } from '@/components/ui/input'
import { AgentCard, type AgentCardProps } from './AgentCard'
import { type ReputationTier } from './ReputationBadge'

interface AgentListProps {
  agents: AgentCardProps[]
  className?: string
}

export function AgentList({ agents, className }: AgentListProps) {
  const [search, setSearch] = useState('')
  const [filterTier, setFilterTier] = useState<ReputationTier | 'ALL'>('ALL')

  const filtered = agents.filter((agent) => {
    const matchesSearch =
      agent.name.toLowerCase().includes(search.toLowerCase()) ||
      agent.role.toLowerCase().includes(search.toLowerCase())
    const matchesTier = filterTier === 'ALL' || agent.reputationTier === filterTier
    return matchesSearch && matchesTier
  })

  return (
    <div className={className}>
      <div className="mb-4 flex gap-2">
        <Input
          placeholder="Search agents..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          aria-label="Search agents"
          className="max-w-sm"
        />
        <select
          value={filterTier}
          onChange={(e) => setFilterTier(e.target.value as ReputationTier | 'ALL')}
          aria-label="Filter by reputation tier"
          className="rounded-md border border-input bg-background px-3 py-2 text-sm"
        >
          <option value="ALL">All Tiers</option>
          <option value="NEW">NEW</option>
          <option value="BASIC">BASIC</option>
          <option value="TRUSTED">TRUSTED</option>
          <option value="VERIFIED">VERIFIED</option>
          <option value="ESTABLISHED">ESTABLISHED</option>
        </select>
      </div>
      {filtered.length === 0 ? (
        <p className="text-center text-muted-foreground py-8">No agents found.</p>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {filtered.map((agent) => (
            <AgentCard key={agent.did} {...agent} />
          ))}
        </div>
      )}
    </div>
  )
}
