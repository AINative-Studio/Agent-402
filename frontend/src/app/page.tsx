import { PageLayout } from '@/components/layout/PageLayout'

export default function DashboardPage() {
  return (
    <PageLayout activePath="/">
      <div className="space-y-6">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Dashboard</h1>
          <p className="text-muted-foreground">
            Welcome to the AIKit Agent Platform. Manage your agent swarm, payments, and reputation.
          </p>
        </div>

        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          {[
            { title: 'Active Agents', value: '—', description: 'Agents currently running' },
            { title: 'Total Payments', value: '—', description: 'USDC transferred this month' },
            { title: 'Avg Reputation', value: '—', description: 'Mean trust score across agents' },
            { title: 'Memory Entries', value: '—', description: 'Total memory records stored' },
          ].map((stat) => (
            <div
              key={stat.title}
              className="rounded-lg border bg-card p-6 shadow-sm"
            >
              <p className="text-sm font-medium text-muted-foreground">{stat.title}</p>
              <p className="mt-2 text-3xl font-bold">{stat.value}</p>
              <p className="mt-1 text-xs text-muted-foreground">{stat.description}</p>
            </div>
          ))}
        </div>
      </div>
    </PageLayout>
  )
}
