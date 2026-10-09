import assert from 'node:assert/strict';
import { chmod, mkdtemp, mkdir, readFile, symlink, writeFile } from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import { spawnSync } from 'node:child_process';
import test from 'node:test';
import { renderHtml, renderJson, renderText, summarize } from '../src/report.js';

const cli = new URL('../src/cli.js', import.meta.url).pathname;
const sample = {
  filesScanned: 1,
  results: [
    { source: 'docs/a.md', line: 2, target: 'present.md', kind: 'link', status: 'ok', reason: 'file exists' },
    { source: 'docs/a.md', line: 3, target: '<script>alert(1)</script>', kind: 'link', status: 'missing', reason: 'file does not exist' },
    { source: 'docs/a.md', line: 4, target: 'https://example.test/?a=1&b=2', kind: 'link', status: 'skipped', reason: 'external URL' },
  ],
};

async function temporaryDirectory(t) {
  const directory = await mkdtemp(path.join(os.tmpdir(), 'link-doctor-cli-'));
  t.after(async () => {
    const { rm } = await import('node:fs/promises');
    await rm(directory, { recursive: true, force: true });
  });
  return directory;
}

function runCli(args) {
  return spawnSync(process.execPath, [cli, ...args], { encoding: 'utf8' });
}

test('renders accurate counts and JSON contract', () => {
  assert.deepEqual(summarize(sample.results), { ok: 1, missing: 1, skipped: 1 });
  assert.equal(JSON.parse(renderJson(sample)).results[1].target, '<script>alert(1)</script>');
  assert.match(renderText(sample), /MISSING docs\/a\.md:3 \[link\]/);
});

test('escapes report content in a standalone static HTML document', () => {
  const html = renderHtml(sample);
  assert.match(html, /&lt;script&gt;alert\(1\)&lt;\/script&gt;/);
  assert.match(html, /&amp;b=2/);
  assert.doesNotMatch(html, /<script>/i);
  assert.match(html, /<meta charset="utf-8">/);
  assert.doesNotMatch(html, /<script[^>]+src=/i);
});

test('CLI emits text, JSON, and HTML to the selected destination with correct exit codes', async (t) => {
  const root = await temporaryDirectory(t);
  await mkdir(path.join(root, 'docs'));
  await writeFile(path.join(root, 'docs', 'ok.md'), '[good](present.md#missing-section)\n[bad](missing.md)\n');
  await writeFile(path.join(root, 'docs', 'present.md'), 'target');

  const text = runCli([path.join(root, 'docs')]);
  assert.equal(text.status, 1);
  assert.match(text.stdout, /Files scanned: 2/);
  assert.match(text.stdout, /anchor not verified/);
  assert.match(text.stdout, /MISSING ok\.md:2/);

  const json = runCli([path.join(root, 'docs'), '--format', 'json']);
  assert.equal(json.status, 1);
  assert.equal(JSON.parse(json.stdout).results[0].reason, 'file exists; anchor not verified');

  const output = path.join(root, 'report.html');
  const html = runCli([path.join(root, 'docs'), '--format', 'html', '--output', output]);
  assert.equal(html.status, 1);
  assert.equal(html.stdout, '');
  assert.match(await readFile(output, 'utf8'), /anchor not verified/);
});

test('CLI returns 0 for clean documents and 2 for bad arguments, input, and output errors', async (t) => {
  const root = await temporaryDirectory(t);
  const clean = path.join(root, 'clean');
  await mkdir(clean);
  await writeFile(path.join(clean, 'index.md'), '[good](target.md)');
  await writeFile(path.join(clean, 'target.md'), 'target');
  assert.equal(runCli([clean]).status, 0);
  assert.equal(runCli([]).status, 2);
  assert.equal(runCli([path.join(root, 'absent')]).status, 2);
  assert.equal(runCli([clean, '--format', 'bogus']).status, 2);
  const input = path.join(clean, 'index.md');
  const original = await readFile(input, 'utf8');
  const overwrite = runCli([clean, '--format', 'html', '--output', input]);
  assert.equal(overwrite.status, 2);
  assert.equal(await readFile(input, 'utf8'), original);
  const alias = path.join(root, 'alias.html');
  await symlink(input, alias);
  assert.equal(runCli([clean, '--format', 'html', '--output', alias]).status, 2);
  assert.equal(await readFile(input, 'utf8'), original);
  assert.equal(runCli([clean, '--format', 'html', '--output', path.join(root, 'absent', 'report.html')]).status, 2);
});

test('returns exit code 2 when a Markdown input cannot be read', async (t) => {
  if (process.platform === 'win32' || process.getuid?.() === 0) {
    t.skip('permission-based read failure requires a non-root POSIX process');
    return;
  }
  const root = await temporaryDirectory(t);
  const input = path.join(root, 'unreadable.md');
  await writeFile(input, '[link](target.md)');
  await chmod(input, 0);
  const result = runCli([root]);
  await chmod(input, 0o644);
  assert.equal(result.status, 2);
  assert.match(result.stderr, /EACCES|permission denied/i);
});
