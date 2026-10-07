#!/bin/bash
set -e

# Auto-detect project directory (falls back to script location if PROJECT_ROOT is empty, 'auto', or not found)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
[ -f "$SCRIPT_DIR/.env" ] && . "$SCRIPT_DIR/.env"

if [ -z "$PROJECT_ROOT" ] || [ "$PROJECT_ROOT" = "auto" ] || [ ! -d "$PROJECT_ROOT" ]; then
    PROJECT_ROOT="$SCRIPT_DIR"
fi
cd "$PROJECT_ROOT"
export PROJECT_ROOT

# Activate virtual environment if it exists
if [ -d ".venv" ]; then
    source .venv/bin/activate
fi

echo "Starting CLIP Pipeline Setup & Initial Tasks"

# 0. Check & Download Offline CLIP Model Weights if missing
if [ ! -f "data/models/clip-vit-base-patch32/model.safetensors" ] && [ ! -f "data/models/clip-vit-base-patch32/pytorch_model.bin" ]; then
    echo -e "\n[0/6] Downloading offline CLIP model weights"
    python -m src.models.downloader
fi

# 1. Database Schema Initialization & Seeding
echo -e "\n[1/6] Initializing & Seeding SQLite Database"
python -m src.data.database

# 2. Data Validation & Stratified Sampling
echo -e "\n[2/6] Running Data Validation & Stratified Sampling"
python -m src.data.sampler

# 3. Statistical EDA Analysis & Report Generator
echo -e "\n[3/6] Running Statistical EDA Analysis & Report Generator"
python -m src.data.eda

# 4. Synchronize Benchmark Queries with Dataset
echo -e "\n[4/6] Synchronizing Benchmark Queries with Dataset"
python -m src.data.sync_ground_truth

# 5. Compute Offline Image Embeddings (CLIP ViT-B/32)
echo -e "\n[5/6] Computing Offline Image Embeddings (CLIP ViT-B/32)"
python -m src.models.indexer

# 6. Automated Batch Evaluation on Benchmark Queries
echo -e "\n[6/6] Running Automated Batch Evaluation"
python -m src.evaluation.benchmark

echo -e "\nSetup Pipeline Executed Successfully!"
