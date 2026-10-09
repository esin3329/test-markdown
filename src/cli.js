#!/usr/bin/env node
import { realpath, writeFile } from 'node:fs/promises';
import path from 'node:path';
import { scan } from './scan.js';
import { renderReport } from './report.js';

function parseArguments(args) {
  let root;
  let format = 'text';
  let output;
  for (let index = 0; index < args.length; index += 1) {
    const argument = args[index];
    if (argument === '--format') {
      format = args[++index];
      if (!['text', 'json', 'html'].includes(format)) throw new Error(`Invalid format: ${format ?? ''}`);
    } else if (argument === '--output') {
      output = args[++index];
      if (!output) throw new Error('--output requires a path');
    } else if (argument.startsWith('-')) {
      throw new Error(`Unknown option: ${argument}`);
    } else if (root === undefined) {
      root = argument;
    } else {
      throw new Error(`Unexpected argument: ${argument}`);
    }
  }
  if (!root) throw new Error('Usage: node src/cli.js <directory> [--format text|json|html] [--output <file>]');
  if (output && format !== 'html') throw new Error('--output is supported only with --format html');
  return { root, format, output };
}
async function resolveWriteTarget(targetPath) {
  let current = path.resolve(targetPath);
  const missingSegments = [];
  while (true) {
    try {
      return path.join(await realpath(current), ...missingSegments);
    } catch (error) {
      if (error.code !== 'ENOENT' && error.code !== 'ENOTDIR') throw error;
      const parent = path.dirname(current);
      if (parent === current) throw error;
      missingSegments.unshift(path.basename(current));
      current = parent;
    }
  }
}

function isWithin(root, candidate) {
  const relative = path.relative(root, candidate);
  return relative === '' || (!relative.startsWith(`..${path.sep}`) && relative !== '..' && !path.isAbsolute(relative));
}

async function assertSafeOutput(rootPath, outputPath) {
  const root = await realpath(path.resolve(rootPath));
  const target = await resolveWriteTarget(outputPath);
  if (isWithin(root, target) && path.extname(target).toLowerCase() === '.md') {
    throw new Error('Refusing to overwrite a Markdown input file');
  }
}
async function main() {
  try {
    const options = parseArguments(process.argv.slice(2));
    const report = await scan(options.root);
    const rendered = renderReport(report, options.format);
    if (options.output) {
      await assertSafeOutput(options.root, options.output);
      await writeFile(options.output, rendered, 'utf8');
    } else process.stdout.write(rendered);
    return report.results.some((result) => result.status === 'missing') ? 1 : 0;
  } catch (error) {
    process.stderr.write(`link-doctor: ${error.message}\n`);
    return 2;
  }
}

process.exitCode = await main();
