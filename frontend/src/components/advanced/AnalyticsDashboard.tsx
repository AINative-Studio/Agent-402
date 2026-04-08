import React from 'react'
import { cn } from '@/lib/utils'

export interface AnalyticsMetric {
  label: string
  value: string | number
  delta?: string
  deltaPositive?: boolean
}

interface AnalyticsDashboardProps {
  metrics?: AnalyticsMetric[]
  className?: string
}

const defaultMetrics: AnalyticsMetric[] = [
  { label: 'Total USDC Spent', value: '—', delta: undefined },
  { label: 'Active Agents (7d)', value: '—', delta: undefined },
  { label: 'Tasks Completed', value: '—', delta: undefined },
  { label: 'Avg Drift Score', value: '—', delta: undefined },
]

export function AnalyticsDashboard({
  metrics = defaultMetrics,
  className,
}: AnalyticsDashboardProps) {
  return (
    <section
      aria-label="Analytics Dashboard"
      className={cn('space-y-6', className)}
    >
      <h2 className="text-xl font-semibold">Analytics</h2>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {metrics.map((metric) => (
          <div
            key={metric.label}
            className="rounded-lg border bg-card p-6 shadow-sm"
            aria-label={`${metric.label}: ${metric.value}`}
          >
            <p className="text-sm font-medium text-muted-foreground">{metric.label}</p>
            <p className="mt-2 text-3xl font-bold">{metric.value}</p>
            {metric.delta && (
              <p
                className={cn(
                  'mt-1 text-xs',
                  metric.deltaPositive ? 'text-green-600' : 'text-red-600'
                )}
              >
                {metric.deltaPositive ? '+' : ''}{metric.delta} vs last period
              </p>
            )}
          </div>
        ))}
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <div
          className="rounded-lg border p-6 space-y-2"
          aria-label="Spend over time chart placeholder"
        >
          <h3 className="font-medium">Spend Over Time</h3>
          <div
            className="flex h-48 items-center justify-center rounded-md bg-muted text-sm text-muted-foreground"
            role="img"
            aria-label="Spend chart (coming soon)"
          >
            Chart coming soon
          </div>
        </div>

        <div
          className="rounded-lg border p-6 space-y-2"
          aria-label="Agent activity chart placeholder"
        >
          <h3 className="font-medium">Agent Activity</h3>
          <div
            className="flex h-48 items-center justify-center rounded-md bg-muted text-sm text-muted-foreground"
            role="img"
            aria-label="Activity chart (coming soon)"
          >
            Chart coming soon
          </div>
        </div>
      </div>

      <div
        className="rounded-lg border p-6 space-y-2"
        aria-label="Reputation drift chart placeholder"
      >
        <h3 className="font-medium">Reputation Drift</h3>
        <div
          className="flex h-48 items-center justify-center rounded-md bg-muted text-sm text-muted-foreground"
          role="img"
          aria-label="Drift chart (coming soon)"
        >
          Chart coming soon
        </div>
      </div>
    </section>
  )
}
