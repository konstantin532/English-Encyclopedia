const {test} = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const review = require("../../static/js/speech-review.js");
const source = fs.readFileSync(path.join(__dirname, "../../static/js/speech-review.js"), "utf8");

test("an independent oral response is revisited at longer spacing intervals", () => {
  const now = Date.parse("2026-10-18T12:00:00Z");
  const a = review.nextState(null, "good", now);
  assert.equal(a.stage, 1);
  assert.equal(a.next_review_at, "2026-10-19T12:00:00.000Z");
  const b = review.nextState(a, "good", now);
  assert.equal(b.stage, 2);
  assert.equal(b.next_review_at, "2026-10-21T12:00:00.000Z");
  const c = review.nextState(b, "good", now);
  assert.equal(c.next_review_at, "2026-10-25T12:00:00.000Z");
  const d = review.nextState(c, "good", now);
  assert.equal(d.next_review_at, "2026-11-01T12:00:00.000Z");
});

test("difficulty makes a segment easier to review without penalizing speech accents", () => {
  const now = Date.parse("2026-10-18T12:00:00Z");
  const p = review.nextState({stage: 4, attempts: 3}, "hard", now);
  assert.equal(p.stage, 3);
  assert.equal(p.attempts, 4);
  assert.equal(p.next_review_at, "2026-10-19T12:00:00.000Z");
  const repeat = review.nextState(p, "again", now);
  assert.equal(repeat.stage, 0);
  assert.equal(repeat.due, true);
  assert.equal(repeat.next_review_at, "2026-10-18T12:00:00.000Z");
  assert.throws(() => review.nextState(null, "perfect", now));
});

test("next due cycles past completed segments, preferring new or genuinely due items", () => {
  const now = Date.parse("2026-10-18T12:00:00Z");
  const future = {next_review_at: "2026-10-19T12:00:00.000Z"};
  const due = {next_review_at: "2026-10-17T12:00:00.000Z"};
  assert.equal(review.nextDue([future, due, future], 3, 0, now), 1);
  assert.equal(review.nextDue([future, future, null], 3, 0, now), 2);
  assert.equal(review.nextDue([future, future, future], 3, 0, now), null);
});

test("ratings, not recordings, are the only data submitted to the private endpoint", () => {
  assert.match(source, /JSON\.stringify\(\{key, index, rating\}\)/);
  assert.match(source, /credentials: "same-origin"/);
  assert.match(source, /X-CSRFToken/);
  assert.doesNotMatch(source, /getUserMedia|MediaRecorder|FormData/);
  assert.doesNotMatch(source, /localStorage|sessionStorage/);
  assert.match(source, /signedIn/);
});

test("full speech controls keep private reviews while weeks use compact recording", () => {
  const root = path.join(__dirname, "../..");
  const controls = fs.readFileSync(path.join(root, "templates/components/speech_studio_controls.html"), "utf8");
  assert.match(controls, /data-speech-grade="again"/);
  assert.match(controls, /data-speech-grade="hard"/);
  assert.match(controls, /data-speech-grade="good"/);
  assert.match(controls, /data-speech-next-review/);
  assert.match(controls, /\{% if user\.is_authenticated %\}<a[^>]+learning:speech_review/);
  for (const file of ["templates/lessons/detail.html", "templates/poems/detail.html"]) {
    const template = fs.readFileSync(path.join(root, file), "utf8");
    assert.match(template, /speech-review\.js/);
    assert.match(template, /include "components\/speech_studio_controls\.html"/);
  }
  const week = fs.readFileSync(path.join(root, "templates/curriculum/week.html"), "utf8");
  assert.match(week, /include "components\/twister_trainer\.html" with week_mode=True/);
  assert.match(week, /speech-studio\.js/);
  assert.doesNotMatch(week, /speech-review\.js/);

  const twister = fs.readFileSync(path.join(root, "templates/components/twister_trainer.html"), "utf8");
  const branches = twister.match(/\{% if week_mode %\}([\s\S]*?)\{% else %\}([\s\S]*)/);
  assert.ok(branches, "twister training must distinguish compact weeks and full speech controls");
  const [, compact, full] = branches;
  assert.match(compact, /include "components\/speech_recorder\.html"/);
  assert.doesNotMatch(compact, /speech_studio_controls|data-speech-studio|data-speech-review/);
  assert.match(full, /data-speech-key="twister:/);
  assert.match(full, /include "components\/speech_studio_controls\.html"/);

  const recorder = fs.readFileSync(path.join(root, "templates/components/speech_recorder.html"), "utf8");
  assert.match(recorder, /data-speech-record>Записать себя/);
  assert.match(recorder, /Запись не отправляется на сервер\./);
});
