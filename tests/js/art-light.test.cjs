const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const root = path.resolve(__dirname, "../..");
const light = require("../../static/js/art-light.js");

test("pointer lighting respects motion, accessibility and input capabilities", () => {
  assert.equal(light.canIlluminate("full", false, false, true), true);
  assert.equal(light.canIlluminate("balanced", false, false, true), true);
  assert.equal(light.canIlluminate("minimal", false, false, true), false);
  assert.equal(light.canIlluminate("full", true, false, true), false);
  assert.equal(light.canIlluminate("full", false, true, true), false);
  assert.equal(light.canIlluminate("full", false, false, false), false);
});

test("spotlight coordinates are scoped to the target and clamped", () => {
  const rect = { left: 20, top: 40, width: 200, height: 100 };
  assert.deepEqual(light.relativeLight(120, 65, rect), { x: "50%", y: "25%" });
  assert.deepEqual(light.relativeLight(-80, 999, rect), { x: "0%", y: "100%" });
  assert.deepEqual(light.relativeLight(10, 10, { left: 0, top: 0, width: 0, height: 0 }), { x: "100%", y: "100%" });
});

test("JS and compiled CSS are wired to the existing Sass design system", () => {
  const base = fs.readFileSync(path.join(root, "templates/base.html"), "utf8");
  const scss = fs.readFileSync(path.join(root, "static/scss/art-light.scss"), "utf8");
  const css = fs.readFileSync(path.join(root, "static/css/art-light.css"), "utf8");
  assert.match(base, /static 'css\/art-light\.css'/);
  assert.match(base, /static 'js\/art-light\.js'/);
  assert.match(scss, /@layer ee-polish/);
  assert.match(css, /data-art-hot=true/);
  assert.doesNotMatch(scss, /--class-\d+\s*:/);
  assert.doesNotMatch(scss, /\.mk\s*\{/);
  assert.match(scss, /pointer-events: none/);
});
