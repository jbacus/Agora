#!/bin/bash
# ============================================
# Data Acquisition Script for Agora
# Downloads public domain texts from Project Gutenberg
# ============================================

set -e

echo "📚 Agora Data Acquisition"
echo "============================================"
echo ""

# Create directories
mkdir -p data/raw/marx
mkdir -p data/raw/whitman
mkdir -p data/raw/manson

# ============================================
# Marx Texts (Public Domain)
# ============================================
echo "📖 Downloading Marx texts from Project Gutenberg..."
echo ""

# Capital Volume 1
if [ ! -f "data/raw/marx/capital_vol1.txt" ]; then
    echo "  Downloading Capital Vol. 1..."
    wget -q --show-progress \
        https://www.gutenberg.org/files/61/61-0.txt \
        -O data/raw/marx/capital_vol1.txt
    echo "  ✅ Capital Vol. 1 downloaded"
else
    echo "  ✅ Capital Vol. 1 already exists"
fi

# Communist Manifesto
if [ ! -f "data/raw/marx/communist_manifesto.txt" ]; then
    echo "  Downloading Communist Manifesto..."
    wget -q --show-progress \
        https://www.gutenberg.org/cache/epub/61/pg61.txt \
        -O data/raw/marx/communist_manifesto.txt
    echo "  ✅ Communist Manifesto downloaded"
else
    echo "  ✅ Communist Manifesto already exists"
fi

# Wage Labour and Capital
if [ ! -f "data/raw/marx/wage_labour_and_capital.txt" ]; then
    echo "  Downloading Wage Labour and Capital..."
    wget -q --show-progress \
        https://www.gutenberg.org/files/8002/8002-0.txt \
        -O data/raw/marx/wage_labour_and_capital.txt
    echo "  ✅ Wage Labour and Capital downloaded"
else
    echo "  ✅ Wage Labour and Capital already exists"
fi

echo ""

# ============================================
# Whitman Texts (Public Domain)
# ============================================
echo "📖 Downloading Whitman texts from Project Gutenberg..."
echo ""

# Leaves of Grass
if [ ! -f "data/raw/whitman/leaves_of_grass.txt" ]; then
    echo "  Downloading Leaves of Grass..."
    wget -q --show-progress \
        https://www.gutenberg.org/files/1322/1322-0.txt \
        -O data/raw/whitman/leaves_of_grass.txt
    echo "  ✅ Leaves of Grass downloaded"
else
    echo "  ✅ Leaves of Grass already exists"
fi

# Democratic Vistas
if [ ! -f "data/raw/whitman/democratic_vistas.txt" ]; then
    echo "  Downloading Democratic Vistas..."
    wget -q --show-progress \
        https://www.gutenberg.org/files/8813/8813-0.txt \
        -O data/raw/whitman/democratic_vistas.txt
    echo "  ✅ Democratic Vistas downloaded"
else
    echo "  ✅ Democratic Vistas already exists"
fi

# Specimen Days
if [ ! -f "data/raw/whitman/specimen_days.txt" ]; then
    echo "  Downloading Specimen Days..."
    wget -q --show-progress \
        https://www.gutenberg.org/files/8892/8892-0.txt \
        -O data/raw/whitman/specimen_days.txt
    echo "  ✅ Specimen Days downloaded"
else
    echo "  ✅ Specimen Days already exists"
fi

echo ""

# ============================================
# Manson Texts (Instructions)
# ============================================
echo "📝 Mark Manson texts (copyright protected):"
echo "============================================"
echo ""
echo "⚠️  Mark Manson's books are under copyright."
echo "Please obtain texts legally through one of these methods:"
echo ""
echo "Option 1: Purchase books and extract text (personal use only)"
echo "  - 'The Subtle Art of Not Giving a F*ck'"
echo "  - 'Everything Is F*cked: A Book About Hope'"
echo ""
echo "Option 2: Use freely available blog posts (recommended)"
echo "  - Visit: https://markmanson.net/archive"
echo "  - Manually save 20-30 articles as .txt files"
echo "  - Save to: data/raw/manson/"
echo "  - Focus on: philosophy, psychology, self-improvement"
echo ""
echo "Option 3: Use public excerpts and summaries"
echo "  - Search for book summaries and key excerpts"
echo "  - Combine with blog content"
echo ""
echo "After acquiring Manson content:"
echo "  1. Save .txt files to data/raw/manson/"
echo "  2. Run: python scripts/clean_texts.py"
echo "  3. Run: python scripts/ingest_author.py --author manson"
echo ""

# ============================================
# Summary
# ============================================
echo "============================================"
echo "✅ Data Acquisition Complete"
echo "============================================"
echo ""

# Count files
MARX_COUNT=$(ls data/raw/marx/*.txt 2>/dev/null | wc -l)
WHITMAN_COUNT=$(ls data/raw/whitman/*.txt 2>/dev/null | wc -l)
MANSON_COUNT=$(ls data/raw/manson/*.txt 2>/dev/null | wc -l)

echo "Files acquired:"
echo "  Marx: $MARX_COUNT files"
echo "  Whitman: $WHITMAN_COUNT files"
echo "  Manson: $MANSON_COUNT files"
echo ""

# Check file sizes
echo "Data size:"
du -sh data/raw/marx 2>/dev/null || echo "  Marx: 0 bytes"
du -sh data/raw/whitman 2>/dev/null || echo "  Whitman: 0 bytes"
du -sh data/raw/manson 2>/dev/null || echo "  Manson: 0 bytes"
echo ""

echo "📝 Next steps:"
echo "  1. Add Manson texts to data/raw/manson/ (see instructions above)"
echo "  2. Clean texts: python scripts/clean_texts.py"
echo "  3. Ingest data: python scripts/ingest_author.py --author [author]"
echo ""
