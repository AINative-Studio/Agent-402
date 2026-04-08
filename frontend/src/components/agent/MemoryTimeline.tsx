import React from 'react'
import { cn } from '@/lib/utils'
import { Badge } from '@/components/ui/badge'

export interface MemoryEntry {
  id: string
  content: string
  timestamp: string
  type: 'observation' | 'reflection' | 'plan' | 'fact'
  decayScore?: number
}

interface MemoryTimelineProps {
  entries: MemoryEntry[]
  className?: string
}

const typeColors: Record<MemoryEntry['type'], string> = {
  observation: 'bg-blue-100 text-blue-700',
  reflection: 'bg-purple-100 text-purple-700',
  plan: 'bg-green-100 text-green-700',
  fact: 'bg-gray-100 text-gray-700',
}

export function MemoryTimeline({ entries, className }: MemoryTimelineProps) {
  if (entries.length === 0) {
    return (
      <p className={cn('text-center text-muted-foreground py-8', className)}>
        No memory entries recorded.
      </p>
    )
  }

  return (
    <ol
      aria-label="Memory timeline"
      className={cn('relative border-l border-muted-foreground/20 space-y-6 pl-6', className)}
    >
      {entries.map((entry) => (
        <li key={entry.id} className="relative">
          <span
            className="absolute -left-[25px] flex h-4 w-4 items-center justify-center rounded-full bg-background border-2 border-primary"
            aria-hidden="true"
          />
          <div className="space-y-1">
            <div className="flex items-center gap-2 flex-wrap">
              <Badge
                variant="outline"
                className={cn('text-xs', typeColors[entry.type])}
              >
                {entry.type}
              </Badge>
              <time
                dateTime={entry.timestamp}
                className="text-xs text-muted-foreground"
              >
                {new Date(entry.timestamp).toLocaleString()}
              </time>
              {entry.decayScore !== undefined && (
                <span className="text-xs text-muted-foreground">
                  decay: {entry.decayScore.toFixed(2)}
                </span>
              )}
            </div>
            <p className="text-sm">{entry.content}</p>
          </div>
        </li>
      ))}
    </ol>
  )
}
