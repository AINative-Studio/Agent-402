import React from 'react'
import { cn } from '@/lib/utils'
import { Badge } from '@/components/ui/badge'

export interface HCSAnchorRecord {
  id: string
  topicId: string
  sequenceNumber: number
  consensusTimestamp: string
  message: string
  anchorType: 'memory' | 'reputation' | 'payment' | 'identity'
}

interface HCSAnchorViewerProps {
  records: HCSAnchorRecord[]
  mirrorNodeBaseUrl?: string
  className?: string
}

const anchorTypeColors: Record<HCSAnchorRecord['anchorType'], string> = {
  memory: 'bg-blue-100 text-blue-700',
  reputation: 'bg-purple-100 text-purple-700',
  payment: 'bg-green-100 text-green-700',
  identity: 'bg-amber-100 text-amber-700',
}

export function HCSAnchorViewer({
  records,
  mirrorNodeBaseUrl = 'https://hashscan.io/testnet/topic',
  className,
}: HCSAnchorViewerProps) {
  if (records.length === 0) {
    return (
      <p className={cn('text-center text-muted-foreground py-8', className)}>
        No HCS anchor records found.
      </p>
    )
  }

  return (
    <section
      aria-label="HCS Anchor Records"
      className={cn('space-y-3', className)}
    >
      {records.map((record) => (
        <div
          key={record.id}
          className="rounded-lg border p-4 space-y-2"
          aria-label={`HCS record ${record.sequenceNumber}`}
        >
          <div className="flex items-center justify-between gap-2 flex-wrap">
            <div className="flex items-center gap-2">
              <Badge
                variant="outline"
                className={cn('text-xs', anchorTypeColors[record.anchorType])}
              >
                {record.anchorType}
              </Badge>
              <span className="text-xs text-muted-foreground">
                #{record.sequenceNumber}
              </span>
            </div>
            <time
              dateTime={record.consensusTimestamp}
              className="text-xs text-muted-foreground"
            >
              {new Date(record.consensusTimestamp).toLocaleString()}
            </time>
          </div>
          <div>
            <a
              href={`${mirrorNodeBaseUrl}/${record.topicId}`}
              target="_blank"
              rel="noopener noreferrer"
              className="font-mono text-xs text-blue-600 hover:underline"
              aria-label={`View topic ${record.topicId} on mirror node`}
            >
              Topic: {record.topicId}
            </a>
          </div>
          <p className="text-sm">{record.message}</p>
        </div>
      ))}
    </section>
  )
}
