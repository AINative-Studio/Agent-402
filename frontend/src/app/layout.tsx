import type { Metadata } from 'next'
import './globals.css'

export const metadata: Metadata = {
  title: 'Agent-402: Autonomous Fintech Agent Infrastructure on Hedera',
  description: 'Agent-402: Autonomous fintech agent infrastructure on Hedera',
  robots: 'index, follow',
  openGraph: {
    title: 'Agent-402: Autonomous Fintech Agent Infrastructure on Hedera',
    description: 'Agent-402: Autonomous fintech agent infrastructure on Hedera',
    url: 'https://agent402.ainative.studio',
    images: [
      {
        url: 'https://agent402.ainative.studio/og-image.png',
        width: 1200,
        height: 630,
        alt: 'Agent-402',
      },
    ],
    type: 'website',
  },
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <head>
        <link rel="canonical" href="https://agent402.ainative.studio" />
        <meta name="robots" content="index, follow" />
        <meta
          name="description"
          content="Agent-402: Autonomous fintech agent infrastructure on Hedera"
        />
        <meta
          property="og:title"
          content="Agent-402: Autonomous Fintech Agent Infrastructure on Hedera"
        />
        <meta
          property="og:description"
          content="Agent-402: Autonomous fintech agent infrastructure on Hedera"
        />
        <meta property="og:url" content="https://agent402.ainative.studio" />
        <meta
          property="og:image"
          content="https://agent402.ainative.studio/og-image.png"
        />
      </head>
      <body>{children}</body>
    </html>
  )
}
