# Install and Configure OpenSpec for DisputeIQ

This repository is pre-seeded with `openspec/config.yaml` and long-lived capability specs derived from the DisputeIQ FRD.

OpenSpec itself must still be installed locally so it can generate the Codex workflow skills under `.codex/skills/`.

## 1. Check prerequisites

Open a PowerShell terminal in VS Code.

```powershell
node --version
npm --version
git --version
```

OpenSpec requires Node.js 20.19.0 or newer.

If Node is older, upgrade Node before continuing.

## 2. Install OpenSpec

```powershell
npm install -g @fission-ai/openspec@latest
```

Verify:

```powershell
openspec --version
```

## 3. Open this repository in VS Code

```powershell
cd <path-to>\DisputeIQ-OpenSpec-Initial-Repository
code .
```

## 4. Initialize Codex integration

From the repository root:

```powershell
openspec init --tools codex --profile core
```

OpenSpec should preserve/configure the `openspec/` project structure and generate Codex OpenSpec skills under:

```text
.codex/skills/openspec-*/
```

Do not manually maintain those generated skill files.

## 5. Refresh generated skills after an OpenSpec upgrade

```powershell
npm install -g @fission-ai/openspec@latest
openspec update
```

Restart VS Code/Codex afterward so the generated skills are rediscovered.

## 6. Validate the project

```powershell
openspec validate --all --strict
```

Useful inspection commands:

```powershell
openspec list
openspec view
openspec show case-intake-and-management --type spec
```

## 7. How to invoke OpenSpec from Codex

Codex uses OpenSpec skills rather than generated `/opsx:*` command files.

In Codex chat, use skill-style invocations such as:

```text
$openspec-explore
$openspec-propose
$openspec-apply
$openspec-sync
$openspec-archive
```

If the skills do not appear:
1. Run `openspec update`.
2. Confirm `.codex/skills/openspec-*` exists.
3. Restart VS Code/Codex.
4. Confirm you opened Codex from this repository root.

## 8. Start the first DisputeIQ change

Open:

`docs/openspec/001-platform-foundation-prompt.md`

Use that prompt in Codex with `$openspec-propose`.

Review all generated artifacts before `$openspec-apply`.

## 9. Recommended workflow for every change

```text
FRD requirement
   ↓
$openspec-explore
   ↓
$openspec-propose
   ↓
proposal.md
spec delta(s)
design.md
tasks.md
   ↓
Human review
   ↓
$openspec-apply
   ↓
Tests + GitHub Actions
   ↓
$openspec-sync
   ↓
$openspec-archive
```

## 10. Windows troubleshooting

If `openspec` is not recognized after installation:

```powershell
npm prefix -g
```

Make sure the returned global npm directory is on your Windows `PATH`, then reopen VS Code/PowerShell.

## Optional: no global install

You can also initialize with the latest package using:

```powershell
npx openspec@latest init --tools codex --profile core
```

For daily project work, a global installation is simpler.
