import * as vscode from 'vscode';
import { exec } from 'child_process';
import * as path from 'path';
import { ToolchainResolver } from './toolchain';

export class PlanController {
    private outputChannel: vscode.OutputChannel;

    constructor(private resolver: ToolchainResolver) {
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
        const pythonPath = this.resolver.getPythonPath('plan');
        const toolchain = this.resolver.getPlanCli(fileInfo.cwd);

        const allowPython = config.get<boolean>('allowPython', false) ? ' --allow-python' : '';
        const allowAllModules = config.get<boolean>('allowAllModules', false) ? ' --allow-all-modules' : '';

        const cmd = `"${pythonPath}" "${toolchain.cliPath}" run "${fileInfo.filePath}"${allowPython}${allowAllModules}`;

        let terminal = vscode.window.terminals.find(t => t.name === 'PLAN');
        if (!terminal) {
            terminal = vscode.window.createTerminal({ name: 'PLAN', cwd: fileInfo.cwd, env: toolchain.env });
        }
        terminal.show();
        terminal.sendText(cmd);
    }

    public build(uri?: vscode.Uri): void {
        const fileInfo = this.getTargetFile(uri);
        if (!fileInfo) return;

        const pythonPath = this.resolver.getPythonPath('plan');
        const toolchain = this.resolver.getPlanCli(fileInfo.cwd);
        const defaultOut = fileInfo.filePath.replace(/\.plan$/, '.py');

        vscode.window.showInputBox({
            prompt: 'Output Python file path',
            value: defaultOut
        }).then(outPath => {
            if (!outPath) return;

            const cmd = `"${pythonPath}" "${toolchain.cliPath}" build "${fileInfo.filePath}" -o "${outPath}"`;
            this.outputChannel.show(true);
            this.outputChannel.appendLine(`[PLAN Build] ${cmd}`);

            exec(cmd, { cwd: fileInfo.cwd, env: toolchain.env }, (error, stdout, stderr) => {
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

        const pythonPath = this.resolver.getPythonPath('plan');
        const toolchain = this.resolver.getPlanCli(fileInfo.cwd);
        const cmd = `"${pythonPath}" "${toolchain.cliPath}" check "${fileInfo.filePath}"`;

        exec(cmd, { cwd: fileInfo.cwd, env: toolchain.env }, (error, stdout, stderr) => {
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

        const pythonPath = this.resolver.getPythonPath('plan');
        const toolchain = this.resolver.getPlanCli(fileInfo.cwd);
        const cmd = `"${pythonPath}" "${toolchain.cliPath}" python "${fileInfo.filePath}"`;

        exec(cmd, { cwd: fileInfo.cwd, env: toolchain.env }, (error, stdout, stderr) => {
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
