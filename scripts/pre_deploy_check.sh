#!/usr/bin/env bash
# ================================================================
# Tijan AI — Pre-deploy check
# Run this BEFORE every git push to main.
# Exit 0 = safe to deploy. Non-zero = DO NOT DEPLOY.
#
# Usage: ./scripts/pre_deploy_check.sh
# ================================================================
set -euo pipefail

echo "╔══════════════════════════════════════════════╗"
echo "║   Tijan AI — Pre-deploy verification         ║"
echo "╚══════════════════════════════════════════════╝"
echo ""

# 1. Local unit tests (fast — no network)
echo "▶ [1/3] Running local tests (plans, DXF, PDF geometry)..."
python -m pytest tests/test_generate_plans_v4.py tests/test_dxf_pipeline.py tests/test_pdf_geometry.py -v --tb=short
echo "✓ Local tests passed"
echo ""

# 2. Live endpoint tests (requires backend to be running)
echo "▶ [2/4] Running live endpoint tests..."
python -m pytest tests/test_endpoints.py -v --tb=short
echo "✓ Endpoint tests passed"
echo ""

# 3. End-to-end integration tests
echo "▶ [3/4] Running e2e integration tests..."
python -m pytest tests/test_e2e.py -v --tb=short
echo "✓ E2E tests passed"
echo ""

# 4. CORS tests
echo "▶ [4/4] Running CORS tests..."
python -m pytest tests/test_cors.py -v --tb=short
echo "✓ CORS tests passed"
echo ""

echo "╔══════════════════════════════════════════════╗"
echo "║   ALL CHECKS PASSED — safe to deploy         ║"
echo "╚══════════════════════════════════════════════╝"
