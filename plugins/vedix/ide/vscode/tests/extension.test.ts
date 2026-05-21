// tests/extension.test.ts — Minimal smoke test for the Vedix extension entry.
//
// We avoid spinning up a full vscode-test host here (that requires an installed
// VS Code binary in CI); instead we just verify that the bundled extension
// module exports the standard `activate` / `deactivate` lifecycle functions.
// CI will run `npm run compile` first, then this test against `out/extension.js`.

import * as assert from "node:assert";
import { describe, it } from "node:test";

describe("vedix extension entrypoint", () => {
  it("exports activate() and deactivate()", async () => {
    const mod = await import("../src/extension");
    assert.strictEqual(typeof mod.activate, "function", "activate should be a function");
    assert.strictEqual(typeof mod.deactivate, "function", "deactivate should be a function");
  });
});
