/**
 * Hedera MCP server tools — Jest tests
 * TDD Phase: RED → GREEN → REFACTOR
 *
 * Built by AINative Dev Team
 * Refs #268
 */

import { transferHbar } from '../src/tools/transfer-hbar';
import { createToken } from '../src/tools/create-token';
import { submitMessage } from '../src/tools/submit-message';
import { queryBalance } from '../src/tools/query-balance';
import { deployContract } from '../src/tools/deploy-contract';
import type {
  TransferHbarInput,
  TransferHbarOutput,
  CreateTokenInput,
  CreateTokenOutput,
  SubmitMessageInput,
  SubmitMessageOutput,
  QueryBalanceInput,
  QueryBalanceOutput,
  DeployContractInput,
  DeployContractOutput,
  HederaMCPToolError,
} from '../src/types';

// ---------------------------------------------------------------------------
// Shared mock factory
// ---------------------------------------------------------------------------

function makeMockFetch(response: object, status = 200): jest.Mock {
  return jest.fn().mockResolvedValue({
    ok: status >= 200 && status < 300,
    status,
    json: jest.fn().mockResolvedValue(response),
    text: jest.fn().mockResolvedValue(JSON.stringify(response)),
  });
}

// ---------------------------------------------------------------------------
// hedera_transfer_hbar
// ---------------------------------------------------------------------------

describe('transferHbar', () => {
  it('has the correct tool name', () => {
    expect(transferHbar.name).toBe('hedera_transfer_hbar');
  });

  it('has a non-empty description', () => {
    expect(transferHbar.description.length).toBeGreaterThan(10);
  });

  it('returns a transaction id on successful transfer', async () => {
    const mockFetch = makeMockFetch({ transaction_id: 'txn-abc-123' });
    const input: TransferHbarInput = {
      sender_account_id: '0.0.100',
      receiver_account_id: '0.0.200',
      amount_hbar: 1.5,
      memo: 'test transfer',
    };
    const result: TransferHbarOutput = await transferHbar.execute(input, { fetch: mockFetch });
    expect(result.transaction_id).toBe('txn-abc-123');
    expect(result.status).toBe('SUCCESS');
  });

  it('includes amount_hbar in the response', async () => {
    const mockFetch = makeMockFetch({ transaction_id: 'txn-xyz', amount_hbar: 2.0 });
    const input: TransferHbarInput = {
      sender_account_id: '0.0.100',
      receiver_account_id: '0.0.300',
      amount_hbar: 2.0,
    };
    const result: TransferHbarOutput = await transferHbar.execute(input, { fetch: mockFetch });
    expect(result.amount_hbar).toBe(2.0);
  });

  it('throws HederaMCPToolError when fetch fails', async () => {
    const mockFetch = makeMockFetch({ detail: 'Insufficient funds' }, 400);
    const input: TransferHbarInput = {
      sender_account_id: '0.0.100',
      receiver_account_id: '0.0.200',
      amount_hbar: 9999,
    };
    await expect(transferHbar.execute(input, { fetch: mockFetch })).rejects.toMatchObject({
      code: 'TRANSFER_FAILED',
    } as Partial<HederaMCPToolError>);
  });

  it('validates that amount_hbar must be positive', async () => {
    const input: TransferHbarInput = {
      sender_account_id: '0.0.100',
      receiver_account_id: '0.0.200',
      amount_hbar: -1,
    };
    await expect(
      transferHbar.execute(input, { fetch: jest.fn() })
    ).rejects.toMatchObject({ code: 'VALIDATION_ERROR' });
  });
});

// ---------------------------------------------------------------------------
// hedera_create_token
// ---------------------------------------------------------------------------

describe('createToken', () => {
  it('has the correct tool name', () => {
    expect(createToken.name).toBe('hedera_create_token');
  });

  it('has a non-empty description', () => {
    expect(createToken.description.length).toBeGreaterThan(10);
  });

  it('returns a token_id on successful fungible token creation', async () => {
    const mockFetch = makeMockFetch({ token_id: '0.0.999', token_type: 'FUNGIBLE_COMMON' });
    const input: CreateTokenInput = {
      name: 'AgentCoin',
      symbol: 'AGT',
      token_type: 'FUNGIBLE_COMMON',
      initial_supply: 1000000,
      decimals: 2,
      treasury_account_id: '0.0.100',
    };
    const result: CreateTokenOutput = await createToken.execute(input, { fetch: mockFetch });
    expect(result.token_id).toBe('0.0.999');
    expect(result.token_type).toBe('FUNGIBLE_COMMON');
  });

  it('returns a token_id on NFT creation', async () => {
    const mockFetch = makeMockFetch({ token_id: '0.0.888', token_type: 'NON_FUNGIBLE_UNIQUE' });
    const input: CreateTokenInput = {
      name: 'AgentNFT',
      symbol: 'ANFT',
      token_type: 'NON_FUNGIBLE_UNIQUE',
      initial_supply: 0,
      decimals: 0,
      treasury_account_id: '0.0.100',
    };
    const result: CreateTokenOutput = await createToken.execute(input, { fetch: mockFetch });
    expect(result.token_id).toBe('0.0.888');
  });

  it('throws HederaMCPToolError when creation fails', async () => {
    const mockFetch = makeMockFetch({ detail: 'Treasury not found' }, 404);
    const input: CreateTokenInput = {
      name: 'Fail',
      symbol: 'FAIL',
      token_type: 'FUNGIBLE_COMMON',
      initial_supply: 0,
      decimals: 0,
      treasury_account_id: '0.0.999999',
    };
    await expect(createToken.execute(input, { fetch: mockFetch })).rejects.toMatchObject({
      code: 'TOKEN_CREATION_FAILED',
    } as Partial<HederaMCPToolError>);
  });
});

// ---------------------------------------------------------------------------
// hedera_submit_message
// ---------------------------------------------------------------------------

describe('submitMessage', () => {
  it('has the correct tool name', () => {
    expect(submitMessage.name).toBe('hedera_submit_message');
  });

  it('has a non-empty description', () => {
    expect(submitMessage.description.length).toBeGreaterThan(10);
  });

  it('returns sequence_number and consensus_timestamp on success', async () => {
    const mockFetch = makeMockFetch({
      sequence_number: 42,
      consensus_timestamp: '2026-04-03T00:00:00.000Z',
      topic_id: '0.0.555',
    });
    const input: SubmitMessageInput = {
      topic_id: '0.0.555',
      message: 'audit event payload',
    };
    const result: SubmitMessageOutput = await submitMessage.execute(input, { fetch: mockFetch });
    expect(result.sequence_number).toBe(42);
    expect(result.topic_id).toBe('0.0.555');
    expect(result.consensus_timestamp).toBeDefined();
  });

  it('throws HederaMCPToolError when submission fails', async () => {
    const mockFetch = makeMockFetch({ detail: 'Topic not found' }, 404);
    const input: SubmitMessageInput = {
      topic_id: '0.0.000',
      message: 'test',
    };
    await expect(submitMessage.execute(input, { fetch: mockFetch })).rejects.toMatchObject({
      code: 'MESSAGE_SUBMIT_FAILED',
    } as Partial<HederaMCPToolError>);
  });

  it('validates that message must be non-empty', async () => {
    const input: SubmitMessageInput = { topic_id: '0.0.555', message: '' };
    await expect(
      submitMessage.execute(input, { fetch: jest.fn() })
    ).rejects.toMatchObject({ code: 'VALIDATION_ERROR' });
  });
});

// ---------------------------------------------------------------------------
// hedera_query_balance
// ---------------------------------------------------------------------------

describe('queryBalance', () => {
  it('has the correct tool name', () => {
    expect(queryBalance.name).toBe('hedera_query_balance');
  });

  it('has a non-empty description', () => {
    expect(queryBalance.description.length).toBeGreaterThan(10);
  });

  it('returns hbar_balance and token_balances on success', async () => {
    const mockFetch = makeMockFetch({
      account_id: '0.0.100',
      hbar_balance: 50.25,
      token_balances: [{ token_id: '0.0.456858', balance: 1000, decimals: 6 }],
    });
    const input: QueryBalanceInput = { account_id: '0.0.100' };
    const result: QueryBalanceOutput = await queryBalance.execute(input, { fetch: mockFetch });
    expect(result.account_id).toBe('0.0.100');
    expect(result.hbar_balance).toBe(50.25);
    expect(result.token_balances).toHaveLength(1);
    expect(result.token_balances[0].token_id).toBe('0.0.456858');
  });

  it('returns empty token_balances when account has no tokens', async () => {
    const mockFetch = makeMockFetch({
      account_id: '0.0.200',
      hbar_balance: 0,
      token_balances: [],
    });
    const input: QueryBalanceInput = { account_id: '0.0.200' };
    const result: QueryBalanceOutput = await queryBalance.execute(input, { fetch: mockFetch });
    expect(result.token_balances).toHaveLength(0);
  });

  it('throws HederaMCPToolError when account not found', async () => {
    const mockFetch = makeMockFetch({ detail: 'Account not found' }, 404);
    const input: QueryBalanceInput = { account_id: '0.0.9999999' };
    await expect(queryBalance.execute(input, { fetch: mockFetch })).rejects.toMatchObject({
      code: 'BALANCE_QUERY_FAILED',
    } as Partial<HederaMCPToolError>);
  });
});

// ---------------------------------------------------------------------------
// hedera_deploy_contract
// ---------------------------------------------------------------------------

describe('deployContract', () => {
  it('has the correct tool name', () => {
    expect(deployContract.name).toBe('hedera_deploy_contract');
  });

  it('has a non-empty description', () => {
    expect(deployContract.description.length).toBeGreaterThan(10);
  });

  it('returns contract_id on successful deployment', async () => {
    const mockFetch = makeMockFetch({
      contract_id: '0.0.12345',
      transaction_id: 'txn-deploy-001',
    });
    const input: DeployContractInput = {
      bytecode: '0x6080604052',
      gas: 100000,
      admin_account_id: '0.0.100',
    };
    const result: DeployContractOutput = await deployContract.execute(input, { fetch: mockFetch });
    expect(result.contract_id).toBe('0.0.12345');
    expect(result.transaction_id).toBe('txn-deploy-001');
  });

  it('throws HederaMCPToolError when deployment fails', async () => {
    const mockFetch = makeMockFetch({ detail: 'Invalid bytecode' }, 400);
    const input: DeployContractInput = {
      bytecode: 'not-valid-hex',
      gas: 1000,
      admin_account_id: '0.0.100',
    };
    await expect(deployContract.execute(input, { fetch: mockFetch })).rejects.toMatchObject({
      code: 'CONTRACT_DEPLOY_FAILED',
    } as Partial<HederaMCPToolError>);
  });

  it('validates that gas must be positive', async () => {
    const input: DeployContractInput = {
      bytecode: '0x6080',
      gas: 0,
      admin_account_id: '0.0.100',
    };
    await expect(
      deployContract.execute(input, { fetch: jest.fn() })
    ).rejects.toMatchObject({ code: 'VALIDATION_ERROR' });
  });
});
