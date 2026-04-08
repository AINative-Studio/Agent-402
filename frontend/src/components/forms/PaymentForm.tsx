import React, { useState } from 'react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'

export interface PaymentFormValues {
  amount: string
  recipient: string
  memo: string
}

interface PaymentFormErrors {
  amount?: string
  recipient?: string
}

interface PaymentFormProps {
  onSubmit: (values: PaymentFormValues) => void
  isLoading?: boolean
}

export function PaymentForm({ onSubmit, isLoading = false }: PaymentFormProps) {
  const [values, setValues] = useState<PaymentFormValues>({
    amount: '',
    recipient: '',
    memo: '',
  })
  const [errors, setErrors] = useState<PaymentFormErrors>({})

  function validate(): PaymentFormErrors {
    const errs: PaymentFormErrors = {}
    const amount = parseFloat(values.amount)
    if (!values.amount || isNaN(amount) || amount <= 0) {
      errs.amount = 'Amount must be a positive number'
    }
    if (!values.recipient.trim()) {
      errs.recipient = 'Recipient address is required'
    }
    return errs
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    const errs = validate()
    setErrors(errs)
    if (Object.keys(errs).length === 0) {
      onSubmit(values)
    }
  }

  return (
    <form onSubmit={handleSubmit} noValidate aria-label="Initiate USDC payment">
      <div className="space-y-4">
        <div className="space-y-1">
          <label htmlFor="payment-amount" className="text-sm font-medium">
            Amount (USDC)
          </label>
          <Input
            id="payment-amount"
            type="number"
            min="0"
            step="0.01"
            value={values.amount}
            onChange={(e) => setValues({ ...values, amount: e.target.value })}
            placeholder="0.00"
            aria-invalid={!!errors.amount}
          />
          {errors.amount && (
            <p role="alert" className="text-sm text-destructive">
              {errors.amount}
            </p>
          )}
        </div>

        <div className="space-y-1">
          <label htmlFor="payment-recipient" className="text-sm font-medium">
            Recipient
          </label>
          <Input
            id="payment-recipient"
            value={values.recipient}
            onChange={(e) => setValues({ ...values, recipient: e.target.value })}
            placeholder="0.0.12345 or DID"
            aria-invalid={!!errors.recipient}
          />
          {errors.recipient && (
            <p role="alert" className="text-sm text-destructive">
              {errors.recipient}
            </p>
          )}
        </div>

        <div className="space-y-1">
          <label htmlFor="payment-memo" className="text-sm font-medium">
            Memo (optional)
          </label>
          <Input
            id="payment-memo"
            value={values.memo}
            onChange={(e) => setValues({ ...values, memo: e.target.value })}
            placeholder="e.g. Task payment for analysis"
          />
        </div>

        <Button type="submit" disabled={isLoading} className="w-full">
          {isLoading ? 'Sending...' : 'Send USDC'}
        </Button>
      </div>
    </form>
  )
}
