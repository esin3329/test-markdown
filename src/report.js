const STATUS_LABELS = { ok: 'OK', missing: 'MISSING', skipped: 'SKIPPED' };

export function summarize(results) {
  const counts = { ok: 0, missing: 0, skipped: 0 };
  for (const result of results) counts[result.status] += 1;
  return counts;
}

function escapeHtml(value) {
  return String(value).replaceAll('&', '&amp;').replaceAll('<', '&lt;').replaceAll('>', '&gt;').replaceAll('"', '&quot;').replaceAll("'", '&#39;');
}

export function renderText(report) {
  const counts = summarize(report.results);
  const lines = [
    `Files scanned: ${report.filesScanned}`,
    `Links: ${report.results.length} (ok ${counts.ok}, missing ${counts.missing}, skipped ${counts.skipped})`,
  ];
  for (const result of report.results) {
    lines.push(`${STATUS_LABELS[result.status]} ${result.source}:${result.line} [${result.kind}] ${JSON.stringify(result.target)} — ${result.reason}`);
  }
  return `${lines.join('\n')}\n`;
}

export function renderJson(report) {
  return `${JSON.stringify({ filesScanned: report.filesScanned, counts: summarize(report.results), results: report.results }, null, 2)}\n`;
}

export function renderHtml(report) {
  const counts = summarize(report.results);
  const rows = report.results.map((result) => `      <tr><td>${escapeHtml(result.status)}</td><td>${escapeHtml(result.source)}:${result.line}</td><td>${escapeHtml(result.kind)}</td><td><code>${escapeHtml(result.target)}</code></td><td>${escapeHtml(result.reason)}</td></tr>`).join('\n');
  return `<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Link Doctor report</title>
  <style>
    :root { color-scheme: light dark; font: 16px/1.5 system-ui, sans-serif; }
    body { margin: 2rem auto; padding: 0 1rem; max-width: 72rem; }
    table { border-collapse: collapse; width: 100%; }
    th, td { border: 1px solid #8888; padding: .5rem; text-align: left; overflow-wrap: anywhere; }
    code { white-space: pre-wrap; }
  </style>
</head>
<body>
  <h1>Link Doctor report</h1>
  <p>Files scanned: ${report.filesScanned}. Links: ${report.results.length} (ok ${counts.ok}, missing ${counts.missing}, skipped ${counts.skipped}).</p>
  <table>
    <thead><tr><th>Status</th><th>Location</th><th>Kind</th><th>Target</th><th>Reason</th></tr></thead>
    <tbody>
${rows}
    </tbody>
  </table>
</body>
</html>
`;
}

export function renderReport(report, format = 'text') {
  if (format === 'text') return renderText(report);
  if (format === 'json') return renderJson(report);
  if (format === 'html') return renderHtml(report);
  throw new Error(`Unsupported report format: ${format}`);
}
