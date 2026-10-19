const {test} = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const source = fs.readFileSync(path.join(__dirname, "../../static/js/speech-review.js"), "utf8");

function fixture(signedIn = false, fetchOverride = null) {
  const nodes = new Map();
  class Element {
    constructor(rating = "") {this.dataset = {speechGrade: rating}; this.disabled = false; this.hidden = false; this.textContent = ""; this.listeners = {};}
    addEventListener(name, fn) {this.listeners[name] = fn;}
    dispatch(name) {return this.listeners[name]();}
  }
  const one = s => {if (!nodes.has(s)) nodes.set(s, new Element()); return nodes.get(s);};
  const grades = ["again", "hard", "good"].map(r => new Element(r));
  const root = {
    dataset: {speechMode: "recall", speechIndex: "0", speechPersist: signedIn ? "true" : "false",
      speechEndpoint: "/learning/speech-practice/", speechKey: "lesson:a1-example"},
    listeners: {},
    addEventListener(name, cb) {this.listeners[name] = cb;},
    dispatchEvent(event) {
      if (event.type === "speech:jump") {
        this.dataset.speechIndex = String(event.detail.index);
        this.dataset.speechMode = "recall";
        this.listeners["speech:changed"]?.();
      }
      return true;
    },
    querySelector: one,
    querySelectorAll(selector) {
      if (selector === "[data-speech-entry]") return [new Element(), new Element(), new Element()];
      if (selector === "[data-speech-grade]") return grades;
      return [];
    }
  };
  const calls = [];
  const window = {
    CustomEvent: class {constructor(type, options) {this.type = type;this.detail = options.detail;}},
    async fetch(uri, options) {
      calls.push({uri, options});
      if (fetchOverride) return fetchOverride(uri, options);
      return {
        ok: true,
        async json() {
          if (!options) return {items: []};
          return {index: JSON.parse(options.body).index, rating: JSON.parse(options.body).rating,
            stage: 1, attempts: 1, next_review_at: "2100-10-19T12:00:00Z", due: false};
        }
      };
    }
  };
  const document = {readyState: "complete", cookie: "csrftoken=csrf-token",
    querySelectorAll(selector) {return selector === "[data-speech-studio]" ? [root] : [];}};
  vm.runInNewContext(source, {window, document, module: {exports: {}}});
  return {root, grades, nodes, calls, one};
}

test("anonymous review grades and moves to a new phrase without any network", async () => {
  const app = fixture(false);
  assert.equal(app.one("[data-speech-grades]").hidden, false);
  await app.grades[2].dispatch("click");
  assert.match(app.one("[data-speech-review-status]").textContent, /Новых: 2/);
  app.one("[data-speech-next-review]").dispatch("click");
  assert.equal(app.root.dataset.speechIndex, "1");
  assert.equal(app.calls.length, 0);
  app.root.dataset.speechMode = "see";
  app.root.listeners["speech:changed"]();
  assert.equal(app.one("[data-speech-grades]").hidden, true);
});

test("signed-in review loads only the user's own data and posts CSRF-protected rating", async () => {
  const app = fixture(true);
  await Promise.resolve(); await Promise.resolve(); await Promise.resolve();
  assert.equal(app.calls[0].uri, "/learning/speech-practice/?key=lesson%3Aa1-example");
  await app.grades[0].dispatch("click");
  assert.equal(app.calls.length, 2);
  const payload = JSON.parse(app.calls[1].options.body);
  assert.equal(payload.key, "lesson:a1-example");
  assert.equal(payload.index, 0);
  assert.equal(payload.rating, "again");
  assert.equal(app.calls[1].options.headers["X-CSRFToken"], "csrf-token");
  assert.equal(app.calls[1].options.credentials, "same-origin");
  assert.equal(app.calls[1].options.body.includes("audio"), false);
});

test("late initial GET must not overwrite a rating already saved by POST", async () => {
  let releaseGet;
  const response = {
    index: 0, rating: "good", stage: 1, attempts: 1,
    next_review_at: "2100-10-19T12:00:00Z", due: false
  };
  const app = fixture(true, (_uri, options) => {
    if (!options || options.method !== "POST") return new Promise(resolve => { releaseGet = resolve; });
    return Promise.resolve({ok: true, json: async () => response});
  });
  await app.grades[2].dispatch("click");
  assert.match(app.one("[data-speech-review-status]").textContent, /Следующее повторение:/);
  releaseGet({ok: true, json: async () => ({items: [{
    index: 0, rating: "again", stage: 0, attempts: 0,
    next_review_at: "2000-10-19T12:00:00Z", due: true
  }]})});
  await new Promise(resolve => setImmediate(resolve));
  assert.match(app.one("[data-speech-review-status]").textContent, /Следующее повторение:/);
  assert.doesNotMatch(app.one("[data-speech-review-status]").textContent, /назначен к повторению сейчас/);
});
