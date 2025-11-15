# LibraryThing to Agora Text Acquisition Pipeline

Automated system for acquiring and preparing author texts from Project Gutenberg based on your LibraryThing library export.

## Overview

This pipeline automates the workflow of:
1. **Parsing** your LibraryThing library export
2. **Searching** for books on Project Gutenberg
3. **Downloading** available public domain texts
4. **Organizing** texts in the correct directory structure for Agora ingest
5. **Generating** detailed reports and download scripts
6. **Preparing** texts for the Agora author knowledge base

## Quick Start

### 1. Export Your LibraryThing Library

1. Go to [LibraryThing.com](https://www.librarything.com) and log in
2. Navigate to: **More → Export your library**
3. Select either format:
   - **Tab-delimited text (opens in Excel)** (.tsv)
   - **JSON** (.json) - Both formats are supported!
4. Download the file (e.g., `LibraryThing_export.tsv` or `librarything_export.json`)

### 2. Run the Acquisition Script

```bash
# Works with both TSV and JSON formats
python scripts/acquire_from_librarything.py --input /path/to/LibraryThing_export.tsv
# or
python scripts/acquire_from_librarything.py --input /path/to/librarything_export.json
```

This will:
- Search Project Gutenberg for each book
- Attempt to download available texts
- Generate reports in `acquisition_report.txt` and `acquisition_report.json`
- Create a download script `download_texts.sh` for manual downloads

### 3. Run the Download Script (if automated downloads fail)

```bash
./download_texts.sh
```

### 4. Review Downloaded Texts

```bash
ls data/raw/
```

You should see directories for each author with their texts:
```
data/raw/
├── marx/
│   ├── das_kapital_vol_1.txt
│   └── communist_manifesto.txt
├── whitman/
│   └── leaves_of_grass.txt
└── austen/
    ├── pride_and_prejudice.txt
    └── emma.txt
```

### 5. Proceed with Agora Ingest Pipeline

Follow the standard Agora workflow:

```bash
# Clean the texts (removes Gutenberg boilerplate)
python scripts/clean_texts.py

# Create author YAML configs (one per author)
# See config/authors/marx.yaml for an example

# Ingest each author
python scripts/ingest_author.py --author marx
python scripts/ingest_author.py --author whitman
python scripts/ingest_author.py --author austen

# Generate expertise profiles
python scripts/create_expertise_profiles.py
```

## Command-Line Options

### Basic Usage

```bash
python scripts/acquire_from_librarything.py --input library.tsv
```

### Filter by Specific Authors

Process only certain authors:

```bash
python scripts/acquire_from_librarything.py \
    --input library.tsv \
    --author-filter "Marx,Whitman,Austen"
```

### Limit Books Per Author

Useful for testing or limiting scope:

```bash
python scripts/acquire_from_librarything.py \
    --input library.tsv \
    --max-books-per-author 5
```

### Custom Output Directory

```bash
python scripts/acquire_from_librarything.py \
    --input library.tsv \
    --output-dir /custom/path/to/texts
```

### Custom Report Paths

```bash
python scripts/acquire_from_librarything.py \
    --input library.tsv \
    --report my_report.txt \
    --json-report my_report.json \
    --download-script download.sh
```

### Verbose Logging

For debugging:

```bash
python scripts/acquire_from_librarything.py \
    --input library.tsv \
    --verbose
```

## Output Files

The script generates several output files:

### 1. Text Report (`acquisition_report.txt`)

Human-readable summary showing:
- Total authors and books processed
- Success/failure statistics
- List of authors with texts found
- List of authors without texts found
- Next steps for ingestion

Example:
```
================================================================================
Agora LibraryThing Text Acquisition Report
================================================================================

SUMMARY
--------------------------------------------------------------------------------
Total authors processed: 10
Total books in library: 87
Books found on Gutenberg: 23 (26.4%)
Books downloaded: 23 (26.4%)
Books failed: 0

AUTHORS WITH TEXTS DISCOVERED
--------------------------------------------------------------------------------
✓ Karl Marx (marx): 3/5 books downloaded
    - Das Kapital, Vol. 1
    - The Communist Manifesto
    - Wage Labour and Capital

✓ Walt Whitman (whitman): 2/3 books downloaded
    - Leaves of Grass
    - Democratic Vistas
```

### 2. JSON Report (`acquisition_report.json`)

Machine-readable detailed report with:
- Complete book metadata
- Gutenberg IDs and URLs
- Download status for each book
- Error information

Structure:
```json
{
  "summary": {
    "total_authors": 10,
    "total_books": 87,
    "books_found": 23,
    "books_downloaded": 23,
    "books_failed": 0
  },
  "authors": {
    "marx": {
      "author": "Karl Marx",
      "total_books": 5,
      "books_found": 3,
      "books": [
        {
          "title": "Das Kapital, Vol. 1",
          "gutenberg_id": "61",
          "gutenberg_url": "https://www.gutenberg.org/ebooks/61",
          "downloaded": true,
          "download_path": "data/raw/marx/das_kapital_vol_1.txt"
        }
      ]
    }
  }
}
```

### 3. Download Script (`download_texts.sh`)

Executable bash script for manual downloading if automated downloads fail:
- Tries multiple URL patterns for each book
- Skips already-downloaded files
- Shows progress with emoji indicators
- Validates downloaded file sizes

### 4. Downloaded Texts (`data/raw/<author>/`)

Plain text files organized by author:
- UTF-8 encoded
- Includes Project Gutenberg headers/footers (cleaned in next step)
- Named with normalized titles (e.g., `das_kapital_vol_1.txt`)

## How It Works

### 1. LibraryThing Parsing

The script supports both JSON and TSV (tab-delimited) export formats from LibraryThing.

**Auto-detection:** The script automatically detects which format you're using based on:
- File extension (.json, .tsv, .txt)
- File content (checks first character)

**Extracted data:**
- Book titles
- Author names (both "First Last" and "Last, First" formats)
- ISBNs (for potential future use)
- Publication dates

### 2. Author Name Normalization

Author names are normalized for directory creation:
- Takes the last name (Western naming convention)
- Converts to lowercase
- Removes special characters

Examples:
| Original Name | Normalized ID |
|---------------|---------------|
| Karl Marx | `marx` |
| Walt Whitman | `whitman` |
| Charles Baudelaire | `baudelaire` |
| Jane Austen | `austen` |

### 3. Book Search

The script searches for books using two methods:

**Method 1: Gutendex API** (when available)
- Queries the official Gutendex API
- Searches by author and title
- Uses fuzzy matching for title variations

**Method 2: Manual Lookup** (fallback)
- Built-in database of popular public domain books
- Maps author+title to Gutenberg IDs
- Covers major classic authors

Currently includes manual mappings for:
- Karl Marx
- Walt Whitman
- Charles Baudelaire
- Jane Austen
- Homer
- Marcus Aurelius
- Plato
- Friedrich Nietzsche
- Niccolò Machiavelli
- Sun Tzu
- And more...

### 4. Download Process

For each found book, the script:
1. **Tries wget** (often works better with Gutenberg)
2. **Falls back to Python requests**
3. **Tries multiple URL patterns:**
   - `/files/{id}/{id}-0.txt` (UTF-8 version)
   - `/files/{id}/{id}.txt` (ASCII version)
   - `/cache/epub/{id}/pg{id}.txt` (ePub cache)
4. **Validates downloads** (checks file size > 100 bytes)
5. **Handles encoding** (UTF-8 preferred, bytes as fallback)

### 5. Report Generation

Creates three types of outputs:
- **Text report**: Human-readable summary
- **JSON report**: Machine-readable data
- **Download script**: Bash script for manual downloading

## Limitations

### Only Public Domain Works

Project Gutenberg only hosts public domain texts. Generally:
- Works published before 1928 in the US ✅
- Modern copyrighted books ❌

### English Language Focus

The current implementation primarily finds English-language texts. Foreign language books may not be found even if available on Gutenberg.

### Western Name Convention

Author normalization assumes Western naming (First Last format). May not work correctly for:
- East Asian names
- Mononyms (single names)
- Complex multi-part names

### Fuzzy Title Matching

The search uses fuzzy matching which may:
- Find wrong editions
- Miss books with very different titles in Gutenberg
- Require manual verification

## Troubleshooting

### Problem: Books Not Found

**Symptom:** "Not found on Gutenberg" errors

**Solutions:**
1. Check if the book is actually on Project Gutenberg
   - Search manually: https://www.gutenberg.org/
2. Try adding the book to the manual lookup database
   - Edit `scripts/acquire_from_librarything.py`
   - Add to the `known_books` dictionary in `_manual_lookup()`
3. Verify the book is public domain
   - Publication date before 1928 in most cases

### Problem: Downloads Failing

**Symptom:** "Failed to download" or 403/404 errors

**Solutions:**
1. Use the generated download script instead:
   ```bash
   ./download_texts.sh
   ```
2. Check network connectivity to Project Gutenberg
3. Try again later (Gutenberg may be under maintenance)
4. Download manually from Project Gutenberg and place in `data/raw/<author>/`

### Problem: Wrong Books Downloaded

**Symptom:** Downloaded text doesn't match expected book

**Solutions:**
1. Review the JSON report to see which Gutenberg IDs were matched
2. Manually check the Gutenberg entry
3. Delete incorrect file and download correct one manually
4. Update the manual lookup dictionary if needed

### Problem: Author Name Issues

**Symptom:** Author directories not created correctly

**Solutions:**
1. Check the LibraryThing export has author names
2. Manually specify author ID by editing the script
3. Create directory manually: `mkdir -p data/raw/<author_id>`

## Advanced Usage

### Adding New Books to Manual Lookup

Edit `scripts/acquire_from_librarything.py` and add to the `known_books` dictionary:

```python
known_books = {
    'author name': {
        'book title': gutenberg_id,
        'another book': gutenberg_id,
    },
}
```

Example:
```python
'charles dickens': {
    'great expectations': 1400,
    'tale of two cities': 98,
    'oliver twist': 730,
},
```

### Extending to Other Sources

The architecture supports adding new text sources beyond Gutenberg:

1. Create a new searcher class (like `GutenbergSearcher`)
2. Implement `search_book()` and `download_text()` methods
3. Add to the pipeline in `TextAcquisitionPipeline`

Potential sources:
- Internet Archive
- Wikisource
- Google Books (snippets)
- Academic repositories

### Custom Author ID Mapping

If you want to override the automatic author ID normalization:

1. Modify `LibraryThingParser._normalize_author_name()`
2. Add custom mappings for specific authors
3. Or use a configuration file for mappings

## Integration with Agora Pipeline

This tool is designed as the first step in the Agora author knowledge base pipeline:

```
LibraryThing Export
        ↓
acquire_from_librarything.py  ← YOU ARE HERE
        ↓
Downloaded Texts (data/raw/)
        ↓
clean_texts.py
        ↓
Cleaned Texts
        ↓
Create Author YAML Configs
        ↓
ingest_author.py
        ↓
Vector Database
        ↓
create_expertise_profiles.py
        ↓
Ready for Agora Multi-Author Debates!
```

### Next Steps After Acquisition

1. **Clean Texts**
   ```bash
   python scripts/clean_texts.py
   ```
   Removes Project Gutenberg headers/footers

2. **Create Author Configs**
   Create YAML file for each author in `config/authors/<author_id>.yaml`:
   ```yaml
   name: Karl Marx
   expertise_domains:
     - political_economy
     - capitalism
   voice_characteristics:
     tone: analytical, critical
     vocabulary: dialectical, materialist
   bio: |
     Karl Marx (1818-1883)...
   major_works:
     - Das Kapital
   system_prompt: |
     You are Karl Marx...
   ```

3. **Ingest Authors**
   ```bash
   python scripts/ingest_author.py --author marx
   ```
   Chunks texts, generates embeddings, stores in vector DB

4. **Create Expertise Profiles**
   ```bash
   python scripts/create_expertise_profiles.py
   ```
   Generates semantic vectors for author routing

## Example Workflow

Complete end-to-end example:

```bash
# Step 1: Export from LibraryThing (done in browser)
# Save as: my_library.tsv

# Step 2: Run acquisition (filter for specific authors)
python scripts/acquire_from_librarything.py \
    --input my_library.tsv \
    --author-filter "Marx,Whitman,Baudelaire,Austen" \
    --max-books-per-author 3

# Step 3: Review report
cat acquisition_report.txt

# Step 4: Run download script if needed
./download_texts.sh

# Step 5: Verify downloads
ls data/raw/*/

# Step 6: Clean texts
python scripts/clean_texts.py

# Step 7: Create configs
for author in marx whitman baudelaire austen; do
    cp config/authors/marx.yaml config/authors/$author.yaml
    # Edit each file manually
done

# Step 8: Ingest all authors
for author in marx whitman baudelaire austen; do
    python scripts/ingest_author.py --author $author
done

# Step 9: Create expertise profiles
python scripts/create_expertise_profiles.py

# Step 10: Test the system
python -m src.main
# Ask: "What do Marx and Whitman think about democracy?"
```

## Files Created by This Tool

```
Agora/
├── scripts/
│   └── acquire_from_librarything.py  ← Main script
├── examples/
│   └── librarything_export_sample.tsv ← Example input
├── docs/
│   └── librarything-acquisition.md    ← Detailed docs
├── acquisition_report.txt             ← Generated report
├── acquisition_report.json            ← Generated data
├── download_texts.sh                  ← Generated script
└── data/raw/                          ← Downloaded texts
    ├── marx/
    ├── whitman/
    └── austen/
```

## Contributing

To add more authors to the manual lookup database:

1. Find the Gutenberg book ID
   - Search: https://www.gutenberg.org/
   - ID is in the URL: `gutenberg.org/ebooks/1234` → ID: 1234

2. Add to `known_books` in `acquire_from_librarything.py`:
   ```python
   'author name': {
       'book title': 1234,
   }
   ```

3. Test with an example LibraryThing export

4. Submit a PR with your additions!

## License

This tool is part of the Agora project. See main project LICENSE.

## Support

For issues or questions:
- Check the [detailed documentation](docs/librarything-acquisition.md)
- Review the generated `acquisition_report.json` for error details
- Use `--verbose` flag for debugging
- Open an issue on the project repository

## Credits

- Built for the Agora multi-author debate system
- Uses Project Gutenberg's free public domain texts
- LibraryThing export format support
- Gutendex API integration (when available)
