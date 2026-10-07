import * as vscode from 'vscode';
import { exec } from 'child_process';
import * as path from 'path';

export class PlanController {
    private outputChannel: vscode.OutputChannel;

    constructor() {
        this.outputChannel = vscode.window.createOutputChannel('PLAN Toolchain');
    }

    public registerCommands(context: vscode.ExtensionContext): void {
        context.subscriptions.push(
            vscode.commands.registerCommand('plan.run', (uri?: vscode.Uri) => this.run(uri)),
            vscode.commands.registerCommand('plan.build', (uri?: vscode.Uri) => this.build(uri)),
            vscode.commands.registerCommand('plan.check', (uri?: vscode.Uri) => this.check(uri)),
            vscode.commands.registerCommand('plan.toPython', (uri?: vscode.Uri) => this.previewPython(uri))
        );
    }

    private getTargetFile(uri?: vscode.Uri): { filePath: string; cwd: string } | null {
        let targetUri = uri;
        if (!targetUri) {
            const editor = vscode.window.activeTextEditor;
            if (editor) {
                targetUri = editor.document.uri;
            }
        }

        if (!targetUri || !targetUri.fsPath.endsWith('.plan')) {
            vscode.window.showErrorMessage('Please open or select a .plan file first.');
            return null;
        }

        const filePath = targetUri.fsPath;
        const workspaceFolder = vscode.workspace.getWorkspaceFolder(targetUri);
        const cwd = workspaceFolder ? workspaceFolder.uri.fsPath : path.dirname(filePath);
        return { filePath, cwd };
    }

    public run(uri?: vscode.Uri): void {
        const fileInfo = this.getTargetFile(uri);
        if (!fileInfo) return;

        const config = vscode.workspace.getConfiguration('plan');
        const pythonPath = config.get<string>('pythonPath', 'python');
        const allowPython = config.get<boolean>('allowPython', false) ? ' --allow-python' : '';
        const allowAllModules = config.get<boolean>('allowAllModules', false) ? ' --allow-all-modules' : '';

        const cmd = `"${pythonPath}" -m plan.cli run "${fileInfo.filePath}"${allowPython}${allowAllModules}`;

        let terminal = vscode.window.terminals.find(t => t.name === 'PLAN');
        if (!terminal) {
            terminal = vscode.window.createTerminal({ name: 'PLAN', cwd: fileInfo.cwd });
        }
        terminal.show();
        terminal.sendText(cmd);
    }

    public build(uri?: vscode.Uri): void {
        const fileInfo = this.getTargetFile(uri);
        if (!fileInfo) return;

        const config = vscode.workspace.getConfiguration('plan');
        const pythonPath = config.get<string>('pythonPath', 'python');
        const defaultOut = fileInfo.filePath.replace(/\.plan$/, '.py');

        vscode.window.showInputBox({
            prompt: 'Output Python file path',
            value: defaultOut
        }).then(outPath => {
            if (!outPath) return;

            const cmd = `"${pythonPath}" -m plan.cli build "${fileInfo.filePath}" -o "${outPath}"`;
            this.outputChannel.show(true);
            this.outputChannel.appendLine(`[PLAN Build] ${cmd}`);

            exec(cmd, { cwd: fileInfo.cwd }, (error, stdout, stderr) => {
                if (error) {
                    this.outputChannel.appendLine(`[Error] ${stderr || stdout}`);
                    vscode.window.showErrorMessage(`PLAN build failed: ${stderr || stdout}`);
                } else {
                    this.outputChannel.appendLine(`[Success] ${stdout.trim()}`);
                    vscode.window.showInformationMessage(`Successfully built ${path.basename(outPath)}`);
                }
            });
        });
    }

    public check(uri?: vscode.Uri): void {
        const fileInfo = this.getTargetFile(uri);
        if (!fileInfo) return;

        const config = vscode.workspace.getConfiguration('plan');
        const pythonPath = config.get<string>('pythonPath', 'python');
        const cmd = `"${pythonPath}" -m plan.cli check "${fileInfo.filePath}"`;

        exec(cmd, { cwd: fileInfo.cwd }, (error, stdout, stderr) => {
            if (error) {
                vscode.window.showErrorMessage(`PLAN Check Failed: ${(stderr || stdout).trim()}`);
            } else {
                vscode.window.showInformationMessage('PLAN check passed with 0 errors.');
            }
        });
    }

    public previewPython(uri?: vscode.Uri): void {
        const fileInfo = this.getTargetFile(uri);
        if (!fileInfo) return;

        const config = vscode.workspace.getConfiguration('plan');
        const pythonPath = config.get<string>('pythonPath', 'python');
        const cmd = `"${pythonPath}" -m plan.cli python "${fileInfo.filePath}"`;

        exec(cmd, { cwd: fileInfo.cwd }, (error, stdout, stderr) => {
            if (error) {
                vscode.window.showErrorMessage(`PLAN codegen failed: ${(stderr || stdout).trim()}`);
            } else {
                vscode.workspace.openTextDocument({
                    content: stdout,
                    language: 'python'
                }).then(doc => {
                    vscode.window.showTextDocument(doc, { preview: true, viewColumn: vscode.ViewColumn.Beside });
                });
            }
        });
    }
}
