import * as vscode from 'vscode';
import { PlanController } from './plan';
import { NdotController } from './ndot';
import { DiagnosticsManager } from './diagnostics';

export function activate(context: vscode.ExtensionContext) {
    console.log('PLAN & N-DOT extension is now active.');

    // Controllers
    const planController = new PlanController();
    planController.registerCommands(context);

    const ndotController = new NdotController();
    ndotController.registerCommands(context);

    // Diagnostics
    const diagnosticsManager = new DiagnosticsManager();
    diagnosticsManager.register(context);

    // Status Bar Item
    const statusBarItem = vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Right, 100);
    statusBarItem.text = "$(symbol-misc) PLAN & N-DOT";
    statusBarItem.tooltip = "PLAN and N-DOT Toolchain Active";
    statusBarItem.command = "plan.check";
    statusBarItem.show();
    context.subscriptions.push(statusBarItem);
}

export function deactivate() {
    console.log('PLAN & N-DOT extension deactivated.');
}
