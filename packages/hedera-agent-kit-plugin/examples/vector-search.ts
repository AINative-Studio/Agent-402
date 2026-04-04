/**
 * Example: Using AINative vector tools in a Hedera agent
 * Built by AINative Dev Team
 * Refs #185, #186
 */

import { getAINativeTools } from '../src/index';

// Simulate an embedding model output (384 dimensions)
function fakeEmbed(text: string): number[] {
  const vec = new Array(384).fill(0).map((_, i) => Math.sin(i + text.length));
  return vec;
}

async function main() {
  const tools = getAINativeTools({
    apiKey: process.env.AINATIVE_API_KEY ?? '',
  });

  const upsertTool = tools.find((t) => t.name === 'ainative_vector_upsert')!;
  const searchTool = tools.find((t) => t.name === 'ainative_vector_search')!;
  const deleteTool = tools.find((t) => t.name === 'ainative_vector_delete')!;

  // Hedera account ID as namespace for isolation
  const hederaAccountId = '0.0.1234567';

  // Store vectors scoped to a Hedera account
  const upsertResult = await upsertTool.invoke({
    vector: fakeEmbed('Hedera HBAR staking rewards'),
    metadata: { topic: 'staking', source: 'docs' },
    namespace: hederaAccountId,
  });
  console.log('Upserted:', upsertResult);

  // Search for similar vectors within the account namespace
  const searchResult = await searchTool.invoke({
    vector: fakeEmbed('how to earn HBAR'),
    top_k: 5,
    namespace: hederaAccountId,
  });
  console.log('Search results:', searchResult);

  // Delete a vector by ID
  // const deleteResult = await deleteTool.invoke({
  //   id: 'vec-abc123',
  //   namespace: hederaAccountId,
  // });
  // console.log('Deleted:', deleteResult);
}

main().catch(console.error);
