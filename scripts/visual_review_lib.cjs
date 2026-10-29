/* Pure helpers for scripts/visual_review.cjs. No browser, no filesystem: unit-tested in tests/js. */
'use strict';

/** Compare two RGBA buffers of equal width over their common height.
 * A pixel counts as changed when any channel differs by more than `tolerance`
 * (anti-aliasing and font rasterisation noise stay below it).
 * Returns {changed, compared, ratio, box} where box is the bounding box of changes or null. */
function diffPixels(a, b, width, heightA, heightB, tolerance = 24) {
  const height = Math.min(heightA, heightB);
  let changed = 0, top = -1, bottom = -1, left = width, right = -1;
  for (let y = 0; y < height; y++) {
    const row = y * width * 4;
    for (let x = 0; x < width; x++) {
      const i = row + x * 4;
      if (Math.abs(a[i] - b[i]) > tolerance || Math.abs(a[i + 1] - b[i + 1]) > tolerance ||
          Math.abs(a[i + 2] - b[i + 2]) > tolerance || Math.abs(a[i + 3] - b[i + 3]) > tolerance) {
        changed++;
        if (top < 0) top = y;
        bottom = y;
        if (x < left) left = x;
        if (x > right) right = x;
      }
    }
  }
  const compared = width * height;
  // Rows that exist on only one side are changed content as well.
  const extraRows = Math.abs(heightA - heightB);
  if (extraRows > 0) {
    changed += extraRows * width;
    if (top < 0) top = height;
    bottom = Math.max(heightA, heightB) - 1;
    left = 0; right = width - 1;
  }
  const total = compared + extraRows * width;
  return {
    changed,
    compared: total,
    ratio: total ? changed / total : 0,
    box: top < 0 ? null : {x: left, y: top, width: right - left + 1, height: bottom - top + 1},
  };
}

/** Where the main learning content starts, in screens (1 = bottom of the first screen). */
function screensDown(top, viewportHeight) {
  return top == null ? null : Math.round((top / viewportHeight) * 100) / 100;
}

/** Decide whether the main content position regressed.
 * fail  — after is beyond the limit and either before was within it, or it moved down by more than a screen;
 * warn  — after is beyond the limit, but it already was before (pre-existing problem);
 * ok    — within the limit. Missing main content after the change always fails. */
function mainContentVerdict({before, after, viewportHeight, maxScreens}) {
  if (after == null) return {status: before == null ? 'warn' : 'fail', reason: 'главное содержание не найдено'};
  const limit = maxScreens * viewportHeight;
  if (after <= limit) return {status: 'ok', reason: ''};
  const wasWithin = before != null && before <= limit;
  const movedFar = before != null && after - before > viewportHeight;
  const where = `начинается на ${screensDown(after, viewportHeight)} экрана (допустимо до ${maxScreens})`;
  if (wasWithin || movedFar || before == null) return {status: 'fail', reason: where};
  return {status: 'warn', reason: `${where}; так было и до изменений`};
}

/** Problems that appear only after the change are regressions; pre-existing ones are warnings. */
function newProblems(beforeList, afterList) {
  const seen = new Set(beforeList);
  return afterList.filter(item => !seen.has(item));
}

const STATUS_ICON = {fail: '❌', warn: '⚠️', ok: '✅'};

function percent(ratio) {
  if (ratio === 0) return '0%';
  if (ratio < 0.001) return '<0.1%';
  return `${(ratio * 100).toFixed(1)}%`;
}

/** Markdown summary for the job summary and the pull request comment. */
function buildSummary(results, {runUrl = '', baseLabel = 'main', headLabel = 'PR'} = {}) {
  const worst = results.some(r => r.status === 'fail') ? 'fail' : results.some(r => r.status === 'warn') ? 'warn' : 'ok';
  const changedPages = results.filter(r => r.diff && r.diff.ratio > 0).length;
  const lines = [
    '<!-- visual-review -->',
    `## ${STATUS_ICON[worst]} Визуальная проверка: ${baseLabel} → ${headLabel}`,
    '',
    worst === 'fail'
      ? '**Есть поломки, которые появились в этом PR.** Подробности — в строках с ❌.'
      : worst === 'warn'
        ? 'Новых поломок нет. Есть старые проблемы (⚠️), они были и до этого PR.'
        : 'Новых поломок нет.',
    `Изменился вид ${changedPages} из ${results.length} снимков. Изменения не всегда ошибка: посмотрите картинки «до/после» в артефакте **visual-review**.`,
    '',
    '| | Страница | Ширина | Изменилось | Высота страницы | Главное начинается (экранов) | Замечания |',
    '|---|---|---|---|---|---|---|',
  ];
  for (const r of results) {
    const height = r.height ? (r.height.before === r.height.after ? `${r.height.after}px` : `${r.height.before} → ${r.height.after}px`) : '—';
    const main = r.main ? `${r.main.before ?? '—'} → ${r.main.after ?? '—'}` : '—';
    lines.push(`| ${STATUS_ICON[r.status]} | ${r.title} | ${r.width} | ${r.diff ? percent(r.diff.ratio) : '—'} | ${height} | ${main} | ${(r.notes || []).join('; ') || ''} |`);
  }
  if (runUrl) lines.push('', `Снимки и разница по пикселям: [запуск проверки](${runUrl}) → Artifacts → **visual-review** (откройте \`index.html\`).`);
  return lines.join('\n') + '\n';
}

module.exports = {diffPixels, screensDown, mainContentVerdict, newProblems, buildSummary, percent};
