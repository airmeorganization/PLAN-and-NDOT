# PLAN & N-DOT VS Code Extension

Official Visual Studio Code extension for **PLAN** (Plain Language controlled-English programming) and **N-DOT** (Neural-DOT numeric computing format).

---

## Features

- **Rich Syntax Highlighting**:
  - Full syntax grammar for `.plan` controlled-English source files.
  - Native syntax grammar for `.ndot` numeric instruction streams and `.ndasm` mnemonic assembly files.
- **Real-Time Diagnostics**:
  - Instant check-time linting on save and edit for PLAN (`P200`, `P301`–`P308`).
  - Validation engine integration for N-DOT (`N101`–`N105`, `N201`–`N209`).
- **Interactive Execution & Compilation**:
  - Run PLAN programs (`plan.run`) directly in integrated terminal.
  - Run N-DOT programs (`ndot.run`) with sandbox permission controls (`--allow-files`, `--allow-network`).
  - Transpile PLAN or N-DOT to clean, standalone Python code (`plan.build`, `ndot.build`).
  - Disassemble `.ndot` binaries into human-readable `.ndasm` listings side-by-side (`ndot.disassemble`).
  - Assemble `.ndasm` mnemonic source into `.ndot` numeric format (`ndot.assemble`).

---

## Extension Commands

| Command | Title | Default Shortcut | Description |
|---|---|---|---|
| `plan.run` | PLAN: Run Program | Editor Play Button | Runs active `.plan` file via `python -m plan.cli run`. |
| `plan.build` | PLAN: Build to Python | Palette | Compiles `.plan` to `.py`. |
| `plan.check` | PLAN: Check Semantics | Palette | Runs semantic check across active file. |
| `plan.toPython` | PLAN: Preview Generated Python | Editor Title Bar | Opens generated Python in an adjacent editor tab. |
| `ndot.run` | N-DOT: Run Program | Editor Play Button | Runs active `.ndot` or `.ndasm` file via `python -m ndot.cli run`. |
| `ndot.build` | N-DOT: Build to Python | Palette | Compiles `.ndot` to `.py`. |
| `ndot.check` | N-DOT: Check Program | Palette | Validates opcode structure, blocks, and slots. |
| `ndot.disassemble` | N-DOT: Disassemble to .ndasm | Editor Title Bar | Generates readable `.ndasm` disassembly. |
| `ndot.assemble` | N-DOT: Assemble to .ndot | Editor Title Bar | Assembles `.ndasm` mnemonic source to `.ndot`. |

---

## Configuration Settings

Configure these options in `settings.json`:

```json
{
  "plan.pythonPath": "python",
  "plan.allowPython": false,
  "plan.allowAllModules": false,
  "ndot.pythonPath": "python",
  "ndot.allowFiles": false,
  "ndot.allowNetwork": false,
  "planAndNdot.diagnosticsOnSave": true
}
```

---

## Development & Building

1. Navigate to the extension directory:
   ```bash
   cd vscode-extension
   ```
2. Install dependencies:
   ```bash
   npm install
   ```
3. Compile TypeScript:
   ```bash
   npm run compile
   ```
4. Package `.vsix` extension:
   ```bash
   npx @vscode/vsce package
   ```
5. Install in VS Code:
   ```bash
   code --install-extension plan-and-ndot-0.1.0.vsix
   ```
