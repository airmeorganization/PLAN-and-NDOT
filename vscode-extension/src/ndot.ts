import * as vscode from 'vscode';
import { exec } from 'child_process';
import * as path from 'path';
import { ToolchainResolver } from './toolchain';

export class NdotController {
    private outputChannel: vscode.OutputChannel;

    constructor(private resolver: ToolchainResolver) {
        this.outputChannel = vscode.window.createOutputChannel('N-DOT Toolchain');
    }

    public registerCommands(context: vscode.ExtensionContext): void {
        context.subscriptions.push(
            vscode.commands.registerCommand('ndot.run', (uri?: vscode.Uri) => this.run(uri)),
            vscode.commands.registerCommand('ndot.build', (uri?: vscode.Uri) => this.build(uri)),
            vscode.commands.registerCommand('ndot.check', (uri?: vscode.Uri) => this.check(uri)),
            vscode.commands.registerCommand('ndot.disassemble', (uri?: vscode.Uri) => this.disassemble(uri)),
            vscode.commands.registerCommand('ndot.assemble', (uri?: vscode.Uri) => this.assemble(uri))
        );
    }

    private getTargetFile(allowedExts: string[] = ['.ndot', '.ndasm'], uri?: vscode.Uri): { filePath: string; cwd: string; ext: string } | null {
        let targetUri = uri;
        if (!targetUri) {
            const editor = vscode.window.activeTextEditor;
            if (editor) {
                targetUri = editor.document.uri;
            }
        }
        if (!targetUri) {
            vscode.window.showErrorMessage('Please open or select an N-DOT (.ndot or .ndasm) file first.');
            return null;
        }
        const filePath = targetUri.fsPath;
        const ext = path.extname(filePath).toLowerCase();
        if (!allowedExts.includes(ext)) {
            vscode.window.showErrorMessage(`Selected file must have extension ${allowedExts.join(' or ')}.`);
            return null;
        }
        const workspaceFolder = vscode.workspace.getWorkspaceFolder(targetUri);
        const cwd = workspaceFolder ? workspaceFolder.uri.fsPath : path.dirname(filePath);
        return { filePath, cwd, ext };
    }

    public run(uri?: vscode.Uri): void {
        const fileInfo = this.getTargetFile(['.ndot', '.ndasm'], uri);
        if (!fileInfo) return;

        const config = vscode.workspace.getConfiguration('ndot');
        const pythonPath = this.resolver.getPythonPath('ndot');
        const toolchain = this.resolver.getNdotCli(fileInfo.cwd);

        const allowFiles = config.get<boolean>('allowFiles', false) ? ' --allow-files' : '';
        const allowNetwork = config.get<boolean>('allowNetwork', false) ? ' --allow-network' : '';

        // If .ndasm, assemble first or run directly
        let targetFile = fileInfo.filePath;
        let setupCmd = '';
        if (fileInfo.ext === '.ndasm') {
            const tempNdot = fileInfo.filePath.replace(/\.ndasm$/, '.ndot');
            setupCmd = `"${pythonPath}" "${toolchain.cliPath}" asm "${fileInfo.filePath}" -o "${tempNdot}" && `;
            targetFile = tempNdot;
        }

        const cmd = `${setupCmd}"${pythonPath}" "${toolchain.cliPath}" run "${targetFile}"${allowFiles}${allowNetwork}`;

        let terminal = vscode.window.terminals.find(t => t.name === 'N-DOT');
        if (!terminal) {
            terminal = vscode.window.createTerminal({ name: 'N-DOT', cwd: fileInfo.cwd, env: toolchain.env });
        }
        terminal.show();
        terminal.sendText(cmd);
    }

    public build(uri?: vscode.Uri): void {
        const fileInfo = this.getTargetFile(['.ndot'], uri);
        if (!fileInfo) return;

        const pythonPath = this.resolver.getPythonPath('ndot');
        const toolchain = this.resolver.getNdotCli(fileInfo.cwd);
        const defaultOut = fileInfo.filePath.replace(/\.ndot$/, '.py');

        vscode.window.showInputBox({
            prompt: 'Output Python file path',
            value: defaultOut
        }).then(outPath => {
            if (!outPath) return;

            const cmd = `"${pythonPath}" "${toolchain.cliPath}" build "${fileInfo.filePath}" -o "${outPath}"`;
            this.outputChannel.show(true);
            this.outputChannel.appendLine(`[N-DOT Build] ${cmd}`);

            exec(cmd, { cwd: fileInfo.cwd, env: toolchain.env }, (error, stdout, stderr) => {
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

    public check(uri?: vscode.Uri): void {
        const fileInfo = this.getTargetFile(['.ndot'], uri);
        if (!fileInfo) return;

        const pythonPath = this.resolver.getPythonPath('ndot');
        const toolchain = this.resolver.getNdotCli(fileInfo.cwd);
        const cmd = `"${pythonPath}" "${toolchain.cliPath}" check "${fileInfo.filePath}"`;

        exec(cmd, { cwd: fileInfo.cwd, env: toolchain.env }, (error, stdout, stderr) => {
            if (error) {
                vscode.window.showErrorMessage(`N-DOT Check Failed: ${(stderr || stdout).trim()}`);
            } else {
                vscode.window.showInformationMessage('N-DOT check passed with 0 errors.');
            }
        });
    }

    public disassemble(uri?: vscode.Uri): void {
        const fileInfo = this.getTargetFile(['.ndot'], uri);
        if (!fileInfo) return;

        const pythonPath = this.resolver.getPythonPath('ndot');
        const toolchain = this.resolver.getNdotCli(fileInfo.cwd);
        const cmd = `"${pythonPath}" "${toolchain.cliPath}" dis "${fileInfo.filePath}"`;

        exec(cmd, { cwd: fileInfo.cwd, env: toolchain.env }, (error, stdout, stderr) => {
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

    public assemble(uri?: vscode.Uri): void {
        const fileInfo = this.getTargetFile(['.ndasm'], uri);
        if (!fileInfo) return;

        const pythonPath = this.resolver.getPythonPath('ndot');
        const toolchain = this.resolver.getNdotCli(fileInfo.cwd);
        const defaultOut = fileInfo.filePath.replace(/\.ndasm$/, '.ndot');

        vscode.window.showInputBox({
            prompt: 'Output .ndot file path',
            value: defaultOut
        }).then(outPath => {
            if (!outPath) return;

            const cmd = `"${pythonPath}" "${toolchain.cliPath}" asm "${fileInfo.filePath}" -o "${outPath}"`;
            this.outputChannel.show(true);
            this.outputChannel.appendLine(`[N-DOT Assemble] ${cmd}`);

            exec(cmd, { cwd: fileInfo.cwd, env: toolchain.env }, (error, stdout, stderr) => {
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
