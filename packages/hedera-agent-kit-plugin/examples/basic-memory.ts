/**
 * Example: Using AINative memory tools in a Hedera agent
 * Built by AINative Dev Team
 * Refs #183, #186
 */

import { getAINativeTools } from '../src/index';

async function main() {
  const tools = getAINativeTools({
    apiKey: process.env.AINATIVE_API_KEY ?? '',
    agentId: 'my-hedera-agent',
  });

  const rememberTool = tools.find((t) => t.name === 'ainative_remember')!;
  const recallTool = tools.find((t) => t.name === 'ainative_recall')!;
  const forgetTool = tools.find((t) => t.name === 'ainative_forget')!;
  const reflectTool = tools.find((t) => t.name === 'ainative_reflect')!;

  // Store a memory
  const storeResult = await rememberTool.invoke({
    content: 'User prefers Hedera mainnet over testnet.',
    agent_id: 'hedera-assistant',
    metadata: { network: 'mainnet', priority: 'high' },
  });
  console.log('Stored:', storeResult);

  // Recall relevant memories
  const recallResult = await recallTool.invoke({
    query: 'Which Hedera network does the user prefer?',
    agent_id: 'hedera-assistant',
    limit: 5,
  });
  console.log('Recalled:', recallResult);

  // Reflect on agent context
  const reflectResult = await reflectTool.invoke({
    agent_id: 'hedera-assistant',
    topic: 'network preferences',
  });
  console.log('Reflected:', reflectResult);

  // Forget a specific memory (use the ID from storeResult)
  // const forgetResult = await forgetTool.invoke({ id: 'mem-abc123' });
  // console.log('Forgotten:', forgetResult);
}

main().catch(console.error);
