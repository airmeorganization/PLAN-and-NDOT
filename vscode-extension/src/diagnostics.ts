import * as vscode from 'vscode';
import { exec } from 'child_process';
import * as path from 'path';

export class DiagnosticsManager {
    private diagnosticCollection: vscode.DiagnosticCollection;
    private timeoutMap: Map<string, NodeJS.Timeout> = new Map();

    constructor() {
        this.diagnosticCollection = vscode.languages.createDiagnosticCollection('plan-and-ndot');
    }

    public register(context: vscode.ExtensionContext): void {
        context.subscriptions.push(this.diagnosticCollection);

        // Run diagnostics on document open
        vscode.workspace.onDidOpenTextDocument(doc => {
            this.runDiagnostics(doc);
        }, null, context.subscriptions);

        // Run diagnostics on document save
        vscode.workspace.onDidSaveTextDocument(doc => {
            const config = vscode.workspace.getConfiguration('planAndNdot');
            if (config.get<boolean>('diagnosticsOnSave', true)) {
                this.runDiagnostics(doc);
            }
        }, null, context.subscriptions);

        // Debounced diagnostics on document change
        vscode.workspace.onDidChangeTextDocument(event => {
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
            this.checkPlan(document, cwd);
        } else if (ext === '.ndot') {
            this.checkNdot(document, cwd);
        }
    }

    private checkPlan(document: vscode.TextDocument, cwd: string): void {
        const config = vscode.workspace.getConfiguration('plan');
        const pythonPath = config.get<string>('pythonPath', 'python');
        const cmd = `"${pythonPath}" -m plan.cli check "${document.fileName}"`;

        exec(cmd, { cwd }, (error, stdout, stderr) => {
            const diagnostics: vscode.Diagnostic[] = [];
            const output = (stderr || stdout || '').trim();

            if (error && output) {
                // Parse PLAN error formats:
                // Format 1: Compile Error: <message> at line <line>, column <col>
                // Format 2: <line>: error <CODE> at col <col>: <message>
                const match1 = output.match(/Compile Error:\s*(?:(\d+):\s*error\s*([A-Z0-9]+)\s*at\s*col\s*(\d+):\s*)?(.*)/i);
                const match2 = output.match(/at line (\d+)(?:,\s*column\s*(\d+))?/i);

                let lineNum = 1;
                let colNum = 1;
                let code = 'PLAN';
                let message = output;

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

                const diagnostic = new vscode.Diagnostic(
                    range,
                    message,
                    vscode.DiagnosticSeverity.Error
                );
                diagnostic.code = code;
                diagnostic.source = 'plan';
                diagnostics.push(diagnostic);
            }

            this.diagnosticCollection.set(document.uri, diagnostics);
        });
    }

    private checkNdot(document: vscode.TextDocument, cwd: string): void {
        const config = vscode.workspace.getConfiguration('ndot');
        const pythonPath = config.get<string>('pythonPath', 'python');
        const cmd = `"${pythonPath}" -m ndot.cli check "${document.fileName}"`;

        exec(cmd, { cwd }, (error, stdout, stderr) => {
            const diagnostics: vscode.Diagnostic[] = [];
            const output = (stderr || stdout || '').trim();

            if (error && output) {
                // Parse N-DOT error formats:
                // Format: Compile Error: <line>: error <CODE> at col <col>: <message>
                // Or: <CODE> at instruction <inst> (char <char>): <message>
                const diagMatch = output.match(/(?:Compile Error:\s*)?(?:(\d+):\s*error\s*)?([N][0-9]{3})(?:\s*at\s*col\s*(\d+))?:\s*(.*)/i);
                
                let lineNum = 1;
                let colNum = 1;
                let code = 'N-DOT';
                let message = output;

                if (diagMatch) {
                    if (diagMatch[1]) lineNum = parseInt(diagMatch[1], 10);
                    if (diagMatch[2]) code = diagMatch[2];
                    if (diagMatch[3]) colNum = parseInt(diagMatch[3], 10);
                    if (diagMatch[4]) message = diagMatch[4].trim();
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

                const diagnostic = new vscode.Diagnostic(
                    range,
                    message,
                    vscode.DiagnosticSeverity.Error
                );
                diagnostic.code = code;
                diagnostic.source = 'ndot';
                diagnostics.push(diagnostic);
            }

            this.diagnosticCollection.set(document.uri, diagnostics);
        });
    }
}
