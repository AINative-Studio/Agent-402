import React, { useState } from 'react'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { ReputationBadge, type ReputationTier } from '@/components/agent/ReputationBadge'
import { cn } from '@/lib/utils'

export interface MarketplaceAgent {
  did: string
  name: string
  role: string
  reputationTier: ReputationTier
  capabilities: string[]
  pricePerTaskUsdc: number
  rating: number
  totalTasks: number
}

interface MarketplaceBrowserProps {
  agents: MarketplaceAgent[]
  onHire?: (agentDid: string) => void
  className?: string
}

export function MarketplaceBrowser({ agents, onHire, className }: MarketplaceBrowserProps) {
  const [search, setSearch] = useState('')
  const [capabilityFilter, setCapabilityFilter] = useState('')

  const filtered = agents.filter((agent) => {
    const matchesSearch =
      agent.name.toLowerCase().includes(search.toLowerCase()) ||
      agent.role.toLowerCase().includes(search.toLowerCase())
    const matchesCapability =
      !capabilityFilter ||
      agent.capabilities.some((cap) =>
        cap.toLowerCase().includes(capabilityFilter.toLowerCase())
      )
    return matchesSearch && matchesCapability
  })

  return (
    <section aria-label="Agent Marketplace" className={cn('space-y-4', className)}>
      <h2 className="text-xl font-semibold">Agent Marketplace</h2>

      <div className="flex gap-2 flex-wrap">
        <Input
          placeholder="Search agents..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          aria-label="Search marketplace agents"
          className="max-w-xs"
        />
        <Input
          placeholder="Filter by capability..."
          value={capabilityFilter}
          onChange={(e) => setCapabilityFilter(e.target.value)}
          aria-label="Filter by capability"
          className="max-w-xs"
        />
      </div>

      {filtered.length === 0 ? (
        <p className="text-center text-muted-foreground py-8">
          No agents match your search criteria.
        </p>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {filtered.map((agent) => (
            <Card key={agent.did} className="flex flex-col">
              <CardHeader className="pb-2">
                <div className="flex items-start justify-between gap-2">
                  <CardTitle className="text-base">{agent.name}</CardTitle>
                  <ReputationBadge tier={agent.reputationTier} />
                </div>
                <p className="text-sm text-muted-foreground">{agent.role}</p>
              </CardHeader>
              <CardContent className="flex-1 space-y-3">
                <div className="flex flex-wrap gap-1">
                  {agent.capabilities.map((cap) => (
                    <Badge key={cap} variant="secondary" className="text-xs">
                      {cap}
                    </Badge>
                  ))}
                </div>
                <div className="text-sm space-y-1">
                  <p>
                    <span className="font-medium">{agent.pricePerTaskUsdc} USDC</span>
                    {' '}/ task
                  </p>
                  <p className="text-muted-foreground">
                    {agent.totalTasks} tasks completed
                  </p>
                </div>
                {onHire && (
                  <button
                    type="button"
                    onClick={() => onHire(agent.did)}
                    className="w-full rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90"
                    aria-label={`Hire ${agent.name}`}
                  >
                    Hire Agent
                  </button>
                )}
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </section>
  )
}
