import { readFile, readdir, realpath, stat } from 'node:fs/promises';
import path from 'node:path';
import { fromMarkdown } from 'mdast-util-from-markdown';

const EXCLUDED_DIRECTORIES = new Set(['.git', 'node_modules']);

function isWithin(root, candidate) {
  const relative = path.relative(root, candidate);
  return relative === '' || (!relative.startsWith(`..${path.sep}`) && relative !== '..' && !path.isAbsolute(relative));
}

function compareText(left, right) {
  return left < right ? -1 : left > right ? 1 : 0;
}

function walkMarkdown(tree, visit) {
  visit(tree);
  for (const child of tree.children ?? []) walkMarkdown(child, visit);
}

function normalizedIdentifier(identifier) {
  return identifier.trim().replaceAll(/\s+/g, ' ').toUpperCase();
}

async function findMarkdownFiles(root) {
  const files = [];
  async function walk(directory) {
    const entries = await readdir(directory, { withFileTypes: true });
    entries.sort((left, right) => compareText(left.name, right.name));
    for (const entry of entries) {
      if (entry.isSymbolicLink()) continue;
      const absolutePath = path.join(directory, entry.name);
      if (entry.isDirectory()) {
        if (!EXCLUDED_DIRECTORIES.has(entry.name)) await walk(absolutePath);
      } else if (entry.isFile() && entry.name.toLowerCase().endsWith('.md')) {
        files.push(absolutePath);
      }
    }
  }
  await walk(root);
  return files;
}

function getTargets(tree) {
  const definitions = new Map();
  walkMarkdown(tree, (node) => {
    if (node.type === 'definition') {
      const identifier = normalizedIdentifier(node.identifier);
      if (!definitions.has(identifier)) definitions.set(identifier, node.url);
    }
  });

  const targets = [];
  walkMarkdown(tree, (node) => {
    if (node.type === 'link' || node.type === 'image') {
      targets.push({ target: node.url, kind: node.type, line: node.position.start.line });
    } else if (node.type === 'linkReference' || node.type === 'imageReference') {
      targets.push({
        target: definitions.get(normalizedIdentifier(node.identifier)) ?? '',
        kind: node.type === 'linkReference' ? 'link' : 'image',
        line: node.position.start.line,
      });
    }
  });
  return targets;
}

function skipResult(source, line, target, kind, reason) {
  return { source, line, target, kind, status: 'skipped', reason };
}

async function nearestExistingRealPath(candidate) {
  let current = candidate;
  while (true) {
    try {
      return await realpath(current);
    } catch (error) {
      if (error.code !== 'ENOENT' && error.code !== 'ENOTDIR') throw error;
      const parent = path.dirname(current);
      if (parent === current) throw error;
      current = parent;
    }
  }
}

async function inspectTarget(root, source, link) {
  const { target, line, kind } = link;
  const trimmedTarget = target.trim();
  if (/^[a-z][a-z\d+.-]*:/i.test(trimmedTarget) || trimmedTarget.startsWith('//')) {
    return skipResult(source, line, target, kind, 'external URL');
  }

  if (trimmedTarget === '') return skipResult(source, line, target, kind, 'empty link target');
  const hasFragment = trimmedTarget.includes('#');
  const pathPart = trimmedTarget.split(/[?#]/, 1)[0];
  if (pathPart === '') {
    const reason = trimmedTarget.startsWith('?') ? 'query-only link' : 'anchor-only link';
    return skipResult(source, line, target, kind, reason);
  }

  let decodedPath;
  try {
    decodedPath = decodeURIComponent(pathPart);
  } catch {
    return skipResult(source, line, target, kind, 'invalid URL encoding');
  }
  if (decodedPath.includes('\0')) return skipResult(source, line, target, kind, 'invalid path');

  const candidate = path.resolve(decodedPath.startsWith('/')
    ? root
    : path.dirname(path.join(root, source)), decodedPath.startsWith('/') ? `.${decodedPath}` : decodedPath);
  if (!isWithin(root, candidate)) return skipResult(source, line, target, kind, 'outside scan root');

  const existingAncestor = await nearestExistingRealPath(candidate);
  if (!isWithin(root, existingAncestor)) return skipResult(source, line, target, kind, 'symlink escapes scan root');

  try {
    const targetStat = await stat(candidate);
    if (targetStat.isFile()) {
      const reason = hasFragment ? 'file exists; anchor not verified' : 'file exists';
      return { source, line, target, kind, status: 'ok', reason };
    }
    return { source, line, target, kind, status: 'missing', reason: 'target is not a file' };
  } catch (error) {
    if (error.code === 'ENOENT' || error.code === 'ENOTDIR') {
      return { source, line, target, kind, status: 'missing', reason: 'file does not exist' };
    }
    throw error;
  }
}

export async function scan(rootPath) {
  const root = await realpath(path.resolve(rootPath));
  const rootStat = await stat(root);
  if (!rootStat.isDirectory()) throw new Error(`Scan root is not a directory: ${rootPath}`);

  const files = await findMarkdownFiles(root);
  const results = [];
  for (const absolutePath of files) {
    const source = path.relative(root, absolutePath).split(path.sep).join('/');
    const contents = await readFile(absolutePath, 'utf8');
    const tree = fromMarkdown(contents);
    for (const link of getTargets(tree)) results.push(await inspectTarget(root, source, link));
  }
  results.sort((left, right) => compareText(left.source, right.source) || left.line - right.line);
  return { filesScanned: files.length, results };
}
