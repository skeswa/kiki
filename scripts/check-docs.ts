import { readdir, readFile, stat } from "node:fs/promises";
import { dirname, extname, isAbsolute, relative, resolve } from "node:path";

type Diagnostic = {
  file: string;
  line: number;
  message: string;
};

const root = process.cwd();
const diagnostics: Diagnostic[] = [];

async function markdownFiles(path: string): Promise<string[]> {
  const entries = await readdir(path, { withFileTypes: true });
  const files: string[] = [];

  for (const entry of entries) {
    const child = resolve(path, entry.name);
    if (entry.isDirectory()) {
      files.push(...(await markdownFiles(child)));
    } else if (entry.isFile() && extname(entry.name).toLowerCase() === ".md") {
      files.push(child);
    }
  }

  return files;
}

function lineNumber(source: string, offset: number): number {
  let line = 1;
  for (let index = 0; index < offset; index += 1) {
    if (source.charCodeAt(index) === 10) line += 1;
  }
  return line;
}

function withoutFencedCode(source: string): string {
  const lines = source.split("\n");
  let fence: { marker: string; length: number } | undefined;

  return lines
    .map((line) => {
      const opening = line.match(/^\s{0,3}(`{3,}|~{3,})/);
      const openingDelimiter = opening?.[1];
      if (!fence && openingDelimiter) {
        fence = { marker: openingDelimiter[0]!, length: openingDelimiter.length };
        return "";
      }

      if (fence) {
        const closing = line.match(/^\s{0,3}(`{3,}|~{3,})\s*$/);
        const closingDelimiter = closing?.[1];
        if (
          closingDelimiter &&
          closingDelimiter[0] === fence.marker &&
          closingDelimiter.length >= fence.length
        ) {
          fence = undefined;
        }
        return "";
      }

      return line;
    })
    .join("\n");
}

function withoutInlineCodeOrComments(source: string): string {
  const preserveLines = (value: string) => value.replace(/[^\n]/g, " ");
  return withoutFencedCode(source)
    .replace(/<!--[\s\S]*?-->/g, preserveLines)
    .replace(/(`+)[\s\S]*?\1/g, preserveLines);
}

function headingText(raw: string): string {
  return raw
    .replace(/\s+#+\s*$/, "")
    .replace(/<[^>]*>/g, "")
    .replace(/!\[([^\]]*)\]\([^)]*\)/g, "$1")
    .replace(/\[([^\]]+)\]\([^)]*\)/g, "$1")
    .replace(/\[([^\]]+)\]\[[^\]]*\]/g, "$1")
    .replace(/[`*_~]/g, "")
    .trim();
}

function githubSlug(value: string): string {
  return value
    .toLowerCase()
    .replace(/&(?:[a-z]+|#\d+|#x[0-9a-f]+);/gi, "")
    .replace(/[\u2000-\u206f\u2e00-\u2e7f'!"#$%&()*+,./:;<=>?@[\]^`{|}~\\]/g, "")
    .replace(/\s+/g, "-");
}

function anchorsFor(source: string): Set<string> {
  const masked = withoutFencedCode(source);
  const lines = masked.split("\n");
  const anchors = new Set<string>();
  const slugCounts = new Map<string, number>();

  const addHeading = (raw: string) => {
    const base = githubSlug(headingText(raw));
    if (!base) return;

    let suffix = slugCounts.get(base) ?? 0;
    let slug = suffix === 0 ? base : `${base}-${suffix}`;
    while (anchors.has(slug)) {
      suffix += 1;
      slug = `${base}-${suffix}`;
    }
    slugCounts.set(base, suffix + 1);
    anchors.add(slug);
  };

  for (let index = 0; index < lines.length; index += 1) {
    const line = lines[index];
    if (line === undefined) continue;

    const atx = line.match(/^\s{0,3}#{1,6}\s+(.+?)\s*$/);
    const atxText = atx?.[1];
    if (atxText) {
      addHeading(atxText);
      continue;
    }

    const underline = lines[index + 1];
    if (line.trim() && underline && /^\s{0,3}(?:=+|-+)\s*$/.test(underline)) {
      addHeading(line);
      index += 1;
    }
  }

  for (const match of masked.matchAll(/<a\s+(?:[^>]*?\s)?(?:id|name)=["']([^"']+)["'][^>]*>/gi)) {
    const anchor = match[1];
    if (anchor) anchors.add(anchor);
  }

  return anchors;
}

function linkDestination(raw: string): string | undefined {
  const trimmed = raw.trim();
  if (!trimmed) return undefined;
  if (trimmed.startsWith("<")) {
    const end = trimmed.indexOf(">");
    return end === -1 ? undefined : trimmed.slice(1, end);
  }
  return trimmed.match(/^\S+/)?.[0];
}

function relativeLinkDestinations(source: string): Array<{ destination: string; offset: number }> {
  const masked = withoutInlineCodeOrComments(source);
  const links: Array<{ destination: string; offset: number }> = [];
  const patterns = [/!?\[[^\]\n]*\]\(([^)\n]+)\)/g, /^\s{0,3}\[[^\]\n]+\]:\s*(\S.*)$/gm];

  for (const pattern of patterns) {
    for (const match of masked.matchAll(pattern)) {
      const rawDestination = match[1];
      if (!rawDestination) continue;
      const destination = linkDestination(rawDestination);
      if (destination) links.push({ destination, offset: match.index ?? 0 });
    }
  }

  return links;
}

function isRelativeMarkdownLink(destination: string): boolean {
  if (destination.startsWith("#")) return true;
  if (isAbsolute(destination) || destination.startsWith("//")) return false;
  return !/^[a-z][a-z\d+.-]*:/i.test(destination);
}

function decoded(value: string): string {
  try {
    return decodeURIComponent(value);
  } catch {
    return value;
  }
}

const files = [resolve(root, "README.md"), ...(await markdownFiles(resolve(root, "docs")))].sort();
const sources = new Map<string, string>();
const anchorCache = new Map<string, Set<string>>();

for (const file of files) {
  sources.set(file, await readFile(file, "utf8"));
}

async function targetExists(path: string): Promise<boolean> {
  try {
    await stat(path);
    return true;
  } catch {
    return false;
  }
}

for (const file of files) {
  const source = sources.get(file)!;
  const displayFile = relative(root, file);

  for (const { destination, offset } of relativeLinkDestinations(source)) {
    if (!isRelativeMarkdownLink(destination)) continue;

    const hash = destination.indexOf("#");
    const rawPath = hash === -1 ? destination : destination.slice(0, hash);
    const fragment = hash === -1 ? "" : decoded(destination.slice(hash + 1));
    const query = rawPath.indexOf("?");
    const cleanPath = decoded(query === -1 ? rawPath : rawPath.slice(0, query));
    const target = cleanPath ? resolve(dirname(file), cleanPath) : file;
    const line = lineNumber(source, offset);

    if (!(await targetExists(target))) {
      diagnostics.push({ file: displayFile, line, message: `missing link target: ${destination}` });
      continue;
    }

    if (!fragment) continue;
    if ((await stat(target)).isDirectory()) {
      diagnostics.push({
        file: displayFile,
        line,
        message: `cannot verify anchor on directory: ${destination}`,
      });
      continue;
    }

    let anchors = anchorCache.get(target);
    if (!anchors) {
      const targetSource = sources.get(target) ?? (await readFile(target, "utf8"));
      anchors = anchorsFor(targetSource);
      anchorCache.set(target, anchors);
    }

    if (!anchors.has(fragment)) {
      diagnostics.push({ file: displayFile, line, message: `missing anchor: ${destination}` });
    }
  }

  const staleContracts: Array<{ pattern: RegExp; message: string }> = [
    { pattern: /#scenario-3-conflict\b/gi, message: "removed scenario-3-conflict anchor" },
    {
      pattern: /\b(?:FollowingParent|ParentMergePending|DetachedMovedToDefault)\b/g,
      message: "invented parent-merge state name",
    },
    { pattern: /(?<!●)●●○(?![●○])/g, message: "stale cascade-pending glyph" },
    {
      pattern:
        /\btranscript(?:s| data| messages)?\b[^\n]{0,160}\bnever leaves? the local machine\b/gi,
      message: "stale transcript local-only claim",
    },
    {
      pattern: /\bowned_stack_root_change_id\b/g,
      message: "stale owned-stack root shortcut; validate the entire exact path",
    },
    {
      pattern: /\bAI-drafted (?:PR |pull request )?(?:title|text|body)/gi,
      message: "AI drafting is not part of the first publishing tranche",
    },
    {
      pattern: /unknown in-flight batches remain pass-through/gi,
      message: "lost PassThrough admission must establish a clean boundary by restart",
    },
    {
      pattern: /(?:^|\s)Conflicted(?:\s|[.,;:]|$)/gm,
      message: "stale capitalized cascade state; canonical value is conflicted",
    },
    {
      pattern: /(?:~\/\.kiki|\.kiki\/)[^\n` ]*audit\.log\b/gi,
      message: "standalone audit file is stale; SQLite is authoritative",
    },
    {
      pattern: /kk init[^\n]{0,100}\b(?:requires|validates)\b[^\n]{0,40}\bgh\b/gi,
      message: "kk init must not require or validate gh",
    },
  ];

  if (displayFile === "docs/reference/book/02-glossary.md") {
    staleContracts.push({
      pattern: /\bLocal-only\b[^\n]*(?:transcript|state\.db)/gi,
      message: "privacy shorthand must distinguish local storage from consented provider egress",
    });
  }

  if (displayFile !== "docs/reference/book/01-orientation.md") {
    staleContracts.push({
      pattern: /^## Acceptance slice\s*$/gim,
      message: "Orientation is the sole scope ledger; link to it instead of duplicating the list",
    });
  }

  for (const { pattern, message } of staleContracts) {
    for (const match of source.matchAll(pattern)) {
      diagnostics.push({ file: displayFile, line: lineNumber(source, match.index ?? 0), message });
    }
  }
}

diagnostics.sort(
  (a, b) => a.file.localeCompare(b.file) || a.line - b.line || a.message.localeCompare(b.message),
);

if (diagnostics.length > 0) {
  for (const diagnostic of diagnostics) {
    console.error(`${diagnostic.file}:${diagnostic.line}: ${diagnostic.message}`);
  }
  console.error(
    `check:docs failed with ${diagnostics.length} error${diagnostics.length === 1 ? "" : "s"}`,
  );
  process.exit(1);
}

console.log(`check:docs passed (${files.length} Markdown files)`);
