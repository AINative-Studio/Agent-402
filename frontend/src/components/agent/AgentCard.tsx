import React from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { ReputationBadge, type ReputationTier } from './ReputationBadge'
import { cn } from '@/lib/utils'

export type AgentStatus = 'active' | 'inactive' | 'busy'

export interface AgentCardProps {
  name: string
  role: string
  did: string
  reputationTier: ReputationTier
  status: AgentStatus
  className?: string
}

const statusConfig: Record<AgentStatus, { label: string; className: string }> = {
  active: { label: 'Active', className: 'bg-green-100 text-green-700' },
  inactive: { label: 'Inactive', className: 'bg-gray-100 text-gray-600' },
  busy: { label: 'Busy', className: 'bg-yellow-100 text-yellow-700' },
}

export function AgentCard({
  name,
  role,
  did,
  reputationTier,
  status,
  className,
}: AgentCardProps) {
  const statusInfo = statusConfig[status]

  return (
    <article className={cn('', className)} aria-label={`Agent: ${name}`}>
      <Card>
        <CardHeader className="pb-2">
          <div className="flex items-start justify-between gap-2">
            <CardTitle className="text-lg">{name}</CardTitle>
            <Badge
              variant="outline"
              className={cn('shrink-0 text-xs', statusInfo.className)}
            >
              {statusInfo.label}
            </Badge>
          </div>
          <p className="text-sm text-muted-foreground">{role}</p>
        </CardHeader>
        <CardContent className="space-y-2">
          <p className="font-mono text-xs text-muted-foreground break-all">{did}</p>
          <ReputationBadge tier={reputationTier} />
        </CardContent>
      </Card>
    </article>
  )
}
