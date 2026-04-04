/**
 * @ainative/agent-sdk — File operations
 * Built by AINative Dev Team
 * Refs #180
 */

import type { HttpClient } from './client';
import type {
  StoredFile,
  FileUploadOptions,
  FileListOptions,
  FileListResponse,
} from './types';

const FILES_BASE = '/api/v1/public/files';

export class FilesModule {
  constructor(private readonly client: HttpClient) {}

  /**
   * Upload a file. Accepts a Blob or File object.
   */
  async upload(file: Blob | File, options?: FileUploadOptions): Promise<StoredFile> {
    const formData = new FormData();
    formData.append('file', file);

    if (options?.namespace) {
      formData.append('namespace', options.namespace);
    }
    if (options?.contentType) {
      formData.append('content_type', options.contentType);
    }
    if (options?.metadata) {
      formData.append('metadata', JSON.stringify(options.metadata));
    }

    return this.client.postFormData<StoredFile>(`${FILES_BASE}/`, formData);
  }

  /**
   * Download a file by ID. Returns raw Blob data.
   */
  async download(fileId: string): Promise<Blob> {
    return this.client.get<Blob>(`${FILES_BASE}/${fileId}`);
  }

  /**
   * List stored files with optional filters.
   */
  async list(options?: FileListOptions): Promise<FileListResponse> {
    const params = new URLSearchParams();

    if (options?.namespace) params.set('namespace', options.namespace);
    if (options?.limit !== undefined) params.set('limit', String(options.limit));
    if (options?.offset !== undefined) params.set('offset', String(options.offset));

    const qs = params.toString();
    const path = qs ? `${FILES_BASE}/?${qs}` : `${FILES_BASE}/`;
    return this.client.get<FileListResponse>(path);
  }
}
