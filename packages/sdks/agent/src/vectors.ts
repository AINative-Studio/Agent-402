/**
 * @ainative/agent-sdk — Vector operations
 * Built by AINative Dev Team
 * Refs #180
 */

import type { HttpClient } from './client';
import type {
  SupportedDimension,
  VectorMetadata,
  VectorUpsertOptions,
  VectorSearchOptions,
  VectorSearchResult,
  VectorUpsertResult,
} from './types';
import { AINativeSDKError } from './errors';

const VECTORS_BASE = '/api/v1/public/vectors';

const SUPPORTED_DIMENSIONS: SupportedDimension[] = [384, 768, 1024, 1536];

function validateDimensions(embedding: number[]): void {
  const dim = embedding.length;
  if (!(SUPPORTED_DIMENSIONS as number[]).includes(dim)) {
    throw new AINativeSDKError(
      `Invalid embedding dimension: ${dim}. Supported dimensions are ${SUPPORTED_DIMENSIONS.join(', ')}.`,
      400,
      'INVALID_DIMENSION'
    );
  }
}

export class VectorsModule {
  constructor(private readonly client: HttpClient) {}

  /**
   * Upsert a vector embedding with metadata.
   * Validates that the embedding has a supported dimension (384, 768, 1024, or 1536).
   */
  async upsert(
    embedding: number[],
    metadata: VectorMetadata,
    options?: VectorUpsertOptions
  ): Promise<VectorUpsertResult> {
    // Client-side dimension validation before any network call
    validateDimensions(embedding);

    const body: Record<string, unknown> = { embedding, metadata };

    if (options?.namespace) body.namespace = options.namespace;
    if (options?.vectorId) body.vector_id = options.vectorId;
    if (options?.model) body.model = options.model;

    return this.client.post<VectorUpsertResult>(`${VECTORS_BASE}/`, body);
  }

  /**
   * Perform semantic search over stored vectors.
   */
  async search(
    query: string,
    options?: VectorSearchOptions
  ): Promise<{ results: VectorSearchResult[]; total: number }> {
    const body: Record<string, unknown> = { query };

    if (options?.namespace) body.namespace = options.namespace;
    if (options?.topK !== undefined) body.top_k = options.topK;
    if (options?.minScore !== undefined) body.min_score = options.minScore;
    if (options?.filter) body.filter = options.filter;

    return this.client.post<{ results: VectorSearchResult[]; total: number }>(
      `${VECTORS_BASE}/search`,
      body
    );
  }

  /**
   * Delete a vector by ID.
   */
  async delete(vectorId: string): Promise<void> {
    await this.client.delete(`${VECTORS_BASE}/${vectorId}`);
  }
}
