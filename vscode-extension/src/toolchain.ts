import * as vscode from 'vscode';
import * as path from 'path';
import * as fs from 'fs';

export interface ToolchainInfo {
    cliPath: string;
    compilerDir: string;
    env: NodeJS.ProcessEnv;
}

export class ToolchainResolver {
    constructor(private context: vscode.ExtensionContext) {}

    public getPythonPath(language: 'plan' | 'ndot'): string {
        const config = vscode.workspace.getConfiguration(language);
        return config.get<string>('pythonPath', 'python');
    }

    public getPlanCli(workspaceCwd?: string): ToolchainInfo {
        // 1. If workspace has local plan/cli.py, prioritize it for language development
        if (workspaceCwd) {
            const localCli = path.join(workspaceCwd, 'plan', 'cli.py');
            if (fs.existsSync(localCli)) {
                return {
                    cliPath: localCli,
                    compilerDir: workspaceCwd,
                    env: this.buildEnv(workspaceCwd)
                };
            }
        }

        // 2. Fall back to bundled compiler in extension
        const bundledDir = path.join(this.context.extensionPath, 'compiler');
        const bundledCli = path.join(bundledDir, 'plan', 'cli.py');
        return {
            cliPath: bundledCli,
            compilerDir: bundledDir,
            env: this.buildEnv(bundledDir)
        };
    }

    public getNdotCli(workspaceCwd?: string): ToolchainInfo {
        // 1. If workspace has local ndot/cli.py, prioritize it for language development
        if (workspaceCwd) {
            const localCli = path.join(workspaceCwd, 'ndot', 'cli.py');
            if (fs.existsSync(localCli)) {
                return {
                    cliPath: localCli,
                    compilerDir: workspaceCwd,
                    env: this.buildEnv(workspaceCwd)
                };
            }
        }

        // 2. Fall back to bundled compiler in extension
        const bundledDir = path.join(this.context.extensionPath, 'compiler');
        const bundledCli = path.join(bundledDir, 'ndot', 'cli.py');
        return {
            cliPath: bundledCli,
            compilerDir: bundledDir,
            env: this.buildEnv(bundledDir)
        };
    }

    private buildEnv(compilerDir: string): NodeJS.ProcessEnv {
        const env = { ...process.env };
        const existingPyPath = env.PYTHONPATH || '';
        env.PYTHONPATH = existingPyPath ? `${compilerDir}${path.delimiter}${existingPyPath}` : compilerDir;
        return env;
    }
}
