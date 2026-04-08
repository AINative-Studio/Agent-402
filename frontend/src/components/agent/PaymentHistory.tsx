import React from 'react'
import {
  Table,
  TableBody,
  TableCaption,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { Badge } from '@/components/ui/badge'

export interface PaymentRecord {
  id: string
  txHash: string
  amount: string
  currency: 'USDC'
  recipient: string
  timestamp: string
  status: 'confirmed' | 'pending' | 'failed'
}

interface PaymentHistoryProps {
  payments: PaymentRecord[]
  mirrorNodeBaseUrl?: string
}

const statusVariant: Record<
  PaymentRecord['status'],
  'default' | 'secondary' | 'destructive'
> = {
  confirmed: 'default',
  pending: 'secondary',
  failed: 'destructive',
}

function truncateTx(hash: string): string {
  if (hash.length <= 16) return hash
  return `${hash.slice(0, 8)}...${hash.slice(-8)}`
}

export function PaymentHistory({
  payments,
  mirrorNodeBaseUrl = 'https://hashscan.io/testnet/transaction',
}: PaymentHistoryProps) {
  return (
    <Table>
      <TableCaption>Recent USDC payment transactions</TableCaption>
      <TableHeader>
        <TableRow>
          <TableHead>Tx Hash</TableHead>
          <TableHead>Amount</TableHead>
          <TableHead>Recipient</TableHead>
          <TableHead>Date</TableHead>
          <TableHead>Status</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {payments.length === 0 ? (
          <TableRow>
            <TableCell colSpan={5} className="text-center text-muted-foreground">
              No payment records found.
            </TableCell>
          </TableRow>
        ) : (
          payments.map((payment) => (
            <TableRow key={payment.id}>
              <TableCell className="font-mono text-xs">
                <a
                  href={`${mirrorNodeBaseUrl}/${payment.txHash}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-blue-600 hover:underline"
                  aria-label={`View transaction ${payment.txHash}`}
                >
                  {truncateTx(payment.txHash)}
                </a>
              </TableCell>
              <TableCell>
                {payment.amount} {payment.currency}
              </TableCell>
              <TableCell className="font-mono text-xs">{payment.recipient}</TableCell>
              <TableCell>{new Date(payment.timestamp).toLocaleDateString()}</TableCell>
              <TableCell>
                <Badge variant={statusVariant[payment.status]}>
                  {payment.status}
                </Badge>
              </TableCell>
            </TableRow>
          ))
        )}
      </TableBody>
    </Table>
  )
}
