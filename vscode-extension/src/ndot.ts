import * as vscode from 'vscode';
import { exec } from 'child_process';
import * as path from 'path';

export class NdotController {
    private outputChannel: vscode.OutputChannel;

    constructor() {
        this.outputChannel = vscode.window.createOutputChannel('N-DOT Toolchain');
    }

    public registerCommands(context: vscode.ExtensionContext): void {
        context.subscriptions.push(
            vscode.commands.registerCommand('ndot.run', () => this.run()),
            vscode.commands.registerCommand('ndot.build', () => this.build()),
            vscode.commands.registerCommand('ndot.check', () => this.check()),
            vscode.commands.registerCommand('ndot.disassemble', () => this.disassemble()),
            vscode.commands.registerCommand('ndot.assemble', () => this.assemble())
        );
    }

    private getActiveFile(allowedExts: string[] = ['.ndot', '.ndasm']): { filePath: string; cwd: string; ext: string } | null {
        const editor = vscode.window.activeTextEditor;
        if (!editor) {
            vscode.window.showErrorMessage('Please open an N-DOT (.ndot or .ndasm) file first.');
            return null;
        }
        const filePath = editor.document.fileName;
        const ext = path.extname(filePath).toLowerCase();
        if (!allowedExts.includes(ext)) {
            vscode.window.showErrorMessage(`Active file must have extension ${allowedExts.join(' or ')}.`);
            return null;
        }
        const workspaceFolder = vscode.workspace.getWorkspaceFolder(editor.document.uri);
        const cwd = workspaceFolder ? workspaceFolder.uri.fsPath : path.dirname(filePath);
        return { filePath, cwd, ext };
    }

    public run(): void {
        const fileInfo = this.getActiveFile();
        if (!fileInfo) return;

        const config = vscode.workspace.getConfiguration('ndot');
        const pythonPath = config.get<string>('pythonPath', 'python');
        const allowFiles = config.get<boolean>('allowFiles', false) ? ' --allow-files' : '';
        const allowNetwork = config.get<boolean>('allowNetwork', false) ? ' --allow-network' : '';

        // If .ndasm, assemble first or run directly
        let targetFile = fileInfo.filePath;
        let setupCmd = '';
        if (fileInfo.ext === '.ndasm') {
            const tempNdot = fileInfo.filePath.replace(/\.ndasm$/, '.ndot');
            setupCmd = `"${pythonPath}" -m ndot.cli asm "${fileInfo.filePath}" -o "${tempNdot}" && `;
            targetFile = tempNdot;
        }

        const cmd = `${setupCmd}"${pythonPath}" -m ndot.cli run "${targetFile}"${allowFiles}${allowNetwork}`;

        let terminal = vscode.window.terminals.find(t => t.name === 'N-DOT');
        if (!terminal) {
            terminal = vscode.window.createTerminal({ name: 'N-DOT', cwd: fileInfo.cwd });
        }
        terminal.show();
        terminal.sendText(cmd);
    }

    public build(): void {
        const fileInfo = this.getActiveFile(['.ndot']);
        if (!fileInfo) return;

        const config = vscode.workspace.getConfiguration('ndot');
        const pythonPath = config.get<string>('pythonPath', 'python');
        const defaultOut = fileInfo.filePath.replace(/\.ndot$/, '.py');

        vscode.window.showInputBox({
            prompt: 'Output Python file path',
            value: defaultOut
        }).then(outPath => {
            if (!outPath) return;

            const cmd = `"${pythonPath}" -m ndot.cli build "${fileInfo.filePath}" -o "${outPath}"`;
            this.outputChannel.show(true);
            this.outputChannel.appendLine(`[N-DOT Build] ${cmd}`);

            exec(cmd, { cwd: fileInfo.cwd }, (error, stdout, stderr) => {
                if (error) {
                    this.outputChannel.appendLine(`[Error] ${stderr || stdout}`);
                    vscode.window.showErrorMessage(`N-DOT build failed: ${stderr || stdout}`);
                } else {
                    this.outputChannel.appendLine(`[Success] ${stdout.trim()}`);
                    vscode.window.showInformationMessage(`Successfully built ${path.basename(outPath)}`);
                }
            });
        });
    }

    public check(): void {
        const fileInfo = this.getActiveFile(['.ndot']);
        if (!fileInfo) return;

        const config = vscode.workspace.getConfiguration('ndot');
        const pythonPath = config.get<string>('pythonPath', 'python');
        const cmd = `"${pythonPath}" -m ndot.cli check "${fileInfo.filePath}"`;

        exec(cmd, { cwd: fileInfo.cwd }, (error, stdout, stderr) => {
            if (error) {
                vscode.window.showErrorMessage(`N-DOT Check Failed: ${(stderr || stdout).trim()}`);
            } else {
                vscode.window.showInformationMessage('N-DOT check passed with 0 errors.');
            }
        });
    }

    public disassemble(): void {
        const fileInfo = this.getActiveFile(['.ndot']);
        if (!fileInfo) return;

        const config = vscode.workspace.getConfiguration('ndot');
        const pythonPath = config.get<string>('pythonPath', 'python');
        const cmd = `"${pythonPath}" -m ndot.cli dis "${fileInfo.filePath}"`;

        exec(cmd, { cwd: fileInfo.cwd }, (error, stdout, stderr) => {
            if (error) {
                vscode.window.showErrorMessage(`N-DOT disassembly failed: ${(stderr || stdout).trim()}`);
            } else {
                vscode.workspace.openTextDocument({
                    content: stdout,
                    language: 'ndasm'
                }).then(doc => {
                    vscode.window.showTextDocument(doc, { preview: true, viewColumn: vscode.ViewColumn.Beside });
                });
            }
        });
    }

    public assemble(): void {
        const fileInfo = this.getActiveFile(['.ndasm']);
        if (!fileInfo) return;

        const config = vscode.workspace.getConfiguration('ndot');
        const pythonPath = config.get<string>('pythonPath', 'python');
        const defaultOut = fileInfo.filePath.replace(/\.ndasm$/, '.ndot');

        vscode.window.showInputBox({
            prompt: 'Output .ndot file path',
            value: defaultOut
        }).then(outPath => {
            if (!outPath) return;

            const cmd = `"${pythonPath}" -m ndot.cli asm "${fileInfo.filePath}" -o "${outPath}"`;
            this.outputChannel.show(true);
            this.outputChannel.appendLine(`[N-DOT Assemble] ${cmd}`);

            exec(cmd, { cwd: fileInfo.cwd }, (error, stdout, stderr) => {
                if (error) {
                    this.outputChannel.appendLine(`[Error] ${stderr || stdout}`);
                    vscode.window.showErrorMessage(`Assembly failed: ${stderr || stdout}`);
                } else {
                    this.outputChannel.appendLine(`[Success] ${stdout.trim()}`);
                    vscode.window.showInformationMessage(`Successfully assembled ${path.basename(outPath)}`);
                }
            });
        });
    }
}
