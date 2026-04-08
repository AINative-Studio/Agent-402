import React, { useState } from 'react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'

export interface TaskSubmitFormValues {
  taskType: string
  description: string
  targetAgentDid: string
  priority: 'low' | 'medium' | 'high'
}

interface TaskSubmitFormErrors {
  taskType?: string
  description?: string
  targetAgentDid?: string
}

interface TaskSubmitFormProps {
  onSubmit: (values: TaskSubmitFormValues) => void
  isLoading?: boolean
}

export function TaskSubmitForm({ onSubmit, isLoading = false }: TaskSubmitFormProps) {
  const [values, setValues] = useState<TaskSubmitFormValues>({
    taskType: '',
    description: '',
    targetAgentDid: '',
    priority: 'medium',
  })
  const [errors, setErrors] = useState<TaskSubmitFormErrors>({})

  function validate(): TaskSubmitFormErrors {
    const errs: TaskSubmitFormErrors = {}
    if (!values.taskType.trim()) errs.taskType = 'Task type is required'
    if (!values.description.trim()) errs.description = 'Description is required'
    if (!values.targetAgentDid.trim()) errs.targetAgentDid = 'Target agent DID is required'
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
    <form onSubmit={handleSubmit} noValidate aria-label="Submit task to agent swarm">
      <div className="space-y-4">
        <div className="space-y-1">
          <label htmlFor="task-type" className="text-sm font-medium">
            Task Type
          </label>
          <Input
            id="task-type"
            value={values.taskType}
            onChange={(e) => setValues({ ...values, taskType: e.target.value })}
            placeholder="e.g. research, summarize, analyze"
            aria-invalid={!!errors.taskType}
          />
          {errors.taskType && (
            <p role="alert" className="text-sm text-destructive">
              {errors.taskType}
            </p>
          )}
        </div>

        <div className="space-y-1">
          <label htmlFor="task-description" className="text-sm font-medium">
            Description
          </label>
          <textarea
            id="task-description"
            value={values.description}
            onChange={(e) => setValues({ ...values, description: e.target.value })}
            placeholder="Describe the task in detail..."
            rows={4}
            aria-invalid={!!errors.description}
            className="flex min-h-[80px] w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
          />
          {errors.description && (
            <p role="alert" className="text-sm text-destructive">
              {errors.description}
            </p>
          )}
        </div>

        <div className="space-y-1">
          <label htmlFor="task-agent-did" className="text-sm font-medium">
            Target Agent DID
          </label>
          <Input
            id="task-agent-did"
            value={values.targetAgentDid}
            onChange={(e) => setValues({ ...values, targetAgentDid: e.target.value })}
            placeholder="did:hedera:testnet:z6Mk..."
            aria-invalid={!!errors.targetAgentDid}
          />
          {errors.targetAgentDid && (
            <p role="alert" className="text-sm text-destructive">
              {errors.targetAgentDid}
            </p>
          )}
        </div>

        <div className="space-y-1">
          <label htmlFor="task-priority" className="text-sm font-medium">
            Priority
          </label>
          <select
            id="task-priority"
            value={values.priority}
            onChange={(e) =>
              setValues({ ...values, priority: e.target.value as TaskSubmitFormValues['priority'] })
            }
            className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
          >
            <option value="low">Low</option>
            <option value="medium">Medium</option>
            <option value="high">High</option>
          </select>
        </div>

        <Button type="submit" disabled={isLoading} className="w-full">
          {isLoading ? 'Submitting...' : 'Submit Task'}
        </Button>
      </div>
    </form>
  )
}
