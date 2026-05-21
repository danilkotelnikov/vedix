// esbuild.js — bundle the Vedix VS Code extension into dist/extension.js
//
// Usage:
//   node esbuild.js          # one-shot build
//   node esbuild.js --watch  # rebuild on change
//
// Notes:
// - VS Code extensions run inside the Electron renderer's Node.js context, so
//   the bundle target is `node` with `cjs` format.
// - `vscode` is provided by the host and must stay external.

const esbuild = require("esbuild");
const path = require("path");

const watchMode = process.argv.includes("--watch");
const isProd = process.argv.includes("--production");

/** @type {import('esbuild').BuildOptions} */
const buildOptions = {
  entryPoints: [path.join(__dirname, "src", "extension.ts")],
  bundle: true,
  outfile: path.join(__dirname, "dist", "extension.js"),
  external: ["vscode"],
  format: "cjs",
  platform: "node",
  target: "node18",
  sourcemap: !isProd,
  minify: isProd,
  logLevel: "info",
};

async function main() {
  if (watchMode) {
    const ctx = await esbuild.context(buildOptions);
    await ctx.watch();
    console.log("[esbuild] watching for changes...");
  } else {
    await esbuild.build(buildOptions);
    console.log("[esbuild] build complete");
  }
}

main().catch((err) => {
  console.error("[esbuild] build failed:", err);
  process.exit(1);
});
