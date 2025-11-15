# LibraryThing Text Acquisition Guide

This guide explains how to use the LibraryThing text acquisition pipeline to automatically download and prepare texts for the Agora author ingest process.

## Overview

The `acquire_from_librarything.py` script automates the process of:

1. Parsing a LibraryThing export file (TSV format)
2. Searching for books on Project Gutenberg
3. Downloading available texts
4. Organizing them in the correct directory structure
5. Generating reports on what was found

## Prerequisites

### Install Dependencies

```bash
pip install requests
```

### Export Your LibraryThing Library

1. Go to LibraryThing.com and log in
2. Navigate to "More" → "Export your library"
3. Select your preferred format:
   - "Tab-delimited text (opens in Excel)" (.tsv)
   - "JSON" (.json)
   - Both formats are fully supported!
4. Click "Download"
5. Save the file (e.g., `LibraryThing_export.tsv` or `librarything_export.json`)

## Basic Usage

### Step 1: Run the Acquisition Script

```bash
python scripts/acquire_from_librarything.py --input /path/to/LibraryThing_export.tsv
```

This will:
- Parse your LibraryThing export
- Search for each book on Project Gutenberg
- Download available texts to `data/raw/<author>/`
- Generate acquisition reports

### Step 2: Review the Report

The script generates two reports:

1. **Text Report** (`acquisition_report.txt`): Human-readable summary
2. **JSON Report** (`acquisition_report.json`): Machine-readable details

Example report output:

```
================================================================================
Agora LibraryThing Text Acquisition Report
================================================================================

SUMMARY
--------------------------------------------------------------------------------
Total authors processed: 15
Total books in library: 142
Books found on Gutenberg: 38 (26.8%)
Books downloaded: 38 (26.8%)
Books failed: 0

AUTHORS WITH TEXTS DISCOVERED
--------------------------------------------------------------------------------
✓ Karl Marx (marx): 3/5 books downloaded
    - Das Kapital, Vol. 1
    - The Communist Manifesto
    - Wage Labour and Capital

✓ Walt Whitman (whitman): 2/4 books downloaded
    - Leaves of Grass
    - Democratic Vistas

AUTHORS WITHOUT TEXTS DISCOVERED
--------------------------------------------------------------------------------
✗ Modern Author (modern): 0/3 books found
✗ Recent Writer (writer): 0/8 books found
```

### Step 3: Create Author Configs

For each author with downloaded texts, create a YAML config file in `config/authors/`:

```bash
# Example: config/authors/marx.yaml
cat > config/authors/marx.yaml << EOF
name: Karl Marx
expertise_domains:
  - political_economy
  - capitalism
  - class_struggle

voice_characteristics:
  tone: analytical, critical
  vocabulary: dialectical, materialist
  perspective: class-based economic analysis

bio: |
  Karl Marx (1818-1883) was a German philosopher, economist, and revolutionary...

major_works:
  - Das Kapital
  - The Communist Manifesto

system_prompt: |
  You are Karl Marx, speaking with rigorous theoretical analysis...
EOF
```

### Step 4: Clean and Ingest Texts

```bash
# Clean the downloaded texts (removes Gutenberg headers/footers)
python scripts/clean_texts.py

# Ingest each author
python scripts/ingest_author.py --author marx
python scripts/ingest_author.py --author whitman

# Create expertise profiles
python scripts/create_expertise_profiles.py
```

## Advanced Usage

### Filter by Specific Authors

Process only specific authors from your library:

```bash
python scripts/acquire_from_librarything.py \
    --input library.tsv \
    --author-filter "Marx,Whitman,Baudelaire"
```

### Limit Books Per Author

Process only the first N books for each author:

```bash
python scripts/acquire_from_librarything.py \
    --input library.tsv \
    --max-books-per-author 5
```

### Custom Output Directory

Specify a custom output directory:

```bash
python scripts/acquire_from_librarything.py \
    --input library.tsv \
    --output-dir /path/to/custom/directory
```

### Verbose Logging

Enable detailed logging for debugging:

```bash
python scripts/acquire_from_librarything.py \
    --input library.tsv \
    --verbose
```

### Custom Report Paths

Specify custom paths for the reports:

```bash
python scripts/acquire_from_librarything.py \
    --input library.tsv \
    --report my_report.txt \
    --json-report my_report.json
```

## Understanding the Output

### Directory Structure

Downloaded texts are organized as:

```
data/raw/
├── marx/
│   ├── das_kapital_vol_1.txt
│   ├── communist_manifesto.txt
│   └── wage_labour_and_capital.txt
├── whitman/
│   ├── leaves_of_grass.txt
│   └── democratic_vistas.txt
└── baudelaire/
    ├── flowers_of_evil.txt
    └── paris_spleen.txt
```

### Author ID Normalization

Author names are normalized to create directory names:

| Original Name | Author ID |
|---------------|-----------|
| Karl Marx | `marx` |
| Walt Whitman | `whitman` |
| Charles Baudelaire | `baudelaire` |
| Jane Austen | `austen` |

The script uses the last name, lowercased, with special characters removed.

### JSON Report Structure

```json
{
  "summary": {
    "total_authors": 15,
    "total_books": 142,
    "books_found": 38,
    "books_downloaded": 38,
    "books_failed": 0
  },
  "authors": {
    "marx": {
      "author": "Karl Marx",
      "author_id": "marx",
      "total_books": 5,
      "books_found": 3,
      "books_downloaded": 3,
      "books_failed": 0,
      "books": [
        {
          "title": "Das Kapital, Vol. 1",
          "gutenberg_id": "61",
          "gutenberg_url": "https://www.gutenberg.org/ebooks/61",
          "downloaded": true,
          "download_path": "data/raw/marx/das_kapital_vol_1.txt",
          "error": null
        }
      ]
    }
  }
}
```

## Troubleshooting

### Books Not Found

Project Gutenberg only hosts public domain texts (generally works published before 1928 in the US). Modern books will not be found.

To find more texts:
- Use the JSON report to see which books were not found
- Manually search for them on:
  - Internet Archive (archive.org)
  - Google Books (for snippets)
  - Wikisource
  - Other public domain repositories

### Download Failures

If downloads fail:
1. Check your internet connection
2. Verify Project Gutenberg is accessible
3. Try running the script again (it will skip already-downloaded files)
4. Use `--verbose` flag to see detailed error messages

### Rate Limiting

The script includes a 1-second delay between downloads to be respectful to Project Gutenberg's servers. For large libraries, this may take time. This is intentional and should not be removed.

## Best Practices

1. **Start Small**: Test with `--author-filter` on a few authors first
2. **Review Reports**: Always check the acquisition reports before proceeding
3. **Manual Review**: Review downloaded texts to ensure quality
4. **Create Configs**: Take time to create thoughtful author YAML configs
5. **Clean Texts**: Always run `clean_texts.py` before ingestion

## Limitations

- Only searches Project Gutenberg (future versions may add more sources)
- Only finds English-language texts
- Requires exact or very similar title matches
- Cannot download copyrighted modern works
- Assumes Western naming conventions (last name used for author ID)

## Future Enhancements

Potential improvements:
- Support for Internet Archive
- Support for Wikisource
- Better fuzzy matching for titles
- Multi-language support
- ISBN-based search
- Parallel downloads
- Resume capability for interrupted downloads

## Support

For issues or questions:
- Check the JSON report for detailed error information
- Use `--verbose` flag for debugging
- Review the LibraryThing export format documentation
- Consult Project Gutenberg API documentation (Gutendex)

## Complete Example Workflow

```bash
# 1. Export from LibraryThing and save as library.tsv

# 2. Run acquisition
python scripts/acquire_from_librarything.py --input library.tsv

# 3. Review reports
cat acquisition_report.txt
less acquisition_report.json

# 4. Create author configs for authors with texts
for author in data/raw/*/; do
    author_id=$(basename "$author")
    echo "Creating config for $author_id"
    # Create config/authors/${author_id}.yaml
done

# 5. Clean texts
python scripts/clean_texts.py

# 6. Ingest authors
for author in data/raw/*/; do
    author_id=$(basename "$author")
    python scripts/ingest_author.py --author "$author_id"
done

# 7. Create expertise profiles
python scripts/create_expertise_profiles.py

# 8. Test the system
python -m src.main
```
