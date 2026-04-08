import React from 'react'
import { Header } from './Header'
import { Sidebar } from './Sidebar'
import { cn } from '@/lib/utils'

interface PageLayoutProps {
  children: React.ReactNode
  activePath?: string
  walletConnected?: boolean
  walletAddress?: string
  className?: string
}

export function PageLayout({
  children,
  activePath = '/',
  walletConnected = false,
  walletAddress,
  className,
}: PageLayoutProps) {
  return (
    <div className="flex min-h-screen flex-col">
      <Header walletConnected={walletConnected} walletAddress={walletAddress} />
      <div className="flex flex-1">
        <Sidebar activePath={activePath} />
        <main
          id="main-content"
          className={cn('flex-1 overflow-auto p-6', className)}
          aria-label="Main content"
        >
          {children}
        </main>
      </div>
    </div>
  )
}
