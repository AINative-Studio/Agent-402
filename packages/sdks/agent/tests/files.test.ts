/**
 * RED tests for File operations
 * Built by AINative Dev Team
 * Refs #180
 */

import { FilesModule } from '../src/files';
import { HttpClient } from '../src/client';
import type {
  StoredFile,
  FileUploadOptions,
  FileListOptions,
  FileListResponse,
} from '../src/types';

jest.mock('../src/client');

function makeFile(overrides: Partial<StoredFile> = {}): StoredFile {
  return {
    id: 'file_abc123456789',
    name: 'document.pdf',
    size: 1024,
    contentType: 'application/pdf',
    namespace: 'default',
    url: 'https://storage.ainative.studio/files/file_abc123456789',
    metadata: {},
    createdAt: '2024-01-01T00:00:00Z',
    updatedAt: '2024-01-01T00:00:00Z',
    ...overrides,
  };
}

describe('FilesModule', () => {
  let mockClient: jest.Mocked<HttpClient>;
  let filesModule: FilesModule;

  beforeEach(() => {
    mockClient = {
      get: jest.fn(),
      post: jest.fn(),
      patch: jest.fn(),
      delete: jest.fn(),
      postFormData: jest.fn(),
      baseUrl: 'https://api.ainative.studio/v1',
      timeout: 30000,
    } as unknown as jest.Mocked<HttpClient>;

    filesModule = new FilesModule(mockClient);
  });

  // ─── files.upload ─────────────────────────────────────────────────────────

  describe('upload', () => {
    it('should POST file data to /api/v1/public/files/', async () => {
      const file = new Blob(['file content'], { type: 'text/plain' });
      const expected = makeFile({ name: 'test.txt', contentType: 'text/plain' });
      mockClient.postFormData.mockResolvedValueOnce(expected);

      const result = await filesModule.upload(file, { contentType: 'text/plain' });

      expect(mockClient.postFormData).toHaveBeenCalledWith(
        '/api/v1/public/files/',
        expect.any(FormData)
      );
      expect(result).toEqual(expected);
    });

    it('should return a StoredFile with id and url', async () => {
      const file = new Blob(['data'], { type: 'application/json' });
      const expected = makeFile({ id: 'file_new001', url: 'https://storage.example.com/file_new001' });
      mockClient.postFormData.mockResolvedValueOnce(expected);

      const result = await filesModule.upload(file);

      expect(result.id).toBe('file_new001');
      expect(result.url).toBeTruthy();
    });

    it('should include namespace in FormData when provided', async () => {
      const file = new Blob(['content'], { type: 'text/plain' });
      const options: FileUploadOptions = { namespace: 'docs-ns' };
      mockClient.postFormData.mockResolvedValueOnce(makeFile({ namespace: 'docs-ns' }));

      await filesModule.upload(file, options);

      const formDataArg = (mockClient.postFormData as jest.Mock).mock.calls[0][1] as FormData;
      expect(formDataArg.get('namespace')).toBe('docs-ns');
    });

    it('should include metadata in FormData when provided', async () => {
      const file = new Blob(['content']);
      const options: FileUploadOptions = { metadata: { category: 'reports' } };
      mockClient.postFormData.mockResolvedValueOnce(makeFile());

      await filesModule.upload(file, options);

      const formDataArg = (mockClient.postFormData as jest.Mock).mock.calls[0][1] as FormData;
      const metadataStr = formDataArg.get('metadata') as string;
      expect(JSON.parse(metadataStr)).toEqual({ category: 'reports' });
    });
  });

  // ─── files.download ───────────────────────────────────────────────────────

  describe('download', () => {
    it('should GET /api/v1/public/files/:fileId', async () => {
      const blobData = new Blob(['file content']);
      mockClient.get.mockResolvedValueOnce(blobData);

      const result = await filesModule.download('file_abc123456789');

      expect(mockClient.get).toHaveBeenCalledWith(
        '/api/v1/public/files/file_abc123456789'
      );
      expect(result).toEqual(blobData);
    });

    it('should return the file data as a Blob', async () => {
      const blobData = new Blob(['binary data'], { type: 'application/octet-stream' });
      mockClient.get.mockResolvedValueOnce(blobData);

      const result = await filesModule.download('file_xyz');

      expect(result).toBeInstanceOf(Blob);
    });
  });

  // ─── files.list ───────────────────────────────────────────────────────────

  describe('list', () => {
    it('should GET /api/v1/public/files/', async () => {
      const response: FileListResponse = {
        files: [makeFile()],
        total: 1,
        limit: 100,
        offset: 0,
      };
      mockClient.get.mockResolvedValueOnce(response);

      const result = await filesModule.list();

      expect(mockClient.get).toHaveBeenCalledWith('/api/v1/public/files/');
      expect(result).toEqual(response);
    });

    it('should append namespace query param when provided', async () => {
      const options: FileListOptions = { namespace: 'docs-ns' };
      const response: FileListResponse = { files: [], total: 0, limit: 100, offset: 0 };
      mockClient.get.mockResolvedValueOnce(response);

      await filesModule.list(options);

      expect(mockClient.get).toHaveBeenCalledWith(
        expect.stringContaining('namespace=docs-ns')
      );
    });

    it('should append limit and offset query params when provided', async () => {
      const options: FileListOptions = { limit: 25, offset: 50 };
      const response: FileListResponse = { files: [], total: 0, limit: 25, offset: 50 };
      mockClient.get.mockResolvedValueOnce(response);

      await filesModule.list(options);

      const calledUrl = (mockClient.get as jest.Mock).mock.calls[0][0] as string;
      expect(calledUrl).toContain('limit=25');
      expect(calledUrl).toContain('offset=50');
    });

    it('should return a list of stored files', async () => {
      const files = [makeFile({ id: 'file_1' }), makeFile({ id: 'file_2' })];
      const response: FileListResponse = { files, total: 2, limit: 100, offset: 0 };
      mockClient.get.mockResolvedValueOnce(response);

      const result = await filesModule.list();

      expect(result.files).toHaveLength(2);
      expect(result.total).toBe(2);
    });
  });
});
