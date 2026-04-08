import type { Metadata } from 'next'
import './globals.css'

export const metadata: Metadata = {
  title: 'AIKit Agent Platform',
  description: 'Multi-agent coordination platform with Hedera identity and USDC payments',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  )
}
