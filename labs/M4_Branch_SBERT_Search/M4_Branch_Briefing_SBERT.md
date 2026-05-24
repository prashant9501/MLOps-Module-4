# Module 4 Branch Project: SBERT News Search Relevancy

## Instructor Briefing Document

**Type:** Take-Home Assignment (Branch Project)
**Estimated Student Effort:** 4-6 hours
**Prerequisites:** Module 3 (ML pipeline basics), Module 4 spine labs (Docker fundamentals)
**Deliverable:** Containerized semantic search API running on localhost:5001

---

## 1. Business Problem

**Scenario:** NewsWire India, a news aggregation startup based in Pune, has a corpus of
12,972 deduplicated news articles across 13 categories and 271 subcategories. Their
current keyword search fails when users phrase queries differently from article titles --
for example, searching "carbon footprint of factories" returns nothing even though
articles about "industrial emissions and climate impact" exist in the corpus.

**The ask:** Build a semantic search API that understands meaning, not just keywords.
Given a natural-language query, return the top-k most relevant articles ranked by
cosine similarity. The API must be containerized with Docker so it can be deployed to
any environment without dependency headaches.

**Why this matters for MLOps learners:** Embedding-based retrieval is the backbone of
modern search, recommendation systems, and Retrieval-Augmented Generation (RAG)
pipelines. Containerizing an NLP inference service is a real-world skill that maps
directly to the spine project's Docker work but introduces a different ML domain
(dense vector search vs. tabular classification).

---

## 2. How SBERT Works (High-Level)

SBERT (Sentence-BERT) produces fixed-size vector representations of text. The model
used here is `all-MiniLM-L6-v2`, which maps any text input to a 384-dimensional
dense vector.

**The embedding pipeline:**

```
Input text
   |
   v
Preprocessing (lowercase, remove punctuation, remove stopwords, lemmatize)
   |
   v
SBERT Transformer (all-MiniLM-L6-v2)
   |
   v
384-dimensional embedding vector
```

**Key intuition for students:** Two texts that mean similar things will have vectors
that point in similar directions. Cosine similarity between their vectors will be
close to 1.0. Unrelated texts will have cosine similarity close to 0.0.

**Why SBERT over plain BERT?** Standard BERT requires passing both sentences through
the network simultaneously (cross-encoder), which is O(n^2) for comparing against a
corpus. SBERT generates independent embeddings (bi-encoder), so we compute each
article's embedding once during indexing, then only compute the query embedding at
search time. This makes search over 12,972 articles near-instantaneous.

---

## 3. System Architecture

```
                         SBERT News Search Architecture
                         ==============================

  Client (curl / Postman / Python requests)
       |
       | POST /search  {"query": ["carbon emissions"], "k": 5}
       v
  +------------------+
  |  Flask API       |    port 5001
  |  (server.py)     |
  +------------------+
       |
       | 1. Validate request
       | 2. Preprocess query text
       v
  +------------------+
  |  Preprocessor    |    lowercase -> remove non-alphanumeric -> 
  |  (preprocessor)  |    remove stopwords -> lemmatize (spaCy)
  +------------------+
       |
       v
  +------------------+
  |  SBERT Embedder  |    all-MiniLM-L6-v2 -> 384-dim vector
  |  (embeddings)    |
  +------------------+
       |
       v
  +------------------+
  |  Annoy Index     |    50 trees, euclidean metric
  |  (build_index)   |    Approximate Nearest Neighbors
  +------------------+
       |
       | Returns k nearest article IDs + distances
       v
  +------------------+
  |  Relevance       |    Cosine similarity >= 0.4 threshold
  |  Scoring         |    Filters out low-quality matches
  +------------------+
       |
       v
  JSON response with article_id, score, title, category
```

**Health check:** `GET /ping` returns `{"status": "healthy", "timestamp": "..."}`

---

## 4. Dataset Summary

| Attribute          | Value                                      |
|--------------------|--------------------------------------------|
| Total articles     | 12,972 (after deduplication)               |
| Categories         | 13 (business, sports, technology, etc.)    |
| Subcategories      | 271                                        |
| Fields per article | article_id, title, text, category, subcategory |
| Index built on     | Article titles only (not full text)        |
| Source format      | CSV (raw.csv)                              |

**Note:** The pre-built Annoy index and associated JSON files are provided to students.
They do NOT need to run the training pipeline -- only the inference (search) pipeline.

---

## 5. Pre-Built Artifacts (Provided to Students)

Students receive these files and must place them in the correct directories:

| File                          | Location          | Size   | Purpose                            |
|-------------------------------|-------------------|--------|------------------------------------|
| `None_title.annoy`           | `models/`         | ~28 MB | Pre-built Annoy index (50 trees)   |
| `None_title_ids.json`        | `models/`         | ~1 MB  | Section-to-article ID mappings     |
| `None_title_stats.json`      | `models/`         | <1 KB  | Section statistics (mean, std)     |
| `None_title_processed.csv`   | `data/processed/` | ~2 MB  | Preprocessed article titles        |
| `raw.csv`                    | `data/raw/`       | ~50 MB | Original news articles dataset     |

**The naming convention** `None_title` comes from the config: `TEXT_SECTION_TYPE=None`
and `TRAIN_DATA_INPUT_TYPES=["title"]`, which means the index was built on whole
article titles (not sectioned into paragraphs or sentences).

---

## 6. What Students Build (Take-Home Tasks)

Students receive a `starter/` folder with:
- Complete `src/` modules (config, preprocessor, embeddings, build_index, search)
- A skeleton `server_starter.py` with 8 TODOs
- A partial `Dockerfile.starter` with 4 TODOs
- A partial `docker-compose.starter.yml` with 2 TODOs
- A complete `requirements.txt`

**Their tasks:**

1. **Complete `server.py`** -- Fill in the 8 TODOs to create a working Flask API:
   - Load model artifacts (Annoy index, ID mappings, statistics)
   - Implement the `/ping` health check endpoint
   - Implement the `/search` endpoint (parse JSON, validate, call search, return results)

2. **Complete `Dockerfile`** -- Fill in 4 TODOs:
   - Copy and install requirements
   - Copy source code
   - Expose port 5001
   - Set the startup command

3. **Complete `docker-compose.yml`** -- Fill in 2 TODOs:
   - Port mapping
   - Volume mount for development

4. **Test the system:**
   - Build and run: `docker compose up --build`
   - Health check: `curl http://localhost:5001/ping`
   - Search: `curl -X POST http://localhost:5001/search -H "Content-Type: application/json" -d '{"query": ["carbon emissions"], "k": 5}'`

---

## 7. Tools and Libraries

| Tool/Library            | Version    | Purpose                                   |
|-------------------------|------------|-------------------------------------------|
| Python                  | 3.12.10    | Runtime                                   |
| Flask                   | 3.0.2      | Web framework for the API                 |
| sentence-transformers   | 3.0.1      | SBERT model loading and inference         |
| annoy                   | 1.17.3     | Approximate Nearest Neighbors index       |
| spaCy                   | 3.7.4      | Tokenization and lemmatization            |
| NLTK                    | 3.8.1      | Stopword list (combined with spaCy)       |
| Docker                  | latest     | Containerization                          |
| Docker Compose          | v2         | Multi-service orchestration               |

**spaCy model:** `en_core_web_sm` -- must be downloaded inside the container
(handled in requirements or Dockerfile).

---

## 8. Key Configuration Parameters

| Parameter                        | Value              | Meaning                             |
|----------------------------------|--------------------|-------------------------------------|
| `SENTENCE_TRANSFORMER_MODEL_TYPE`| `all-MiniLM-L6-v2` | SBERT model (384-dim embeddings)   |
| `ANNOY_N_TREES`                  | `50`               | More trees = better accuracy, slower build |
| `ANNOY_METRIC`                   | `euclidean`        | Distance metric for the index      |
| `ANNOY_SIZE`                     | `384`              | Embedding dimension (must match model) |
| `RELEVANCE_SCORE_THRESHOLD`      | `0.4`              | Cosine similarity cutoff           |
| `RELEVANCE_SCORE_ROUNDING`       | `2`                | Decimal places for scores          |
| `TEXT_SECTION_TYPE`              | `None`             | Index entire titles (no sectioning) |
| `TRAIN_DATA_INPUT_TYPES`        | `["title"]`        | Index built on titles only         |

---

## 9. Contrast with the Spine Project

| Aspect              | Spine (Truck Delay)              | Branch (SBERT Search)            |
|---------------------|----------------------------------|----------------------------------|
| ML task             | Tabular binary classification    | Dense vector retrieval (NLP)     |
| Input data          | Structured (routes, weather)     | Unstructured (text articles)     |
| Model type          | Gradient boosting / logistic     | Transformer (SBERT)              |
| Inference pattern   | Single prediction per request    | Top-k ranked results per query   |
| Index structure     | None (direct model inference)    | Annoy approximate nearest neighbor |
| Docker complexity   | Model + API                      | Model + Index + Preprocessing    |
| Key new concept     | Containerizing ML serving        | Embedding search + containerization |

**Pedagogical intent:** Students see that Docker containerization applies equally to
NLP workloads and tabular ML. The Dockerfile/docker-compose patterns are nearly
identical, reinforcing transferable skills.

---

## 10. Common Student Issues and Instructor Tips

### Issue 1: "Model download takes forever during docker build"
The SBERT model (~90 MB) downloads from HuggingFace on first import. In Docker, this
happens every build unless cached. **Tip:** The model gets cached in the Docker layer
after the first build. Advise students to be patient on the first build (~5-10 minutes).

### Issue 2: "spaCy model not found"
The `en_core_web_sm` model must be installed. It is listed in requirements.txt via the
direct URL. If this fails, students can add `RUN python -m spacy download en_core_web_sm`
to their Dockerfile after the pip install step.

### Issue 3: "Annoy index file not found"
Students forget to copy model artifacts into the `models/` directory. Remind them to
check the README_DATA.md file and copy the files from the course materials.

### Issue 4: "JSON decode error on /search"
Students forget to set `Content-Type: application/json` header in curl. Remind them the
search endpoint expects a JSON body, not form data.

### Issue 5: "Port already in use"
If students ran the server locally before Docker, port 5001 may be occupied. Tell them
to stop the local server first or use `docker compose down` to clean up.

### Issue 6: Memory usage
The SBERT model and Annoy index together use ~500 MB of RAM. Students on machines with
limited memory may see slowdowns. Docker Desktop default is 2 GB, which is sufficient.

---

## 11. Grading Rubric (Suggested)

| Component                        | Points | Criteria                                   |
|----------------------------------|--------|--------------------------------------------|
| `server.py` completeness         | 30     | All 8 TODOs filled correctly               |
| `Dockerfile` completeness        | 20     | All 4 TODOs, builds without errors         |
| `docker-compose.yml` completeness| 15     | Port mapping and volume mount correct      |
| `/ping` endpoint works           | 10     | Returns valid JSON with status and timestamp|
| `/search` endpoint works         | 15     | Returns ranked results for test queries    |
| Error handling                   | 10     | Graceful handling of missing fields        |
| **Total**                        | **100**|                                            |

---

## 12. In-Class Session Plan (1 Hour)

| Time      | Activity                                                |
|-----------|---------------------------------------------------------|
| 0:00-0:10 | Explain semantic search vs keyword search (whiteboard)  |
| 0:10-0:20 | Walk through the architecture diagram                   |
| 0:20-0:30 | Demo: Show the working solution (live curl commands)    |
| 0:30-0:40 | Walk through starter code, explain the 8 TODOs          |
| 0:40-0:50 | Walk through Dockerfile and docker-compose TODOs        |
| 0:50-1:00 | Q&A, clarify submission requirements                    |

**Demo commands for in-class:**

```bash
# Health check
curl http://localhost:5001/ping

# Single query search
curl -X POST http://localhost:5001/search \
  -H "Content-Type: application/json" \
  -d '{"query": ["artificial intelligence in healthcare"], "k": 5}'

# Multiple queries in one request
curl -X POST http://localhost:5001/search \
  -H "Content-Type: application/json" \
  -d '{"query": ["climate change policy", "stock market crash"], "k": 3}'
```

---

## 13. File Structure (What Students Receive)

```
M4_Branch_SBERT_Search/
+-- starter/
|   +-- server_starter.py          <-- 8 TODOs to complete
|   +-- Dockerfile.starter         <-- 4 TODOs to complete
|   +-- docker-compose.starter.yml <-- 2 TODOs to complete
|   +-- requirements.txt           <-- provided complete
|   +-- src/
|   |   +-- __init__.py
|   |   +-- config.py              <-- provided complete
|   |   +-- preprocessor.py        <-- provided complete
|   |   +-- embeddings.py          <-- provided complete
|   |   +-- build_index.py         <-- provided complete
|   |   +-- search.py              <-- provided complete
|   +-- models/
|   |   +-- README_DATA.md         <-- instructions to copy artifacts
|   +-- data/
|       +-- processed/
|       |   +-- .gitkeep
|       +-- raw/
|           +-- .gitkeep
+-- solution/
    +-- server.py                  <-- complete working solution
    +-- Dockerfile                 <-- complete
    +-- docker-compose.yml         <-- complete
    +-- .dockerignore              <-- complete
    +-- requirements.txt           <-- same as starter
    +-- src/                       <-- same as starter (no changes needed)
    +-- models/                    <-- same placeholder
    +-- data/                      <-- same placeholder
```
