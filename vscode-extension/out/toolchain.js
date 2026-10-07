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
exports.ToolchainResolver = void 0;
const vscode = __importStar(require("vscode"));
const path = __importStar(require("path"));
const fs = __importStar(require("fs"));
class ToolchainResolver {
    constructor(context) {
        this.context = context;
    }
    getPythonPath(language) {
        const config = vscode.workspace.getConfiguration(language);
        return config.get('pythonPath', 'python');
    }
    getPlanCli(workspaceCwd) {
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
    getNdotCli(workspaceCwd) {
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
    buildEnv(compilerDir) {
        const env = { ...process.env };
        const existingPyPath = env.PYTHONPATH || '';
        env.PYTHONPATH = existingPyPath ? `${compilerDir}${path.delimiter}${existingPyPath}` : compilerDir;
        return env;
    }
}
exports.ToolchainResolver = ToolchainResolver;
//# sourceMappingURL=toolchain.js.map