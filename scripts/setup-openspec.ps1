$ErrorActionPreference = "Stop"

Write-Host "Checking Node.js..."
$nodeVersion = node --version
Write-Host "Node: $nodeVersion"

Write-Host "Installing latest OpenSpec globally..."
npm install -g @fission-ai/openspec@latest

Write-Host "OpenSpec version:"
openspec --version

Write-Host "Configuring OpenSpec for Codex..."
openspec init --tools codex --profile core

Write-Host "Validating OpenSpec project..."
openspec validate --all --strict

Write-Host "Done. Restart VS Code/Codex and use `$openspec-explore or `$openspec-propose."
