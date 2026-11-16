"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const { test } = require("node:test");
const ts = require("typescript");

// Use the existing TypeScript compiler; no frontend test dependency is needed.
const source = ts.transpileModule(
  fs.readFileSync(path.join(__dirname, "../src/lib/preferences.ts"), "utf8"),
  { compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2020 } },
).outputText;

function harness({ entries = {}, denied = false, bridge } = {}) {
  const storage = new Map(Object.entries(entries));
  const module = { exports: {} };
  const root = { dataset: {} };
  const meta = {};
  vm.runInNewContext(source, {
    module, exports: module.exports,
    require: () => ({ getDesktopBridge: () => bridge }),
    window: { localStorage: {
      getItem: (key) => storage.get(key) ?? null,
      setItem: (key, value) => {
        if (denied) throw new Error("Storage denied");
        storage.set(key, value);
      },
    } },
    document: { documentElement: root, querySelector: () => ({
      setAttribute: (key, value) => { meta[key] = value; },
    }) },
    getComputedStyle: () => ({ getPropertyValue: (key) =>
      key === "--color-surface-canvas" ? "#123456" : "#abcdef",
    }),
  });
  return { api: module.exports, storage, root, meta };
}

test("browser defaults and legacy collapsed preference are preserved", async () => {
  assert.equal((await harness().api.loadPreferences()).theme, "light");
  const h = harness({ entries: { "surrosim.sidebar.collapsed": "1" } });
  assert.equal((await h.api.loadPreferences()).sidebarCollapsed, true);
});

test("browser theme and sidebar round-trip together", async () => {
  const h = harness();
  await h.api.savePreferences({ theme: "black", sidebarCollapsed: true });
  const loaded = await h.api.loadPreferences();
  assert.equal(loaded.theme, "black");
  assert.equal(loaded.sidebarCollapsed, true);
});

test("invalid and corrupt saved values fall back safely", async () => {
  for (const saved of ["{broken", "null", '{"theme":"system","sidebarCollapsed":"yes"}']) {
    const h = harness({ entries: { "surrosim.preferences": saved } });
    const loaded = await h.api.loadPreferences();
    assert.equal(loaded.theme, "light");
    assert.equal(loaded.sidebarCollapsed, false);
  }
});

test("storage failures reject instead of reporting a saved choice", async () => {
  const h = harness({ denied: true });
  await assert.rejects(h.api.savePreferences({ theme: "black", sidebarCollapsed: false }), /Storage denied/);
});

test("desktop persistence uses the narrow bridge, not browser storage", async () => {
  let saved;
  let colors;
  const h = harness({ denied: true, bridge: {
    getPreferences: async () => ({ theme: "black", sidebarCollapsed: true }),
    savePreferences: async (value) => { saved = value; },
    setAppearance: async (value) => { colors = value; },
  } });
  assert.equal((await h.api.loadPreferences()).theme, "black");
  await h.api.savePreferences({ theme: "light", sidebarCollapsed: false });
  assert.equal(saved.theme, "light");
  await h.api.applyTheme("black");
  assert.equal(h.root.dataset.theme, "black");
  assert.equal(h.meta.content, "#123456");
  assert.equal(colors.canvas, "#123456");
  assert.equal(colors.ink, "#abcdef");
});

const css = fs.readFileSync(path.join(__dirname, "../src/tokens.css"), "utf8");
const tokens = (block) => Object.fromEntries(
  Array.from(block.matchAll(/(--color-[\w-]+):\s*([^;]+);/g), (match) => [match[1], match[2].trim()]),
);
const light = tokens(css.split('[data-theme="black"]')[0]);
const black = tokens(css.split('[data-theme="black"]')[1]);

function contrast(a, b) {
  const luminance = (hex) => {
    const channels = [1, 3, 5].map((offset) => parseInt(hex.slice(offset, offset + 2), 16) / 255);
    const [r, g, blue] = channels.map((v) => v <= 0.04045 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4);
    return r * 0.2126 + g * 0.7152 + blue * 0.0722;
  };
  const x = luminance(a), y = luminance(b);
  return (Math.max(x, y) + 0.05) / (Math.min(x, y) + 0.05);
}

test("Light and Black map exactly the same color roles", () => {
  assert.deepEqual(Object.keys(black).sort(), Object.keys(light).sort());
});

test("theme text, status, actions, and focus meet contrast targets", () => {
  for (const [theme, mapping] of [["light", light], ["black", black]]) {
    const ratio = (fore, back) => contrast(mapping[`--color-${fore}`], mapping[`--color-${back}`]);
    for (const surface of ["surface-canvas", "surface-default", "surface-subtle"]) {
      for (const text of ["text-primary", "text-muted", "link", "accent-strong"]) {
        assert.ok(ratio(text, surface) >= 4.5, `${theme}: ${text}/${surface}`);
      }
      assert.ok(ratio("focus-ring", surface) >= 3, `${theme}: focus/${surface}`);
    }
    assert.ok(ratio("action-primary-text", "action-primary") >= 4.5, `${theme}: action`);
    assert.ok(ratio("action-primary-text", "action-primary-hover") >= 4.5, `${theme}: action hover`);
    assert.ok(ratio("accent-ink", "accent-soft") >= 4.5, `${theme}: selection`);
    for (const tone of ["success", "warning", "danger", "info"]) {
      assert.ok(ratio(`feedback-${tone}`, `feedback-${tone}-soft`) >= 4.5, `${theme}: ${tone}`);
    }
  }
});
