import React, { useState } from 'react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'

export interface AgentCreateFormValues {
  name: string
  role: string
  capabilities: string
}

interface AgentCreateFormErrors {
  name?: string
  role?: string
}

interface AgentCreateFormProps {
  onSubmit: (values: AgentCreateFormValues) => void
  isLoading?: boolean
}

export function AgentCreateForm({ onSubmit, isLoading = false }: AgentCreateFormProps) {
  const [values, setValues] = useState<AgentCreateFormValues>({
    name: '',
    role: '',
    capabilities: '',
  })
  const [errors, setErrors] = useState<AgentCreateFormErrors>({})

  function validate(): AgentCreateFormErrors {
    const errs: AgentCreateFormErrors = {}
    if (!values.name.trim()) errs.name = 'Name is required'
    if (!values.role.trim()) errs.role = 'Role is required'
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
    <form onSubmit={handleSubmit} noValidate aria-label="Create agent form">
      <div className="space-y-4">
        <div className="space-y-1">
          <label htmlFor="agent-name" className="text-sm font-medium">
            Agent Name
          </label>
          <Input
            id="agent-name"
            value={values.name}
            onChange={(e) => setValues({ ...values, name: e.target.value })}
            placeholder="e.g. ResearchAgent"
            aria-describedby={errors.name ? 'agent-name-error' : undefined}
            aria-invalid={!!errors.name}
          />
          {errors.name && (
            <p id="agent-name-error" role="alert" className="text-sm text-destructive">
              {errors.name}
            </p>
          )}
        </div>

        <div className="space-y-1">
          <label htmlFor="agent-role" className="text-sm font-medium">
            Role
          </label>
          <Input
            id="agent-role"
            value={values.role}
            onChange={(e) => setValues({ ...values, role: e.target.value })}
            placeholder="e.g. Researcher"
            aria-describedby={errors.role ? 'agent-role-error' : undefined}
            aria-invalid={!!errors.role}
          />
          {errors.role && (
            <p id="agent-role-error" role="alert" className="text-sm text-destructive">
              {errors.role}
            </p>
          )}
        </div>

        <div className="space-y-1">
          <label htmlFor="agent-capabilities" className="text-sm font-medium">
            Capabilities
          </label>
          <Input
            id="agent-capabilities"
            value={values.capabilities}
            onChange={(e) => setValues({ ...values, capabilities: e.target.value })}
            placeholder="e.g. analysis,reporting,summarization"
            aria-label="Capabilities (comma-separated)"
          />
          <p className="text-xs text-muted-foreground">Comma-separated list of capabilities</p>
        </div>

        <Button type="submit" disabled={isLoading} className="w-full">
          {isLoading ? 'Creating...' : 'Create Agent'}
        </Button>
      </div>
    </form>
  )
}
