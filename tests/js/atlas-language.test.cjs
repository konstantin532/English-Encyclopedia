const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const atlas = require("../../static/js/atlas-language.js");
const root = path.resolve(__dirname, "../..");
const read = (p) => fs.readFileSync(path.join(root, p), "utf8");

test("language atlas exposes accurate explanations and ignores unknown roles", () => {
  assert.match(atlas.describeRole("subject"), /подлежащее/);
  assert.match(atlas.describeRole("be"), /am/);
  assert.match(atlas.describeRole("place"), /без предлога/);
  assert.equal(atlas.describeRole("__proto__"), null);
  assert.equal(atlas.describeRole("unknown"), null);
});

test("the grammar controls animate only when motion is explicitly full", () => {
  assert.equal(atlas.canAnimate("full", false), true);
  assert.equal(atlas.canAnimate("balanced", false), false);
  assert.equal(atlas.canAnimate("minimal", false), false);
  assert.equal(atlas.canAnimate("full", true), false);
});

test("the design progressively enhances rather than hiding text or changing markers", () => {
  const home = read("templates/core/home.html");
  const base = read("templates/base.html");
  const css = read("static/scss/editorial-world.scss");
  assert.match(home, /data-language-atlas/);
  assert.match(home, /data-atlas-explanation/);
  assert.match(home, /data-atlas-role="subject"/);
  assert.match(home, /data-atlas-role="be"/);
  assert.match(home, /data-atlas-role="place"/);
  assert.match(base, /js\/atlas-language\.js/);
  assert.match(css, /\.studio-phrase-roles \.atlas-grammar-control:focus-visible/);
  assert.doesNotMatch(css, /--class-\d+\s*:/);
  assert.doesNotMatch(css, /grid-template-columns/);
});

test("all fourteen original SVG covers exist and catalogue/chapter reference them", () => {
  const titles = ["Знакомство","дом","кафе","Семья","Магазин","обычный","работает","пройти","Телефон","Выходные","врача","почте","Курсы","автобусе"];
  for (let i = 1; i <= 14; i++) {
    const name = "static/img/studio/a1-week-" + String(i).padStart(2, "0") + ".svg";
    const svg = read(name);
    assert.match(svg, /<svg[^>]+viewBox="0 0 1440 810"/);
    assert.match(svg, new RegExp(titles[i - 1], "i"));
    assert.doesNotMatch(svg, /<script|<foreignObject|https?:\/\//);
  }
  const view = read("apps/curriculum/views.py");
  const hero = read("templates/components/week_hero.html");
  const catalog = read("templates/curriculum/level.html");
  assert.match(view, /a1_atlas_cover/);
  assert.match(view, /static\(f"img\/studio\/a1-week-/);
  assert.match(hero, /week-hero-atlas/);
  assert.match(hero, /cafe-morning\.webp/);
  assert.match(catalog, /week-card-art/);
});
