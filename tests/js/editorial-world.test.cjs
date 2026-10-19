const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const root = path.resolve(__dirname, "../..");
const design = require("../../static/js/editorial-world.js");

function read(relative) {
  return fs.readFileSync(path.join(root, relative), "utf8");
}

test("editorial experience is real SCSS + CSS + JS, using existing GSAP", () => {
  const base = read("templates/base.html");
  const scss = read("static/scss/editorial-world.scss");
  const css = read("static/css/editorial-world.css");
  const js = read("static/js/editorial-world.js");
  assert.match(base, /static 'css\/editorial-world\.css'/);
  assert.match(base, /static 'js\/editorial-world\.js'/);
  assert.match(base, /static 'vendor\/gsap\/gsap\.min\.js'/);
  assert.match(scss, /@mixin editorial-raised/);
  assert.match(scss, /@include editorial-raised/);
  assert.match(scss, /@layer ee-polish/);
  assert.match(css, /\.story-script \.script-line\.is-speaking/);
  assert.match(css, /\.story-player\[data-editorial-playing=true\]/);
  assert.match(js, /global\.gsap\.fromTo/);
  assert.match(js, /IntersectionObserver/);
});

test("the optional scene treatment respects reduced motion and high contrast", () => {
  assert.equal(design.allowsOrnamentMotion("full", false, false), true);
  assert.equal(design.allowsOrnamentMotion("balanced", false, false), false);
  assert.equal(design.allowsOrnamentMotion("minimal", false, false), false);
  assert.equal(design.allowsOrnamentMotion("full", true, false), false);
  assert.equal(design.allowsOrnamentMotion("full", false, true), false);
  assert.equal(design.isPlaying("true"), true);
  assert.equal(design.isPlaying("false"), false);
  assert.equal(design.isPlaying(null), false);
});

test("editorial improvements do not redefine the learning marker colors or grids", () => {
  const scss = read("static/scss/editorial-world.scss");
  const base = read("templates/base.html");
  assert.doesNotMatch(scss, /--class-\d+\s*:/);
  assert.doesNotMatch(scss, /\.mk(?:\s|\{|::|:)/);
  assert.doesNotMatch(scss, /grid-template-(?:columns|rows)\s*:/);
  assert.doesNotMatch(scss, /(?:^|\s)(?:width|height|padding|margin|font-size)\s*:/m);
  assert.match(scss, /@media \(max-width: 700px\)/);
  assert.match(scss, /@media \(forced-colors: active\)/);
  assert.match(scss, /@media \(prefers-reduced-motion: reduce\)/);
  assert.match(scss, /pointer-events: none/);
  assert.ok(base.indexOf("css/art-direction.css") < base.indexOf("css/editorial-world.css"));
  assert.ok(base.indexOf("js/motion-system.js") < base.indexOf("js/editorial-world.js"));
});
