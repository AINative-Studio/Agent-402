# Compare Embeddings Endpoint - Example Usage

## Endpoint

```
POST /v1/public/{project_id}/embeddings/compare
```

## Authentication

Requires `X-API-Key` header with a valid API key.

## Request Schema

```json
{
  "text1": "string (required)",
  "text2": "string (required)",
  "model": "string (optional, defaults to BAAI/bge-small-en-v1.5)"
}
```

## Response Schema

```json
{
  "text1": "string",
  "text2": "string",
  "embedding1": [float],
  "embedding2": [float],
  "cosine_similarity": float,
  "model": "string",
  "dimensions": integer,
  "processing_time_ms": integer
}
```

## Example Usage

### Python

```python
import requests

API_KEY = "your-api-key"
PROJECT_ID = "your-project-id"
BASE_URL = "http://localhost:8000"

headers = {
    "X-API-Key": API_KEY,
    "Content-Type": "application/json"
}

# Compare two texts
response = requests.post(
    f"{BASE_URL}/v1/public/{PROJECT_ID}/embeddings/compare",
    headers=headers,
    json={
        "text1": "Autonomous agent executing compliance check",
        "text2": "AI system performing regulatory verification"
    }
)

data = response.json()

print(f"Text 1: {data['text1']}")
print(f"Text 2: {data['text2']}")
print(f"Cosine Similarity: {data['cosine_similarity']:.4f}")
print(f"Model: {data['model']}")
print(f"Dimensions: {data['dimensions']}")
print(f"Processing Time: {data['processing_time_ms']}ms")
```

### cURL

```bash
curl -X POST "http://localhost:8000/v1/public/proj_abc123/embeddings/compare" \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "text1": "Autonomous agent executing compliance check",
    "text2": "AI system performing regulatory verification"
  }'
```

### JavaScript/TypeScript

```typescript
const API_KEY = "your-api-key";
const PROJECT_ID = "your-project-id";
const BASE_URL = "http://localhost:8000";

async function compareTexts(text1: string, text2: string) {
  const response = await fetch(
    `${BASE_URL}/v1/public/${PROJECT_ID}/embeddings/compare`,
    {
      method: "POST",
      headers: {
        "X-API-Key": API_KEY,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ text1, text2 }),
    }
  );

  const data = await response.json();

  console.log(`Similarity: ${data.cosine_similarity.toFixed(4)}`);
  console.log(`Model: ${data.model}`);

  return data;
}

// Example usage
compareTexts(
  "Autonomous agent executing compliance check",
  "AI system performing regulatory verification"
).then(console.log);
```

## Use Cases

### 1. Duplicate Detection

```python
# Check if two product descriptions are duplicates
similarity = compare_embeddings(
    "Premium wireless headphones with noise cancellation",
    "Wireless headphones with active noise cancelling - premium quality"
)

if similarity > 0.9:
    print("Likely duplicate")
elif similarity > 0.7:
    print("Very similar")
else:
    print("Different products")
```

### 2. Content Matching

```python
# Match user query to FAQ answers
user_query = "How do I reset my password?"
faq_answer = "To reset your password, click the forgot password link"

similarity = compare_embeddings(user_query, faq_answer)

if similarity > 0.8:
    print("This FAQ answers the user's question")
```

### 3. Semantic Search Relevance

```python
# Score document relevance to query
query = "machine learning algorithms"
document = "This article covers various AI and ML techniques"

similarity = compare_embeddings(query, document)

print(f"Relevance score: {similarity:.2f}")
```

## Cosine Similarity Interpretation

- **1.0**: Texts are semantically identical
- **0.8-0.99**: Very high similarity (paraphrases, near-duplicates)
- **0.6-0.79**: High similarity (related topics)
- **0.4-0.59**: Moderate similarity (some overlap)
- **0.2-0.39**: Low similarity (loosely related)
- **0.0-0.19**: Very low similarity (mostly unrelated)

## Supported Models

| Model | Dimensions | Description |
|-------|------------|-------------|
| BAAI/bge-small-en-v1.5 | 384 | Default - Fast and efficient |
| BAAI/bge-base-en-v1.5 | 768 | Balanced performance |
| BAAI/bge-large-en-v1.5 | 1024 | Highest quality |
| sentence-transformers/all-mpnet-base-v2 | 768 | General purpose |

## Error Handling

```python
try:
    response = requests.post(url, headers=headers, json=payload)
    response.raise_for_status()
    data = response.json()
except requests.exceptions.HTTPError as e:
    if response.status_code == 401:
        print("Invalid API key")
    elif response.status_code == 422:
        print("Validation error:", response.json())
    else:
        print(f"HTTP error: {e}")
except Exception as e:
    print(f"Error: {e}")
```

## Performance Tips

1. **Batch Comparisons**: If comparing many texts, consider caching embeddings
2. **Model Selection**: Use smaller models (384d) for faster processing
3. **Parallel Requests**: The endpoint is stateless and supports concurrent requests
4. **Caching**: Identical texts always produce identical embeddings (deterministic)

## Response Fields

| Field | Type | Description |
|-------|------|-------------|
| text1 | string | First input text (trimmed) |
| text2 | string | Second input text (trimmed) |
| embedding1 | array[float] | Embedding vector for text1 |
| embedding2 | array[float] | Embedding vector for text2 |
| cosine_similarity | float | Similarity score (0.0-1.0) |
| model | string | Model used for generation |
| dimensions | integer | Vector dimensionality |
| processing_time_ms | integer | Processing time in milliseconds |

## Notes

- Both embeddings are returned for transparency and potential reuse
- Processing time includes both embedding generations and similarity calculation
- Texts are automatically trimmed of leading/trailing whitespace
- Empty or whitespace-only texts are rejected with 422 error
- Results are deterministic - same inputs always produce same outputs
