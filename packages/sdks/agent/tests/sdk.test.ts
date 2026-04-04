/**
 * RED tests for AINativeSDK entry point
 * Built by AINative Dev Team
 * Refs #178 #179 #180
 */

import { AINativeSDK } from '../src/index';
import { AgentsModule } from '../src/agents';
import { MemoryModule } from '../src/memory';
import { VectorsModule } from '../src/vectors';
import { FilesModule } from '../src/files';

describe('AINativeSDK', () => {
  describe('constructor', () => {
    it('should create an SDK instance with apiKey', () => {
      const sdk = new AINativeSDK({ apiKey: 'test-api-key' });
      expect(sdk).toBeInstanceOf(AINativeSDK);
    });

    it('should create an SDK instance with jwt', () => {
      const sdk = new AINativeSDK({ jwt: 'my.jwt.token' });
      expect(sdk).toBeInstanceOf(AINativeSDK);
    });

    it('should throw when no auth credentials provided', () => {
      expect(() => new AINativeSDK({})).toThrow();
    });
  });

  describe('modules', () => {
    let sdk: AINativeSDK;

    beforeEach(() => {
      sdk = new AINativeSDK({ apiKey: 'test-key' });
    });

    it('should expose agents module', () => {
      expect(sdk.agents).toBeInstanceOf(AgentsModule);
    });

    it('should expose memory module', () => {
      expect(sdk.memory).toBeInstanceOf(MemoryModule);
    });

    it('should expose vectors module', () => {
      expect(sdk.vectors).toBeInstanceOf(VectorsModule);
    });

    it('should expose files module', () => {
      expect(sdk.files).toBeInstanceOf(FilesModule);
    });

    it('should expose agents.tasks sub-module', () => {
      expect(sdk.agents.tasks).toBeDefined();
      expect(typeof sdk.agents.tasks.create).toBe('function');
      expect(typeof sdk.agents.tasks.get).toBe('function');
      expect(typeof sdk.agents.tasks.list).toBe('function');
    });

    it('should expose memory.graph sub-module', () => {
      expect(sdk.memory.graph).toBeDefined();
      expect(typeof sdk.memory.graph.traverse).toBe('function');
      expect(typeof sdk.memory.graph.addEntity).toBe('function');
      expect(typeof sdk.memory.graph.addEdge).toBe('function');
      expect(typeof sdk.memory.graph.graphrag).toBe('function');
    });
  });

  describe('configuration', () => {
    it('should use custom baseUrl when provided', () => {
      const sdk = new AINativeSDK({
        apiKey: 'key',
        baseUrl: 'https://custom.api.com/v2',
      });
      expect(sdk).toBeInstanceOf(AINativeSDK);
    });

    it('should use default baseUrl when not provided', () => {
      const sdk = new AINativeSDK({ apiKey: 'key' });
      expect(sdk).toBeInstanceOf(AINativeSDK);
    });
  });
});
