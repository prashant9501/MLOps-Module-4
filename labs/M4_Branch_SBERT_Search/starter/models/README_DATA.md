# Model Artifacts -- Required Files

This directory must contain the following pre-built model artifacts before
running the search API. These files are NOT included in the starter code
because they are large binary/data files.

## How to Get These Files

Copy them from the course materials (USB drive or download link provided
by your instructor):

```
Course_Materials/
  Module_4/
    branch_sbert_models/
      None_title.annoy         (~28 MB)
      None_title_ids.json      (~1 MB)
      None_title_stats.json    (<1 KB)
```

## Where to Place Them

Copy all three files into THIS directory (`models/`):

```
starter/
  models/
    None_title.annoy           <-- copy here
    None_title_ids.json        <-- copy here
    None_title_stats.json      <-- copy here
```

## File Descriptions

| File                    | Size   | Description                                    |
|-------------------------|--------|------------------------------------------------|
| `None_title.annoy`     | ~28 MB | Annoy index with 50 trees, euclidean metric    |
| `None_title_ids.json`  | ~1 MB  | Maps section IDs to article IDs                |
| `None_title_stats.json`| <1 KB  | Section count statistics (mean, median, std)   |

## Also Needed: Data Files

You also need the dataset files in the `data/` directory:

```
starter/
  data/
    raw/
      raw.csv                  (~50 MB, original news articles)
    processed/
      None_title_processed.csv (~2 MB, preprocessed titles)
```

Copy these from:
```
Course_Materials/
  Module_4/
    branch_sbert_data/
      raw.csv
      None_title_processed.csv
```

## Verification

After copying, your directory should look like:

```
starter/
  models/
    None_title.annoy
    None_title_ids.json
    None_title_stats.json
    README_DATA.md          (this file)
  data/
    raw/
      raw.csv
    processed/
      None_title_processed.csv
```

Without these files, the server will crash on startup with a FileNotFoundError.
