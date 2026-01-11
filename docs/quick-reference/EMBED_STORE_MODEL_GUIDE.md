# Embed & Store Model Quick Reference

**Print this page or bookmark it for quick reference**

---

## The Rule

```
+-----------------------------------------------+
|                                               |
|   Store with Model X  -->  Search with Model X |
|                                               |
|   NEVER mix different models in same namespace |
|                                               |
+-----------------------------------------------+
```

---

## Supported Models

| Model | Dims | Speed | Best For |
|-------|------|-------|----------|
| **BAAI/bge-small-en-v1.5** | 384 | Fast | Default, general use |
| all-MiniLM-L6-v2 | 384 | Fast | Lightweight apps |
| all-MiniLM-L12-v2 | 384 | Med | Balanced |
| all-mpnet-base-v2 | 768 | Slow | High quality |
| paraphrase-multilingual-MiniLM-L12-v2 | 384 | Med | Multi-language |
| all-distilroberta-v1 | 768 | Slow | Robust |
| msmarco-distilbert-base-v4 | 768 | Slow | Search-optimized |

**Note:** Use `sentence-transformers/` prefix for all models except BAAI.

---

## Quick Copy-Paste Code

### Python Setup

```python
# config.py
EMBEDDING_MODEL = "BAAI/bge-small-en-v1.5"
NAMESPACE = "my_namespace"
```

### Store Documents

```python
requests.post(
    f"{BASE_URL}/v1/public/{PROJECT_ID}/embeddings/embed-and-store",
    headers={"X-API-Key": API_KEY},
    json={
        "documents": [{"id": "doc1", "text": "..."}],
        "model": EMBEDDING_MODEL,
        "namespace": NAMESPACE
    }
)
```

### Search Documents

```python
requests.post(
    f"{BASE_URL}/v1/public/{PROJECT_ID}/embeddings/search",
    headers={"X-API-Key": API_KEY},
    json={
        "query": "search query",
        "model": EMBEDDING_MODEL,  # SAME model
        "namespace": NAMESPACE     # SAME namespace
    }
)
```

### curl Store

```bash
curl -X POST "${BASE_URL}/v1/public/${PROJECT_ID}/embeddings/embed-and-store" \
  -H "X-API-Key: ${API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "documents": [{"id": "doc1", "text": "my document"}],
    "model": "BAAI/bge-small-en-v1.5",
    "namespace": "my_namespace"
  }'
```

### curl Search

```bash
curl -X POST "${BASE_URL}/v1/public/${PROJECT_ID}/embeddings/search" \
  -H "X-API-Key: ${API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "search query",
    "model": "BAAI/bge-small-en-v1.5",
    "namespace": "my_namespace"
  }'
```

---

## Common Errors

### DIMENSION_MISMATCH

**Error:**
```json
{"detail": "Vector dimension mismatch. Expected 384, got 768"}
```

**Fix:** Use same model for search as you used for store.

```python
# Wrong: different dimensions
store(..., model="BAAI/bge-small-en-v1.5")      # 384
search(..., model="all-mpnet-base-v2")          # 768

# Right: same model
store(..., model="BAAI/bge-small-en-v1.5")
search(..., model="BAAI/bge-small-en-v1.5")
```

### No Results Found

**Possible causes:**
1. Wrong namespace
2. Different model (even if same dimensions)
3. Similarity threshold too high

**Fixes:**
```python
# Check namespace matches
store(..., namespace="agent_memory")
search(..., namespace="agent_memory")  # Must match

# Check model matches exactly
store(..., model="BAAI/bge-small-en-v1.5")
search(..., model="BAAI/bge-small-en-v1.5")  # Exact match

# Lower threshold
search(..., similarity_threshold=0.5)  # More lenient
```

### MODEL_NOT_FOUND

**Fix:** Check spelling of model name.

```python
# Wrong
"BAAI/bge-small-v1.5"        # Missing 'en'
"bge-small-en-v1.5"          # Missing 'BAAI/'
"BAAI/bge-small-en-v1.5 "    # Extra space

# Right
"BAAI/bge-small-en-v1.5"
```

---

## Warning Signs

**WARNING: Model Mismatch**

You are mixing models if:

| Store Model | Search Model | Result |
|------------|--------------|--------|
| Model A (384) | Model B (768) | ERROR |
| Model A (384) | Model C (384) | Poor results |
| Model A (768) | Model A (768) | SUCCESS |

Even models with the same dimensions encode text differently.

---

## Do's and Don'ts

| DO | DON'T |
|----|-------|
| Define model as constant | Hard-code model strings |
| Same model for store and search | Mix models in namespace |
| Specify model explicitly | Rely on defaults |
| One namespace per model | Change models mid-project |
| Test model consistency | Assume interchangeability |

---

## Troubleshooting Checklist

When search fails:

1. [ ] Same model for store and search?
2. [ ] Same namespace for store and search?
3. [ ] Model name spelled correctly?
4. [ ] Documents exist in namespace?
5. [ ] Similarity threshold reasonable?
6. [ ] Metadata filters not too strict?

---

## Multiple Models Strategy

If you need multiple models, use separate namespaces:

```python
CONFIGS = {
    "fast": {
        "model": "BAAI/bge-small-en-v1.5",
        "namespace": "data_384"
    },
    "quality": {
        "model": "sentence-transformers/all-mpnet-base-v2",
        "namespace": "data_768"
    }
}

# Use consistently
cfg = CONFIGS["fast"]
store(..., model=cfg["model"], namespace=cfg["namespace"])
search(..., model=cfg["model"], namespace=cfg["namespace"])
```

---

## Related Docs

- [Full Model Consistency Guide](/docs/api/MODEL_CONSISTENCY_GUIDE.md)
- [Embed-Store Consistency](/docs/api/MODEL_CONSISTENCY_EMBED_STORE.md)
- [Embed and Store API](/docs/api/EMBED_AND_STORE_API.md)
- [Embeddings Store Search Spec](/docs/api/embeddings-store-search-spec.md)

---

**Remember: Same Model + Same Namespace = Successful Search**

---

Built by AINative Dev Team
