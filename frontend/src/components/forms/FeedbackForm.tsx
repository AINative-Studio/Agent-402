import React, { useState } from 'react'
import { Button } from '@/components/ui/button'

export interface FeedbackFormValues {
  rating: number
  comment: string
}

interface FeedbackFormErrors {
  rating?: string
  comment?: string
}

interface FeedbackFormProps {
  agentDid: string
  onSubmit: (values: FeedbackFormValues) => void
  isLoading?: boolean
}

export function FeedbackForm({ agentDid, onSubmit, isLoading = false }: FeedbackFormProps) {
  const [rating, setRating] = useState<number>(0)
  const [comment, setComment] = useState('')
  const [errors, setErrors] = useState<FeedbackFormErrors>({})

  function validate(): FeedbackFormErrors {
    const errs: FeedbackFormErrors = {}
    if (rating < 1 || rating > 5) errs.rating = 'Rating must be between 1 and 5'
    if (!comment.trim()) errs.comment = 'Comment is required'
    return errs
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    const errs = validate()
    setErrors(errs)
    if (Object.keys(errs).length === 0) {
      onSubmit({ rating, comment })
    }
  }

  return (
    <form onSubmit={handleSubmit} noValidate aria-label="Submit reputation feedback">
      <input type="hidden" name="agentDid" value={agentDid} />
      <div className="space-y-4">
        <div className="space-y-1">
          <fieldset>
            <legend className="text-sm font-medium">Rating (1-5)</legend>
            <div className="flex gap-2 mt-2">
              {[1, 2, 3, 4, 5].map((value) => (
                <button
                  key={value}
                  type="button"
                  onClick={() => setRating(value)}
                  aria-label={`Rate ${value} out of 5`}
                  aria-pressed={rating === value}
                  className={`h-10 w-10 rounded-md border text-sm font-medium transition-colors ${
                    rating === value
                      ? 'bg-primary text-primary-foreground border-primary'
                      : 'bg-background border-input hover:bg-accent'
                  }`}
                >
                  {value}
                </button>
              ))}
            </div>
            {errors.rating && (
              <p role="alert" className="text-sm text-destructive mt-1">
                {errors.rating}
              </p>
            )}
          </fieldset>
        </div>

        <div className="space-y-1">
          <label htmlFor="feedback-comment" className="text-sm font-medium">
            Comment
          </label>
          <textarea
            id="feedback-comment"
            value={comment}
            onChange={(e) => setComment(e.target.value)}
            placeholder="Describe your experience with this agent..."
            rows={4}
            aria-invalid={!!errors.comment}
            className="flex min-h-[80px] w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
          />
          {errors.comment && (
            <p role="alert" className="text-sm text-destructive">
              {errors.comment}
            </p>
          )}
        </div>

        <Button type="submit" disabled={isLoading} className="w-full">
          {isLoading ? 'Submitting...' : 'Submit Feedback'}
        </Button>
      </div>
    </form>
  )
}
