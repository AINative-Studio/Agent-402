import React from 'react'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { AgentCreateForm } from '../../src/components/forms/AgentCreateForm'

describe('AgentCreateForm', () => {
  it('renders the name field', () => {
    render(<AgentCreateForm onSubmit={jest.fn()} />)
    expect(screen.getByLabelText(/agent name/i)).toBeInTheDocument()
  })

  it('renders the role field', () => {
    render(<AgentCreateForm onSubmit={jest.fn()} />)
    expect(screen.getByLabelText(/role/i)).toBeInTheDocument()
  })

  it('renders the capabilities field', () => {
    render(<AgentCreateForm onSubmit={jest.fn()} />)
    expect(screen.getByLabelText(/capabilities/i)).toBeInTheDocument()
  })

  it('renders a submit button', () => {
    render(<AgentCreateForm onSubmit={jest.fn()} />)
    expect(screen.getByRole('button', { name: /create agent/i })).toBeInTheDocument()
  })

  it('calls onSubmit with form values when submitted', async () => {
    const user = userEvent.setup()
    const onSubmit = jest.fn()
    render(<AgentCreateForm onSubmit={onSubmit} />)

    await user.type(screen.getByLabelText(/agent name/i), 'TestAgent')
    await user.type(screen.getByLabelText(/role/i), 'Analyst')
    await user.type(screen.getByLabelText(/capabilities/i), 'analysis,reporting')
    await user.click(screen.getByRole('button', { name: /create agent/i }))

    await waitFor(() => {
      expect(onSubmit).toHaveBeenCalledWith({
        name: 'TestAgent',
        role: 'Analyst',
        capabilities: 'analysis,reporting',
      })
    })
  })

  it('shows validation error when name is empty on submit', async () => {
    const user = userEvent.setup()
    const onSubmit = jest.fn()
    render(<AgentCreateForm onSubmit={onSubmit} />)

    await user.click(screen.getByRole('button', { name: /create agent/i }))

    await waitFor(() => {
      expect(screen.getByText(/name is required/i)).toBeInTheDocument()
    })
    expect(onSubmit).not.toHaveBeenCalled()
  })

  it('shows validation error when role is empty on submit', async () => {
    const user = userEvent.setup()
    const onSubmit = jest.fn()
    render(<AgentCreateForm onSubmit={onSubmit} />)

    await user.type(screen.getByLabelText(/agent name/i), 'TestAgent')
    await user.click(screen.getByRole('button', { name: /create agent/i }))

    await waitFor(() => {
      expect(screen.getByText(/role is required/i)).toBeInTheDocument()
    })
    expect(onSubmit).not.toHaveBeenCalled()
  })

  it('does not call onSubmit when form is invalid', async () => {
    const user = userEvent.setup()
    const onSubmit = jest.fn()
    render(<AgentCreateForm onSubmit={onSubmit} />)

    await user.click(screen.getByRole('button', { name: /create agent/i }))

    expect(onSubmit).not.toHaveBeenCalled()
  })
})
