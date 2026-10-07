"use strict";
var __createBinding = (this && this.__createBinding) || (Object.create ? (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    var desc = Object.getOwnPropertyDescriptor(m, k);
    if (!desc || ("get" in desc ? !m.__esModule : desc.writable || desc.configurable)) {
      desc = { enumerable: true, get: function() { return m[k]; } };
    }
    Object.defineProperty(o, k2, desc);
}) : (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    o[k2] = m[k];
}));
var __setModuleDefault = (this && this.__setModuleDefault) || (Object.create ? (function(o, v) {
    Object.defineProperty(o, "default", { enumerable: true, value: v });
}) : function(o, v) {
    o["default"] = v;
});
var __importStar = (this && this.__importStar) || (function () {
    var ownKeys = function(o) {
        ownKeys = Object.getOwnPropertyNames || function (o) {
            var ar = [];
            for (var k in o) if (Object.prototype.hasOwnProperty.call(o, k)) ar[ar.length] = k;
            return ar;
        };
        return ownKeys(o);
    };
    return function (mod) {
        if (mod && mod.__esModule) return mod;
        var result = {};
        if (mod != null) for (var k = ownKeys(mod), i = 0; i < k.length; i++) if (k[i] !== "default") __createBinding(result, mod, k[i]);
        __setModuleDefault(result, mod);
        return result;
    };
})();
Object.defineProperty(exports, "__esModule", { value: true });
exports.NdotController = void 0;
const vscode = __importStar(require("vscode"));
const child_process_1 = require("child_process");
const path = __importStar(require("path"));
class NdotController {
    constructor(resolver) {
        this.resolver = resolver;
        this.outputChannel = vscode.window.createOutputChannel('N-DOT Toolchain');
    }
    registerCommands(context) {
        context.subscriptions.push(vscode.commands.registerCommand('ndot.run', (uri) => this.run(uri)), vscode.commands.registerCommand('ndot.build', (uri) => this.build(uri)), vscode.commands.registerCommand('ndot.check', (uri) => this.check(uri)), vscode.commands.registerCommand('ndot.disassemble', (uri) => this.disassemble(uri)), vscode.commands.registerCommand('ndot.assemble', (uri) => this.assemble(uri)));
    }
    getTargetFile(allowedExts = ['.ndot', '.ndasm'], uri) {
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
    run(uri) {
        const fileInfo = this.getTargetFile(['.ndot', '.ndasm'], uri);
        if (!fileInfo)
            return;
        const config = vscode.workspace.getConfiguration('ndot');
        const pythonPath = this.resolver.getPythonPath('ndot');
        const toolchain = this.resolver.getNdotCli(fileInfo.cwd);
        const allowFiles = config.get('allowFiles', false) ? ' --allow-files' : '';
        const allowNetwork = config.get('allowNetwork', false) ? ' --allow-network' : '';
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
    build(uri) {
        const fileInfo = this.getTargetFile(['.ndot'], uri);
        if (!fileInfo)
            return;
        const pythonPath = this.resolver.getPythonPath('ndot');
        const toolchain = this.resolver.getNdotCli(fileInfo.cwd);
        const defaultOut = fileInfo.filePath.replace(/\.ndot$/, '.py');
        vscode.window.showInputBox({
            prompt: 'Output Python file path',
            value: defaultOut
        }).then(outPath => {
            if (!outPath)
                return;
            const cmd = `"${pythonPath}" "${toolchain.cliPath}" build "${fileInfo.filePath}" -o "${outPath}"`;
            this.outputChannel.show(true);
            this.outputChannel.appendLine(`[N-DOT Build] ${cmd}`);
            (0, child_process_1.exec)(cmd, { cwd: fileInfo.cwd, env: toolchain.env }, (error, stdout, stderr) => {
                if (error) {
                    this.outputChannel.appendLine(`[Error] ${stderr || stdout}`);
                    vscode.window.showErrorMessage(`N-DOT build failed: ${stderr || stdout}`);
                }
                else {
                    this.outputChannel.appendLine(`[Success] ${stdout.trim()}`);
                    vscode.window.showInformationMessage(`Successfully built ${path.basename(outPath)}`);
                }
            });
        });
    }
    check(uri) {
        const fileInfo = this.getTargetFile(['.ndot'], uri);
        if (!fileInfo)
            return;
        const pythonPath = this.resolver.getPythonPath('ndot');
        const toolchain = this.resolver.getNdotCli(fileInfo.cwd);
        const cmd = `"${pythonPath}" "${toolchain.cliPath}" check "${fileInfo.filePath}"`;
        (0, child_process_1.exec)(cmd, { cwd: fileInfo.cwd, env: toolchain.env }, (error, stdout, stderr) => {
            if (error) {
                vscode.window.showErrorMessage(`N-DOT Check Failed: ${(stderr || stdout).trim()}`);
            }
            else {
                vscode.window.showInformationMessage('N-DOT check passed with 0 errors.');
            }
        });
    }
    disassemble(uri) {
        const fileInfo = this.getTargetFile(['.ndot'], uri);
        if (!fileInfo)
            return;
        const pythonPath = this.resolver.getPythonPath('ndot');
        const toolchain = this.resolver.getNdotCli(fileInfo.cwd);
        const cmd = `"${pythonPath}" "${toolchain.cliPath}" dis "${fileInfo.filePath}"`;
        (0, child_process_1.exec)(cmd, { cwd: fileInfo.cwd, env: toolchain.env }, (error, stdout, stderr) => {
            if (error) {
                vscode.window.showErrorMessage(`N-DOT disassembly failed: ${(stderr || stdout).trim()}`);
            }
            else {
                vscode.workspace.openTextDocument({
                    content: stdout,
                    language: 'ndasm'
                }).then(doc => {
                    vscode.window.showTextDocument(doc, { preview: true, viewColumn: vscode.ViewColumn.Beside });
                });
            }
        });
    }
    assemble(uri) {
        const fileInfo = this.getTargetFile(['.ndasm'], uri);
        if (!fileInfo)
            return;
        const pythonPath = this.resolver.getPythonPath('ndot');
        const toolchain = this.resolver.getNdotCli(fileInfo.cwd);
        const defaultOut = fileInfo.filePath.replace(/\.ndasm$/, '.ndot');
        vscode.window.showInputBox({
            prompt: 'Output .ndot file path',
            value: defaultOut
        }).then(outPath => {
            if (!outPath)
                return;
            const cmd = `"${pythonPath}" "${toolchain.cliPath}" asm "${fileInfo.filePath}" -o "${outPath}"`;
            this.outputChannel.show(true);
            this.outputChannel.appendLine(`[N-DOT Assemble] ${cmd}`);
            (0, child_process_1.exec)(cmd, { cwd: fileInfo.cwd, env: toolchain.env }, (error, stdout, stderr) => {
                if (error) {
                    this.outputChannel.appendLine(`[Error] ${stderr || stdout}`);
                    vscode.window.showErrorMessage(`Assembly failed: ${stderr || stdout}`);
                }
                else {
                    this.outputChannel.appendLine(`[Success] ${stdout.trim()}`);
                    vscode.window.showInformationMessage(`Successfully assembled ${path.basename(outPath)}`);
                }
            });
        });
    }
}
exports.NdotController = NdotController;
//# sourceMappingURL=ndot.js.map