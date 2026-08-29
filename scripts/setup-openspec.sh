#!/usr/bin/env bash
set -euo pipefail

echo "Checking Node.js..."
node --version
npm --version

echo "Installing latest OpenSpec globally..."
npm install -g @fission-ai/openspec@latest

echo "OpenSpec version:"
openspec --version

echo "Configuring OpenSpec for Codex..."
openspec init --tools codex --profile core

echo "Validating OpenSpec project..."
openspec validate --all --strict

echo 'Done. Restart Codex and use $openspec-explore or $openspec-propose.'
