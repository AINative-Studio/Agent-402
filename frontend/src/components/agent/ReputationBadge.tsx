import React from 'react'
import { Badge } from '@/components/ui/badge'
import { cn } from '@/lib/utils'

export type ReputationTier = 'NEW' | 'BASIC' | 'TRUSTED' | 'VERIFIED' | 'ESTABLISHED'

interface ReputationBadgeProps {
  tier: ReputationTier
  className?: string
}

const tierStyles: Record<ReputationTier, string> = {
  NEW: 'bg-gray-100 text-gray-700 border-gray-200',
  BASIC: 'bg-blue-100 text-blue-700 border-blue-200',
  TRUSTED: 'bg-green-100 text-green-700 border-green-200',
  VERIFIED: 'bg-purple-100 text-purple-700 border-purple-200',
  ESTABLISHED: 'bg-amber-100 text-amber-700 border-amber-200',
}

export function ReputationBadge({ tier, className }: ReputationBadgeProps) {
  return (
    <Badge
      variant="outline"
      className={cn(tierStyles[tier], 'font-semibold', className)}
      aria-label={`Reputation tier: ${tier}`}
    >
      {tier}
    </Badge>
  )
}
