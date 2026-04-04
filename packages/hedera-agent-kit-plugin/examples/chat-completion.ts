/**
 * Example: Using AINative chat completion tools in a Hedera agent
 * Built by AINative Dev Team
 * Refs #184, #186
 */

import { getAINativeTools } from '../src/index';

async function main() {
  const tools = getAINativeTools({
    apiKey: process.env.AINATIVE_API_KEY ?? '',
  });

  const chatTool = tools.find((t) => t.name === 'ainative_chat')!;

  // Chat with Anthropic Claude (default)
  const claudeResult = await chatTool.invoke({
    messages: [
      { role: 'system', content: 'You are a Hedera blockchain assistant.' },
      { role: 'user', content: 'What is HBAR?' },
    ],
    provider: 'anthropic',
    temperature: 0.7,
  });
  console.log('Claude:', claudeResult);

  // Chat with OpenAI GPT
  const gptResult = await chatTool.invoke({
    messages: [
      { role: 'user', content: 'Explain Hedera Hashgraph consensus in one sentence.' },
    ],
    provider: 'openai',
    model: 'gpt-4o-mini',
    max_tokens: 100,
  });
  console.log('GPT:', gptResult);

  // Chat with Google Gemini
  const geminiResult = await chatTool.invoke({
    messages: [
      { role: 'user', content: 'List three Hedera smart contract use cases.' },
    ],
    provider: 'google',
  });
  console.log('Gemini:', geminiResult);

  // Chat with Meta Llama
  const llamaResult = await chatTool.invoke({
    messages: [
      { role: 'user', content: 'What makes Hedera different from Ethereum?' },
    ],
    provider: 'meta',
  });
  console.log('Llama:', llamaResult);
}

main().catch(console.error);
