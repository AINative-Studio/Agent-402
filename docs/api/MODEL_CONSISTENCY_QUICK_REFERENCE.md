# Model Consistency Quick Reference Card

**Print this page or bookmark it for quick reference**

---

## The Golden Rule

```
┌───────────────────────────────────────┐
│                                       │
│  Store with Model X                   │
│         ↓                             │
│  Search with Model X                  │
│                                       │
│  ALWAYS USE THE SAME MODEL            │
│                                       │
└───────────────────────────────────────┘
```

---

## Quick Setup (Copy-Paste)

```python
# 1. Define model as constant
EMBEDDING_MODEL = "BAAI/bge-small-en-v1.5"
NAMESPACE = "my_namespace"

# 2. Store documents
import requests

requests.post(
    f"{BASE_URL}/v1/public/{PROJECT_ID}/embeddings/embed-and-store",
    headers={"X-API-Key": API_KEY},
    json={
        "documents": [{"id": "doc1", "text": "..."}],
        "model": EMBEDDING_MODEL,  # ← Use constant
        "namespace": NAMESPACE
    }
)

# 3. Search documents
requests.post(
    f"{BASE_URL}/v1/public/{PROJECT_ID}/embeddings/search",
    headers={"X-API-Key": API_KEY},
    json={
        "query": "...",
        "model": EMBEDDING_MODEL,  # ← Same constant
        "namespace": NAMESPACE      # ← Same namespace
    }
)
```

---

## Common Errors & Fixes

### Error: DIMENSION_MISMATCH

**Fix:** Use same model for search as you used for store

```python
# ❌ This caused error:
store(..., model="BAAI/bge-small-en-v1.5")     # 384 dims
search(..., model="all-mpnet-base-v2")         # 768 dims

# ✅ Fix:
search(..., model="BAAI/bge-small-en-v1.5")    # 384 dims
```

### Error: No Results Found

**Fix 1:** Check namespace matches
```python
# ❌ Wrong namespace
store(..., namespace="agent_memory")
search(..., namespace="compliance")  # Different!

# ✅ Fix
search(..., namespace="agent_memory")
```

**Fix 2:** Check model matches
```python
# ❌ Different model
store(..., model="BAAI/bge-small-en-v1.5")
search(..., model="all-MiniLM-L6-v2")  # Different!

# ✅ Fix
search(..., model="BAAI/bge-small-en-v1.5")
```

**Fix 3:** Lower similarity threshold
```python
# ❌ Too strict
search(..., similarity_threshold=0.95)

# ✅ More lenient
search(..., similarity_threshold=0.7)
```

---

## Do's and Don'ts

| ✅ DO | ❌ DON'T |
|-------|----------|
| Define model as constant | Hard-code model strings |
| Use same model for store & search | Mix models in same namespace |
| Specify model explicitly | Rely on defaults without documenting |
| Use namespace per model | Change models mid-project |
| Test model consistency | Assume models are interchangeable |

---

## Supported Models Reference

| Model | Dimensions | Use Case |
|-------|------------|----------|
| **BAAI/bge-small-en-v1.5** (default) | 384 | General purpose, fast |
| sentence-transformers/all-MiniLM-L6-v2 | 384 | Fast, efficient |
| sentence-transformers/all-mpnet-base-v2 | 768 | High quality |
| sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2 | 384 | Multi-lingual |

**List all models:**
```bash
curl -X GET "${BASE_URL}/v1/public/embeddings/models" \
  -H "X-API-Key: ${API_KEY}"
```

---

## Troubleshooting Checklist

When search isn't working:

1. ☐ Same model for store and search?
2. ☐ Same namespace for store and search?
3. ☐ Model name spelled correctly (no typos)?
4. ☐ Documents actually exist in namespace?
5. ☐ Similarity threshold not too high?
6. ☐ Metadata filter not too restrictive?

---

## Need More Help?

- **Comprehensive Guide:** [/docs/api/MODEL_CONSISTENCY_GUIDE.md](/docs/api/MODEL_CONSISTENCY_GUIDE.md)
- **Full API Spec:** [/docs/api/embeddings-store-search-spec.md](/docs/api/embeddings-store-search-spec.md)
- **DX Contract:** [/DX-Contract.md](/DX-Contract.md)

---

**Remember: Same Model + Same Namespace = Successful Search** 🎯
