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
exports.PlanController = void 0;
const vscode = __importStar(require("vscode"));
const child_process_1 = require("child_process");
const path = __importStar(require("path"));
class PlanController {
    constructor(resolver) {
        this.resolver = resolver;
        this.outputChannel = vscode.window.createOutputChannel('PLAN Toolchain');
    }
    registerCommands(context) {
        context.subscriptions.push(vscode.commands.registerCommand('plan.run', (uri) => this.run(uri)), vscode.commands.registerCommand('plan.build', (uri) => this.build(uri)), vscode.commands.registerCommand('plan.check', (uri) => this.check(uri)), vscode.commands.registerCommand('plan.toPython', (uri) => this.previewPython(uri)));
    }
    getTargetFile(uri) {
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
    run(uri) {
        const fileInfo = this.getTargetFile(uri);
        if (!fileInfo)
            return;
        const config = vscode.workspace.getConfiguration('plan');
        const pythonPath = this.resolver.getPythonPath('plan');
        const toolchain = this.resolver.getPlanCli(fileInfo.cwd);
        const allowPython = config.get('allowPython', false) ? ' --allow-python' : '';
        const allowAllModules = config.get('allowAllModules', false) ? ' --allow-all-modules' : '';
        const cmd = `"${pythonPath}" "${toolchain.cliPath}" run "${fileInfo.filePath}"${allowPython}${allowAllModules}`;
        let terminal = vscode.window.terminals.find(t => t.name === 'PLAN');
        if (!terminal) {
            terminal = vscode.window.createTerminal({ name: 'PLAN', cwd: fileInfo.cwd, env: toolchain.env });
        }
        terminal.show();
        terminal.sendText(cmd);
    }
    build(uri) {
        const fileInfo = this.getTargetFile(uri);
        if (!fileInfo)
            return;
        const pythonPath = this.resolver.getPythonPath('plan');
        const toolchain = this.resolver.getPlanCli(fileInfo.cwd);
        const defaultOut = fileInfo.filePath.replace(/\.plan$/, '.py');
        vscode.window.showInputBox({
            prompt: 'Output Python file path',
            value: defaultOut
        }).then(outPath => {
            if (!outPath)
                return;
            const cmd = `"${pythonPath}" "${toolchain.cliPath}" build "${fileInfo.filePath}" -o "${outPath}"`;
            this.outputChannel.show(true);
            this.outputChannel.appendLine(`[PLAN Build] ${cmd}`);
            (0, child_process_1.exec)(cmd, { cwd: fileInfo.cwd, env: toolchain.env }, (error, stdout, stderr) => {
                if (error) {
                    this.outputChannel.appendLine(`[Error] ${stderr || stdout}`);
                    vscode.window.showErrorMessage(`PLAN build failed: ${stderr || stdout}`);
                }
                else {
                    this.outputChannel.appendLine(`[Success] ${stdout.trim()}`);
                    vscode.window.showInformationMessage(`Successfully built ${path.basename(outPath)}`);
                }
            });
        });
    }
    check(uri) {
        const fileInfo = this.getTargetFile(uri);
        if (!fileInfo)
            return;
        const pythonPath = this.resolver.getPythonPath('plan');
        const toolchain = this.resolver.getPlanCli(fileInfo.cwd);
        const cmd = `"${pythonPath}" "${toolchain.cliPath}" check "${fileInfo.filePath}"`;
        (0, child_process_1.exec)(cmd, { cwd: fileInfo.cwd, env: toolchain.env }, (error, stdout, stderr) => {
            if (error) {
                vscode.window.showErrorMessage(`PLAN Check Failed: ${(stderr || stdout).trim()}`);
            }
            else {
                vscode.window.showInformationMessage('PLAN check passed with 0 errors.');
            }
        });
    }
    previewPython(uri) {
        const fileInfo = this.getTargetFile(uri);
        if (!fileInfo)
            return;
        const pythonPath = this.resolver.getPythonPath('plan');
        const toolchain = this.resolver.getPlanCli(fileInfo.cwd);
        const cmd = `"${pythonPath}" "${toolchain.cliPath}" python "${fileInfo.filePath}"`;
        (0, child_process_1.exec)(cmd, { cwd: fileInfo.cwd, env: toolchain.env }, (error, stdout, stderr) => {
            if (error) {
                vscode.window.showErrorMessage(`PLAN codegen failed: ${(stderr || stdout).trim()}`);
            }
            else {
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
exports.PlanController = PlanController;
//# sourceMappingURL=plan.js.map