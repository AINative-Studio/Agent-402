import React from 'react'
import { cn } from '@/lib/utils'

interface HeaderProps {
  walletConnected: boolean
  walletAddress?: string
  className?: string
}

const navLinks = [
  { href: '/agents', label: 'Agents' },
  { href: '/payments', label: 'Payments' },
  { href: '/reputation', label: 'Reputation' },
]

export function Header({ walletConnected, walletAddress, className }: HeaderProps) {
  return (
    <header
      className={cn(
        'sticky top-0 z-50 w-full border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60',
        className
      )}
    >
      <div className="container flex h-16 items-center gap-6">
        <a
          href="/"
          className="flex items-center gap-2 font-bold text-lg"
          aria-label="AIKit home"
        >
          <span className="text-primary">AIKit</span>
        </a>

        <nav aria-label="Main navigation" className="flex items-center gap-4">
          {navLinks.map((link) => (
            <a
              key={link.href}
              href={link.href}
              className="text-sm font-medium text-muted-foreground transition-colors hover:text-foreground"
            >
              {link.label}
            </a>
          ))}
        </nav>

        <div className="ml-auto flex items-center gap-3">
          {walletConnected && walletAddress ? (
            <span
              className="rounded-full border px-3 py-1 text-xs font-mono"
              aria-label={`Wallet connected: ${walletAddress}`}
            >
              {walletAddress}
            </span>
          ) : (
            <button
              type="button"
              className="rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90"
              aria-label="Connect wallet"
            >
              Connect Wallet
            </button>
          )}
        </div>
      </div>
    </header>
  )
}
