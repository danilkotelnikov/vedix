// src/commands.ts — Top-level Vedix commands exposed in the Command Palette.
//
// All commands collect input through showInputBox / showQuickPick, then dispatch
// either to the SaaS API or to the local `vedix` CLI subprocess via api.ts.

import * as vscode from "vscode";
import { newJob, switchVenue, runReproAudit } from "./api";
import { openProgressPanel } from "./progressPanel";

const DISCIPLINES = [
  "chemistry",
  "biology",
  "medicine",
  "physics",
  "mathematics",
  "geology",
  "computer_science",
  "humanities",
];

const LANGUAGES = ["en", "ru", "es", "de", "fr", "zh", "ja"];

export function registerCommands(ctx: vscode.ExtensionContext): void {
  ctx.subscriptions.push(
    vscode.commands.registerCommand("vedix.newManuscript", async () => {
      const topic = await vscode.window.showInputBox({
        prompt: "Research topic",
        placeHolder: "e.g. solvent polarity on Diels-Alder kinetics",
        ignoreFocusOut: true,
      });
      if (!topic) return;

      const discipline = await vscode.window.showQuickPick(DISCIPLINES, {
        placeHolder: "Discipline",
        ignoreFocusOut: true,
      });
      if (!discipline) return;

      const language = await vscode.window.showQuickPick(LANGUAGES, {
        placeHolder: "Manuscript language",
        ignoreFocusOut: true,
      });
      if (!language) return;

      const venue = await vscode.window.showInputBox({
        prompt: "Target venue (e.g. preprint, elsevier:cell-reports-medicine, ieee:transactions)",
        value: "preprint",
        ignoreFocusOut: true,
      });
      if (!venue) return;

      try {
        const r = await newJob({
          topic,
          discipline,
          language,
          venue,
          hypothesis_style: "exploratory",
          experiment_type: "computational",
          primary_metric: "TBD",
          expected_direction: "increase",
          tolerance: 0.05,
        });
        const jobId = r.job_id ?? r.jobId ?? "(unknown)";
        vscode.window.showInformationMessage(`Vedix job ${jobId} queued`);
        if (jobId !== "(unknown)") {
          openProgressPanel(ctx, jobId);
        }
      } catch (err) {
        vscode.window.showErrorMessage(`Vedix: failed to start job — ${(err as Error).message}`);
      }
    }),

    vscode.commands.registerCommand("vedix.switchVenue", async () => {
      const jobId = await vscode.window.showInputBox({
        prompt: "Job ID",
        ignoreFocusOut: true,
      });
      if (!jobId) return;

      const venue = await vscode.window.showInputBox({
        prompt: "Switch to venue (e.g. elsevier:cell-reports-medicine)",
        ignoreFocusOut: true,
      });
      if (!venue) return;

      try {
        await switchVenue(jobId, venue);
        vscode.window.showInformationMessage(`Vedix venue switch: ${venue}`);
      } catch (err) {
        vscode.window.showErrorMessage(`Vedix: venue switch failed — ${(err as Error).message}`);
      }
    }),

    vscode.commands.registerCommand("vedix.reproducibilityAudit", async () => {
      const jobId = await vscode.window.showInputBox({
        prompt: "Job ID",
        ignoreFocusOut: true,
      });
      if (!jobId) return;

      try {
        const r = await runReproAudit(jobId);
        const mismatchCount = r.mismatches?.length ?? 0;
        vscode.window.showInformationMessage(
          `Vedix audit ${r.status}: ${mismatchCount} mismatches`,
        );
      } catch (err) {
        vscode.window.showErrorMessage(`Vedix: audit failed — ${(err as Error).message}`);
      }
    }),

    vscode.commands.registerCommand("vedix.openPanel", async () => {
      const jobId = await vscode.window.showInputBox({
        prompt: "Job ID",
        ignoreFocusOut: true,
      });
      if (jobId) openProgressPanel(ctx, jobId);
    }),
  );
}
