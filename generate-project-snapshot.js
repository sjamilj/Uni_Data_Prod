#!/usr/bin/env node
/**
 * generate-project-snapshot.js
 *
 * Walks a project folder (or a set of them), builds a directory tree, and
 * dumps every file's content underneath it into a single Markdown file —
 * useful for sharing your whole project structure + code in one file
 * (e.g. to paste into a chat, or keep as a dated snapshot).
 *
 * ── TWO MODES ────────────────────────────────────────────────────────────
 *
 * 1) ALL-UNI MODE — snapshot every university's `code/` folder in one go,
 *    plus the shared `shared/` and `dashboard/` folders.
 *
 *      node generate-project-snapshot.js --mode all --root "E:\Project Next\UK UNIVERSITIES\UNI\Uni_Data_Prod"
 *
 *    This expects a layout like:
 *      <root>\Aston University\code\...
 *      <root>\<Other University>\code\...
 *      <root>\shared\...
 *      <root>\dashboard\...
 *
 *    Every immediate subfolder of <root> that itself contains a `code`
 *    subfolder is treated as a university and included automatically —
 *    you don't need to list university names anywhere.
 *
 * 2) SINGLE-UNI MODE — snapshot just one university's `code/` folder
 *    (still includes shared/ and dashboard/ by default, since the code
 *    usually depends on them — turn that off with --no-shared).
 *
 *      node generate-project-snapshot.js --mode uni --uni "Aston University" --root "E:\Project Next\UK UNIVERSITIES\UNI\Uni_Data_Prod"
 *
 * 3) LEGACY / PLAIN MODE — original behaviour, snapshot any single folder
 *    directly (no university structure assumed):
 *
 *      node generate-project-snapshot.js [rootPath] [outputFile]
 *      node generate-project-snapshot.js .
 *      node generate-project-snapshot.js "E:\Project Next\Personal Digital Document Vault\document-vault"
 *
 * ── FLAGS ────────────────────────────────────────────────────────────────
 *   --mode <all|uni|plain>   default: plain
 *   --root <path>            root folder (Uni_Data_Prod for all/uni modes)
 *   --uni "<Name>"           required for --mode uni; must match a folder
 *                            name directly under --root
 *   --output <file>          output markdown path (default project-snapshot.md)
 *   --no-shared              (uni mode only) skip shared/ and dashboard/
 *   --code-dir <name>        subfolder name that holds the code, per
 *                            university (default: "code")
 *
 * CHANGES vs original:
 *   - Writes to disk via a stream instead of building one giant in-memory
 *     string, which was crashing with "RangeError: Invalid string length"
 *     on large projects (V8 caps a single string around ~512MB-1GB).
 *   - Skips common generated/output/data directories and large data files
 *     by default (see IGNORE_DIRS / IGNORE_FILES / IGNORE_EXTENSIONS below)
 *     — edit these lists for your project.
 *   - Caps any single file's dumped content at MAX_FILE_BYTES; oversized
 *     files are noted but not dumped in full.
 *   - NEW: --mode all / --mode uni for multi-university project layouts.
 */

const fs = require('fs');
const path = require('path');

// ── Config ────────────────────────────────────────────────────────────────

// Don't include more than this many bytes of any single file's content.
const MAX_FILE_BYTES = 200 * 1024; // 200 KB per file

// Folders to skip entirely (never descend into these)
const IGNORE_DIRS = new Set([
  'node_modules',
  '.git',
  'dist',
  'build',
  '.next',
  '.turbo',
  'coverage',
  '.vscode',
  '.idea',
  '__pycache__',
  // Excluded wherever they appear in the tree (matched by folder name,
  // not full path) — so this catches every university's
  // "<Uni Name>/output/course_pages/" automatically, no path listing needed:
  'course_pages',
]);

// Files to skip entirely — not shown in the tree, not dumped
const IGNORE_FILES = new Set([
  '.env',
  '.env.local',
  '.env.development',
  '.env.production',
  '.env.test',
  'package-lock.json',
  'yarn.lock',
  'pnpm-lock.yaml',
]);

// Extensions to skip content dump for even if not "binary" (large/noisy data files)
const IGNORE_CONTENT_EXTENSIONS = new Set([
  '.csv',
  '.log',
]);

// Binary / non-text extensions — skip content dump, just note the file
const BINARY_EXTENSIONS = new Set([
  '.png', '.jpg', '.jpeg', '.gif', '.webp', '.ico', '.bmp',
  '.pdf', '.zip', '.rar', '.7z', '.exe', '.dll', '.so',
  '.woff', '.woff2', '.ttf', '.eot',
  '.mp3', '.mp4', '.mov', '.avi',
]);

// Map file extensions to Markdown code-fence language tags
const LANG_MAP = {
  '.ts': 'typescript',
  '.tsx': 'tsx',
  '.js': 'javascript',
  '.jsx': 'jsx',
  '.json': 'json',
  '.md': 'markdown',
  '.yml': 'yaml',
  '.yaml': 'yaml',
  '.html': 'html',
  '.css': 'css',
  '.scss': 'scss',
  '.sql': 'sql',
  '.sh': 'bash',
  '.ps1': 'powershell',
  '.env': 'env',
};

// ── CLI arg parsing ──────────────────────────────────────────────────────

function parseArgs(argv) {
  const args = { _: [] };
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (a === '--no-shared') {
      args.noShared = true;
    } else if (a.startsWith('--')) {
      const key = a.slice(2);
      const val = argv[i + 1];
      args[key] = val;
      i++;
    } else {
      args._.push(a);
    }
  }
  return args;
}

const cliArgs = parseArgs(process.argv.slice(2));

const mode = (cliArgs.mode || 'plain').toLowerCase(); // 'all' | 'uni' | 'plain'
const codeDirName = cliArgs['code-dir'] || 'code';

// root: explicit --root, else first positional arg (plain mode), else cwd
const rootPath = path.resolve(cliArgs.root || cliArgs._[0] || '.');

// output: explicit --output, else second positional arg (plain mode), else default
const outputFile = path.resolve(
  cliArgs.output || cliArgs._[1] || 'project-snapshot.md'
);

// ── Helpers ───────────────────────────────────────────────────────────────

function getLang(filePath) {
  const ext = path.extname(filePath).toLowerCase();
  return LANG_MAP[ext] || '';
}

function isBinary(filePath) {
  return BINARY_EXTENSIONS.has(path.extname(filePath).toLowerCase());
}

function isIgnoredContent(filePath) {
  return IGNORE_CONTENT_EXTENSIONS.has(path.extname(filePath).toLowerCase());
}

/** Recursively collect { dirs, files } respecting ignore rules, sorted. */
function walk(dir) {
  const entries = fs.readdirSync(dir, { withFileTypes: true });
  const dirs = [];
  const files = [];

  for (const entry of entries.sort((a, b) => a.name.localeCompare(b.name))) {
    if (entry.name.startsWith('.') && entry.name !== '.env') {
      // still allow dotfiles like .gitignore to show, just skip noisy ones
      if (IGNORE_DIRS.has(entry.name)) continue;
    }
    if (entry.isDirectory()) {
      if (IGNORE_DIRS.has(entry.name)) continue;
      dirs.push(entry.name);
    } else {
      if (IGNORE_FILES.has(entry.name)) continue;
      files.push(entry.name);
    }
  }
  return { dirs, files };
}

/** Build the visual tree text (like the `tree` command). */
function buildTree(dir, prefix = '') {
  let output = '';
  const { dirs, files } = walk(dir);
  const items = [
    ...dirs.map((d) => ({ name: d, isDir: true })),
    ...files.map((f) => ({ name: f, isDir: false })),
  ];

  items.forEach((item, index) => {
    const isLast = index === items.length - 1;
    const connector = isLast ? '└── ' : '├── ';
    output += `${prefix}${connector}${item.name}${item.isDir ? '/' : ''}\n`;

    if (item.isDir) {
      const nextPrefix = prefix + (isLast ? '    ' : '│   ');
      output += buildTree(path.join(dir, item.name), nextPrefix);
    }
  });

  return output;
}

/** Recursively collect all file paths (relative to a base dir), in tree order. */
function collectFiles(dir, relBase = '') {
  const { dirs, files } = walk(dir);
  let result = [];

  for (const f of files) {
    result.push(path.join(relBase, f));
  }
  for (const d of dirs) {
    result = result.concat(collectFiles(path.join(dir, d), path.join(relBase, d)));
  }
  return result;
}

/** Discover university folders under root: any immediate subfolder that
 *  itself contains a `codeDirName` subfolder. */
function discoverUniversities(root) {
  if (!fs.existsSync(root)) return [];
  const entries = fs.readdirSync(root, { withFileTypes: true });
  const unis = [];
  for (const entry of entries.sort((a, b) => a.name.localeCompare(b.name))) {
    if (!entry.isDirectory()) continue;
    if (IGNORE_DIRS.has(entry.name)) continue;
    if (entry.name === 'shared' || entry.name === 'dashboard') continue;
    const candidateCodeDir = path.join(root, entry.name, codeDirName);
    if (fs.existsSync(candidateCodeDir) && fs.statSync(candidateCodeDir).isDirectory()) {
      unis.push(entry.name);
    }
  }
  return unis;
}

/**
 * Write one "section" of the snapshot: a heading, its folder tree, and
 * every file's content underneath it.
 */
function writeSection(out, sectionTitle, sectionDir) {
  out.write(`## ${sectionTitle}\n\n`);
  out.write(`Path: \`${sectionDir}\`\n\n`);

  if (!fs.existsSync(sectionDir)) {
    out.write(`_Folder not found — skipped._\n\n`);
    return { count: 0, skippedLarge: 0, skippedContentType: 0 };
  }

  out.write('```\n');
  out.write(`${path.basename(sectionDir)}/\n`);
  out.write(buildTree(sectionDir));
  out.write('```\n\n');

  const allFiles = collectFiles(sectionDir);
  let skippedLarge = 0;
  let skippedContentType = 0;

  for (const relFile of allFiles) {
    const fullPath = path.join(sectionDir, relFile);
    const displayPath = relFile.split(path.sep).join('/');

    out.write(`### \`${displayPath}\`\n\n`);

    if (isBinary(relFile)) {
      out.write(`_Binary file — content not included._\n\n`);
      continue;
    }

    if (isIgnoredContent(relFile)) {
      out.write(`_Skipped (excluded extension: ${path.extname(relFile)})._\n\n`);
      skippedContentType++;
      continue;
    }

    let stat;
    try {
      stat = fs.statSync(fullPath);
    } catch (err) {
      out.write(`_Could not stat file: ${err.message}_\n\n`);
      continue;
    }

    if (stat.size > MAX_FILE_BYTES) {
      out.write(
        `_File too large to include (${(stat.size / 1024).toFixed(1)} KB, ` +
          `limit ${(MAX_FILE_BYTES / 1024).toFixed(0)} KB). Skipped._\n\n`
      );
      skippedLarge++;
      continue;
    }

    let content;
    try {
      content = fs.readFileSync(fullPath, 'utf8');
    } catch (err) {
      out.write(`_Could not read file: ${err.message}_\n\n`);
      continue;
    }

    const lang = getLang(relFile);
    out.write('```' + lang + '\n');
    out.write(content);
    if (!content.endsWith('\n')) out.write('\n');
    out.write('```\n\n');
  }

  return { count: allFiles.length, skippedLarge, skippedContentType };
}

// ── Main ──────────────────────────────────────────────────────────────────

function main() {
  if (!fs.existsSync(rootPath)) {
    console.error(`Path does not exist: ${rootPath}`);
    process.exit(1);
  }

  const timestamp = new Date().toISOString();
  const out = fs.createWriteStream(outputFile, { encoding: 'utf8' });

  let totals = { count: 0, skippedLarge: 0, skippedContentType: 0 };
  const addTotals = (t) => {
    totals.count += t.count;
    totals.skippedLarge += t.skippedLarge;
    totals.skippedContentType += t.skippedContentType;
  };

  if (mode === 'all') {
    // ── ALL universities' code/ + shared/ + dashboard/ ──
    const unis = discoverUniversities(rootPath);
    if (unis.length === 0) {
      console.error(
        `No university folders found under ${rootPath} ` +
          `(looked for subfolders containing a "${codeDirName}" folder).`
      );
      process.exit(1);
    }

    out.write(`# Project Snapshot: All Universities (${unis.length})\n\n`);
    out.write(`Generated: ${timestamp}\n\n`);
    out.write(`Root: \`${rootPath}\`\n\n`);
    out.write(`Universities included: ${unis.join(', ')}\n\n`);

    for (const uniName of unis) {
      addTotals(
        writeSection(out, `${uniName} — code/`, path.join(rootPath, uniName, codeDirName))
      );
    }

    addTotals(writeSection(out, 'shared/', path.join(rootPath, 'shared')));
    addTotals(writeSection(out, 'dashboard/', path.join(rootPath, 'dashboard')));

    finish(out, outputFile, totals, `all ${unis.length} universities + shared/dashboard`);
  } else if (mode === 'uni') {
    // ── ONE university's code/ (+ shared/ + dashboard/ by default) ──
    const uniName = cliArgs.uni;
    if (!uniName) {
      console.error('--mode uni requires --uni "<University Name>"');
      process.exit(1);
    }

    out.write(`# Project Snapshot: ${uniName}\n\n`);
    out.write(`Generated: ${timestamp}\n\n`);
    out.write(`Root: \`${rootPath}\`\n\n`);

    addTotals(
      writeSection(out, `${uniName} — code/`, path.join(rootPath, uniName, codeDirName))
    );

    if (!cliArgs.noShared) {
      addTotals(writeSection(out, 'shared/', path.join(rootPath, 'shared')));
      addTotals(writeSection(out, 'dashboard/', path.join(rootPath, 'dashboard')));
    }

    finish(out, outputFile, totals, uniName);
  } else {
    // ── PLAIN / legacy: snapshot rootPath directly ──
    const projectName = path.basename(rootPath);
    out.write(`# Project Snapshot: ${projectName}\n\n`);
    out.write(`Generated: ${timestamp}\n\n`);
    out.write(`Root: \`${rootPath}\`\n\n`);

    addTotals(writeSection(out, 'Folder Contents', rootPath));

    finish(out, outputFile, totals, projectName);
  }
}

function finish(out, outputFile, totals, label) {
  out.end();
  out.on('finish', () => {
    console.log(`✅ Snapshot written to: ${outputFile}`);
    console.log(`   Scope: ${label}`);
    console.log(`   Files included: ${totals.count}`);
    if (totals.skippedLarge) console.log(`   Skipped (too large): ${totals.skippedLarge}`);
    if (totals.skippedContentType)
      console.log(`   Skipped (excluded extension): ${totals.skippedContentType}`);
  });
}

main();