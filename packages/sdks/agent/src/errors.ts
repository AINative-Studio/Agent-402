/**
 * @ainative/agent-sdk — Error types
 * Built by AINative Dev Team
 * Refs #178
 */

/**
 * Base error class for all AINative SDK errors.
 */
export class AINativeSDKError extends Error {
  readonly status: number;
  readonly code: string;
  readonly details?: unknown;

  constructor(message: string, status: number, code: string, details?: unknown) {
    super(message);
    this.name = 'AINativeSDKError';
    this.status = status;
    this.code = code;
    this.details = details;
    // Maintain proper prototype chain for instanceof checks
    Object.setPrototypeOf(this, new.target.prototype);
  }
}

/**
 * Thrown when the API returns a 401 Unauthorized response.
 * Check that your apiKey or jwt is valid.
 */
export class AuthenticationError extends AINativeSDKError {
  constructor(message = 'Authentication failed. Check your apiKey or jwt.', details?: unknown) {
    super(message, 401, 'AUTHENTICATION_ERROR', details);
    this.name = 'AuthenticationError';
    Object.setPrototypeOf(this, new.target.prototype);
  }
}

/**
 * Thrown when the API returns a 404 Not Found response.
 */
export class NotFoundError extends AINativeSDKError {
  constructor(message = 'Resource not found.', details?: unknown) {
    super(message, 404, 'NOT_FOUND', details);
    this.name = 'NotFoundError';
    Object.setPrototypeOf(this, new.target.prototype);
  }
}

/**
 * Thrown when the API returns a 429 Too Many Requests response.
 */
export class RateLimitError extends AINativeSDKError {
  constructor(message = 'Rate limit exceeded. Please slow down your requests.', details?: unknown) {
    super(message, 429, 'RATE_LIMITED', details);
    this.name = 'RateLimitError';
    Object.setPrototypeOf(this, new.target.prototype);
  }
}

/**
 * Thrown when client-side validation fails before a request is made.
 * For example: unsupported vector dimensions.
 */
export class ValidationError extends AINativeSDKError {
  constructor(message: string, details?: unknown) {
    super(message, 400, 'VALIDATION_ERROR', details);
    this.name = 'ValidationError';
    Object.setPrototypeOf(this, new.target.prototype);
  }
}

/**
 * Thrown when a network error occurs (e.g. DNS failure, connection refused).
 */
export class NetworkError extends AINativeSDKError {
  constructor(message: string, details?: unknown) {
    super(message, 0, 'NETWORK_ERROR', details);
    this.name = 'NetworkError';
    Object.setPrototypeOf(this, new.target.prototype);
  }
}
