import React from 'react'
import { cn } from '@/lib/utils'

interface SidebarProps {
  activePath: string
  className?: string
}

const menuItems = [
  { href: '/agents', label: 'Agents', icon: 'agent' },
  { href: '/payments', label: 'Payments', icon: 'payment' },
  { href: '/reputation', label: 'Reputation', icon: 'reputation' },
  { href: '/memory', label: 'Memory', icon: 'memory' },
  { href: '/analytics', label: 'Analytics', icon: 'analytics' },
]

export function Sidebar({ activePath, className }: SidebarProps) {
  return (
    <aside
      className={cn('w-64 shrink-0 border-r bg-background', className)}
      aria-label="Application sidebar"
    >
      <nav aria-label="Sidebar navigation" className="p-4 space-y-1">
        {menuItems.map((item) => {
          const isActive = activePath === item.href
          return (
            <a
              key={item.href}
              href={item.href}
              aria-current={isActive ? 'page' : undefined}
              className={cn(
                'flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors',
                isActive
                  ? 'bg-primary/10 text-primary'
                  : 'text-muted-foreground hover:bg-accent hover:text-accent-foreground'
              )}
            >
              {item.label}
            </a>
          )
        })}
      </nav>
    </aside>
  )
}
