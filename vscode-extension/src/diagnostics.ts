import * as vscode from 'vscode';
import { exec, ChildProcess } from 'child_process';
import * as path from 'path';
import { ToolchainResolver } from './toolchain';

interface StructuredDiag {
    code: string;
    message: string;
    line?: number;
    column?: number;
    severity?: string;
    location?: string;
    source_text?: string;
}

interface StructuredResult {
    ok: boolean;
    diagnostics?: StructuredDiag[];
}

export class DiagnosticsManager {
    private diagnosticCollection: vscode.DiagnosticCollection;
    private timeoutMap: Map<string, NodeJS.Timeout> = new Map();
    private activeProcesses: Map<string, ChildProcess> = new Map();

    constructor(private resolver: ToolchainResolver) {
        this.diagnosticCollection = vscode.languages.createDiagnosticCollection('plan-and-ndot');
    }

    public register(context: vscode.ExtensionContext): void {
        context.subscriptions.push(this.diagnosticCollection);

        // Run diagnostics on document open
        vscode.workspace.onDidOpenTextDocument(doc => {
            this.runDiagnostics(doc);
        }, null, context.subscriptions);

        // Run diagnostics on document save (default: true)
        vscode.workspace.onDidSaveTextDocument(doc => {
            const config = vscode.workspace.getConfiguration('planAndNdot');
            if (config.get<boolean>('diagnosticsOnSave', true)) {
                this.runDiagnostics(doc);
            }
        }, null, context.subscriptions);

        // Live diagnostics on document change (default: false, debounced 600ms)
        vscode.workspace.onDidChangeTextDocument(event => {
            const config = vscode.workspace.getConfiguration('planAndNdot');
            if (!config.get<boolean>('diagnosticsOnChange', false)) {
                return;
            }

            const doc = event.document;
            const docUri = doc.uri.toString();
            if (this.timeoutMap.has(docUri)) {
                clearTimeout(this.timeoutMap.get(docUri)!);
            }
            const timer = setTimeout(() => {
                this.runDiagnostics(doc);
                this.timeoutMap.delete(docUri);
            }, 600);
            this.timeoutMap.set(docUri, timer);
        }, null, context.subscriptions);

        // Clear diagnostics when document is closed
        vscode.workspace.onDidCloseTextDocument(doc => {
            const docUri = doc.uri.toString();
            if (this.timeoutMap.has(docUri)) {
                clearTimeout(this.timeoutMap.get(docUri)!);
                this.timeoutMap.delete(docUri);
            }
            if (this.activeProcesses.has(docUri)) {
                this.activeProcesses.get(docUri)!.kill();
                this.activeProcesses.delete(docUri);
            }
            this.diagnosticCollection.delete(doc.uri);
        }, null, context.subscriptions);

        // Run on all currently open matching documents
        vscode.workspace.textDocuments.forEach(doc => this.runDiagnostics(doc));
    }

    public runDiagnostics(document: vscode.TextDocument): void {
        const ext = path.extname(document.fileName).toLowerCase();
        if (ext !== '.plan' && ext !== '.ndot') {
            return;
        }

        const workspaceFolder = vscode.workspace.getWorkspaceFolder(document.uri);
        const cwd = workspaceFolder ? workspaceFolder.uri.fsPath : path.dirname(document.fileName);

        if (ext === '.plan') {
            this.checkLanguage(document, cwd, 'plan');
        } else if (ext === '.ndot') {
            this.checkLanguage(document, cwd, 'ndot');
        }
    }

    private checkLanguage(document: vscode.TextDocument, cwd: string, lang: 'plan' | 'ndot'): void {
        const docUri = document.uri.toString();

        // Kill any in-flight check process for this document
        if (this.activeProcesses.has(docUri)) {
            try {
                this.activeProcesses.get(docUri)!.kill();
            } catch (_) {}
            this.activeProcesses.delete(docUri);
        }

        const pythonPath = this.resolver.getPythonPath(lang);
        const toolchain = lang === 'plan' ? this.resolver.getPlanCli(cwd) : this.resolver.getNdotCli(cwd);
        const cmd = `"${pythonPath}" "${toolchain.cliPath}" check "${document.fileName}" --json`;

        const child = exec(cmd, { cwd, env: toolchain.env }, (error, stdout, stderr) => {
            this.activeProcesses.delete(docUri);
            const diagnostics: vscode.Diagnostic[] = [];
            const rawOutput = (stdout || stderr || '').trim();

            if (!rawOutput) {
                this.diagnosticCollection.set(document.uri, []);
                return;
            }

            // 1. Try structured JSON diagnostics from compiler
            let parsedJson: StructuredResult | null = null;
            try {
                parsedJson = JSON.parse(rawOutput);
            } catch (_) {
                // If output has extra prefix text before json, find first '{'
                const firstBrace = rawOutput.indexOf('{');
                if (firstBrace !== -1) {
                    try {
                        parsedJson = JSON.parse(rawOutput.slice(firstBrace));
                    } catch (_) {}
                }
            }

            if (parsedJson && Array.isArray(parsedJson.diagnostics)) {
                for (const item of parsedJson.diagnostics) {
                    const lineIndex = Math.max(0, (item.line || 1) - 1);
                    const colIndex = Math.max(0, (item.column || 1) - 1);
                    const lineText = document.lineCount > lineIndex ? document.lineAt(lineIndex).text : '';

                    // Find precise token bounds starting at colIndex
                    let endColIndex = colIndex + 1;
                    while (endColIndex < lineText.length && !/[\s.,;:()[\]{}]/.test(lineText[endColIndex])) {
                        endColIndex++;
                    }

                    const range = new vscode.Range(
                        lineIndex,
                        colIndex,
                        lineIndex,
                        Math.max(endColIndex, colIndex + 1)
                    );

                    const severity = item.severity === 'warning'
                        ? vscode.DiagnosticSeverity.Warning
                        : vscode.DiagnosticSeverity.Error;

                    const diag = new vscode.Diagnostic(range, item.message, severity);
                    diag.code = item.code;
                    diag.source = lang;
                    diagnostics.push(diag);
                }
                this.diagnosticCollection.set(document.uri, diagnostics);
                return;
            }

            // 2. Fallback regex parser for legacy or raw error output
            if (error && rawOutput) {
                const match1 = rawOutput.match(/(?:Compile Error:\s*)?(?:(\d+):\s*error\s*)?([A-Z0-9]+)?(?:\s*at\s*col\s*(\d+))?:\s*(.*)/i);
                const match2 = rawOutput.match(/at line (\d+)(?:,\s*column\s*(\d+))?/i);

                let lineNum = 1;
                let colNum = 1;
                let code = lang.toUpperCase();
                let message = rawOutput;

                if (match1) {
                    if (match1[1]) lineNum = parseInt(match1[1], 10);
                    if (match1[2]) code = match1[2];
                    if (match1[3]) colNum = parseInt(match1[3], 10);
                    if (match1[4]) message = match1[4].trim();
                }
                if (match2) {
                    lineNum = parseInt(match2[1], 10);
                    if (match2[2]) colNum = parseInt(match2[2], 10);
                }

                const lineIndex = Math.max(0, lineNum - 1);
                const colIndex = Math.max(0, colNum - 1);
                const lineText = document.lineCount > lineIndex ? document.lineAt(lineIndex).text : '';
                const range = new vscode.Range(
                    lineIndex,
                    colIndex,
                    lineIndex,
                    Math.max(colIndex + 1, lineText.length)
                );

                const diag = new vscode.Diagnostic(range, message, vscode.DiagnosticSeverity.Error);
                diag.code = code;
                diag.source = lang;
                diagnostics.push(diag);
            }

            this.diagnosticCollection.set(document.uri, diagnostics);
        });

        this.activeProcesses.set(docUri, child);
    }
}
