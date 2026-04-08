import React from 'react'
import { Badge } from '@/components/ui/badge'
import { cn } from '@/lib/utils'

export interface SwarmStage {
  id: string
  name: string
  agentName: string
  agentDid: string
  status: 'pending' | 'running' | 'completed' | 'failed'
  startedAt?: string
  completedAt?: string
}

interface AgentSwarmViewProps {
  workflowName: string
  stages: SwarmStage[]
  className?: string
}

const stageStatusStyles: Record<SwarmStage['status'], string> = {
  pending: 'bg-gray-100 text-gray-600',
  running: 'bg-blue-100 text-blue-700',
  completed: 'bg-green-100 text-green-700',
  failed: 'bg-red-100 text-red-700',
}

export function AgentSwarmView({ workflowName, stages, className }: AgentSwarmViewProps) {
  return (
    <section
      aria-label={`Agent swarm workflow: ${workflowName}`}
      className={cn('space-y-4', className)}
    >
      <h2 className="text-xl font-semibold">{workflowName}</h2>
      <ol aria-label="Workflow stages" className="relative space-y-4">
        {stages.map((stage, index) => (
          <li
            key={stage.id}
            className="flex items-start gap-4 rounded-lg border p-4"
            aria-label={`Stage ${index + 1}: ${stage.name}`}
          >
            <div
              className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full border-2 border-primary text-sm font-bold"
              aria-hidden="true"
            >
              {index + 1}
            </div>
            <div className="flex-1 space-y-1">
              <div className="flex items-center justify-between gap-2">
                <p className="font-medium">{stage.name}</p>
                <Badge
                  variant="outline"
                  className={cn('text-xs', stageStatusStyles[stage.status])}
                >
                  {stage.status}
                </Badge>
              </div>
              <p className="text-sm text-muted-foreground">Agent: {stage.agentName}</p>
              <p className="font-mono text-xs text-muted-foreground">{stage.agentDid}</p>
              {stage.startedAt && (
                <p className="text-xs text-muted-foreground">
                  Started: {new Date(stage.startedAt).toLocaleString()}
                </p>
              )}
              {stage.completedAt && (
                <p className="text-xs text-muted-foreground">
                  Completed: {new Date(stage.completedAt).toLocaleString()}
                </p>
              )}
            </div>
          </li>
        ))}
      </ol>
    </section>
  )
}
