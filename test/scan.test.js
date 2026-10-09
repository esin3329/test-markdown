import assert from 'node:assert/strict';
import { mkdtemp, mkdir, readFile, symlink, writeFile } from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import test from 'node:test';
import { scan } from '../src/scan.js';

const fixtureRoot = new URL('./fixtures/scan/', import.meta.url);

async function temporaryDirectory(t) {
  const directory = await mkdtemp(path.join(os.tmpdir(), 'link-doctor-'));
  t.after(async () => {
    const { rm } = await import('node:fs/promises');
    await rm(directory, { recursive: true, force: true });
  });
  return directory;
}

test('scans local file, image, nested, missing, and reference links in stable order', async () => {
  const report = await scan(fixtureRoot.pathname);
  assert.equal(report.filesScanned, 3);
  assert.deepEqual(report.results.map(({ source, line, target, kind, status }) => ({ source, line, target, kind, status })), [
    { source: 'index.md', line: 3, target: 'assets/guide.md', kind: 'link', status: 'ok' },
    { source: 'index.md', line: 4, target: 'assets/missing.md', kind: 'link', status: 'missing' },
    { source: 'index.md', line: 5, target: 'images/pixel.png', kind: 'image', status: 'ok' },
    { source: 'index.md', line: 6, target: 'nested/child.md', kind: 'link', status: 'ok' },
    { source: 'index.md', line: 7, target: 'assets/guide.md', kind: 'link', status: 'ok' },
  ]);
});

test('skips code, resolves encoded and root-relative names, and reports reference use lines', async (t) => {
  const root = await temporaryDirectory(t);
  await mkdir(path.join(root, 'nested'));
  await mkdir(path.join(root, 'images'));
  await writeFile(path.join(root, '한글 guide.md'), 'content');
  await writeFile(path.join(root, 'images', 'pixel.png'), 'image');
  await writeFile(path.join(root, 'nested', 'entry.md'), [
    '[space](../%ED%95%9C%EA%B8%80%20guide.md)',
    '[root](/%ED%95%9C%EA%B8%80%20guide.md)',
    '[ref][label]',
    '![reference image][picture]',
    '[directory](../nested)',
    '',
    '[label]: ../%ED%95%9C%EA%B8%80%20guide.md',
    '[picture]: ../images/pixel.png',
    '`[inline](missing-inline.md)`',
    '```md',
    '[block](missing-block.md)',
    '```',
  ].join('\n'));
  const { results } = await scan(root);
  assert.deepEqual(results.map(({ line, kind, status, reason }) => ({ line, kind, status, reason })), [
    { line: 1, kind: 'link', status: 'ok', reason: 'file exists' },
    { line: 2, kind: 'link', status: 'ok', reason: 'file exists' },
    { line: 3, kind: 'link', status: 'ok', reason: 'file exists' },
    { line: 4, kind: 'image', status: 'ok', reason: 'file exists' },
    { line: 5, kind: 'link', status: 'missing', reason: 'target is not a file' },
  ]);
});

test('marks existing file fragments unverified and missing targets missing', async (t) => {
  const root = await temporaryDirectory(t);
  await writeFile(path.join(root, 'guide.md'), 'content without a section');
  await writeFile(path.join(root, 'index.md'), [
    '[section](guide.md#missing-section)',
    '[absent](absent.md#missing-section)',
  ].join('\n'));
  const { results } = await scan(root);
  assert.deepEqual(results.map(({ status, reason }) => ({ status, reason })), [
    { status: 'ok', reason: 'file exists; anchor not verified' },
    { status: 'missing', reason: 'file does not exist' },
  ]);
});

test('skips URLs, anchors, invalid encodings, traversal, and symlink escapes', async (t) => {
  const root = await temporaryDirectory(t);
  const outside = await temporaryDirectory(t);
  await writeFile(path.join(outside, 'outside.md'), 'outside');
  await symlink(outside, path.join(root, 'escape'));
  await writeFile(path.join(root, 'entry.md'), [
    '[web](https://example.test/a)',
    '[anchor](#section)',
    '[parent](../outside.md)',
    '[through symlink](escape/outside.md)',
    '[through missing symlink](escape/not-created.md)',
    '[bad encoding](bad%ZZ.md)',
    '[empty]()',
    '[query only](?x=1)',
  ].join('\n'));
  const { results } = await scan(root);
  assert.deepEqual(results.map(({ status, reason }) => ({ status, reason })), [
    { status: 'skipped', reason: 'external URL' },
    { status: 'skipped', reason: 'anchor-only link' },
    { status: 'skipped', reason: 'outside scan root' },
    { status: 'skipped', reason: 'symlink escapes scan root' },
    { status: 'skipped', reason: 'symlink escapes scan root' },
    { status: 'skipped', reason: 'invalid URL encoding' },
    { status: 'skipped', reason: 'empty link target' },
    { status: 'skipped', reason: 'query-only link' },
  ]);
});

test('does not follow symlink directories, traverses exclusions, and scans uppercase extensions', async (t) => {
  const root = await temporaryDirectory(t);
  const outside = await temporaryDirectory(t);
  await writeFile(path.join(outside, 'linked.md'), '[bad](missing.md)');
  await symlink(outside, path.join(root, 'linked-dir'));
  await mkdir(path.join(root, '.git'));
  await mkdir(path.join(root, 'node_modules'));
  await writeFile(path.join(root, '.git', 'ignored.md'), '[bad](missing.md)');
  await writeFile(path.join(root, 'node_modules', 'ignored.md'), '[bad](missing.md)');
  await writeFile(path.join(root, 'visible.md'), 'no links');
  await writeFile(path.join(root, 'UPPER.MD'), 'also no links');
  assert.deepEqual(await scan(root), { filesScanned: 2, results: [] });
});

test('orders paths by UTF-16 code-unit order and same-line links by source occurrence', async (t) => {
  const root = await temporaryDirectory(t);
  await mkdir(path.join(root, 'B'));
  await mkdir(path.join(root, 'a-b'));
  await mkdir(path.join(root, 'a'));
  await writeFile(path.join(root, 'a-b', 'z.md'), '[first](missing.md)');
  await writeFile(path.join(root, 'B', 'z.md'), '[upper directory](missing.md)');
  await writeFile(path.join(root, 'a.md'), [
    '[text][first] ![image][second]',
    '',
    '[first]: missing.md',
    '[second]: missing.png',
  ].join('\n'));
  await writeFile(path.join(root, 'a', 'z.md'), '[last](missing.md)');
  await writeFile(path.join(root, 'Z.md'), '[upper file](missing.md)');
  await writeFile(path.join(root, 'b.md'), '[lower file](missing.md)');
  const { results } = await scan(root);
  assert.deepEqual(results.map(({ source, line, kind }) => ({ source, line, kind })), [
    { source: 'B/z.md', line: 1, kind: 'link' },
    { source: 'Z.md', line: 1, kind: 'link' },
    { source: 'a-b/z.md', line: 1, kind: 'link' },
    { source: 'a.md', line: 1, kind: 'link' },
    { source: 'a.md', line: 1, kind: 'image' },
    { source: 'a/z.md', line: 1, kind: 'link' },
    { source: 'b.md', line: 1, kind: 'link' },
  ]);
});

test('rejects a non-directory scan root', async (t) => {
  const root = await temporaryDirectory(t);
  const file = path.join(root, 'file.md');
  await writeFile(file, 'text');
  await assert.rejects(scan(file), /Scan root is not a directory/);
});
