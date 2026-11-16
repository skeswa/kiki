import { mkdir, writeFile } from "node:fs/promises";
import { dirname, join } from "node:path";
import { defineConfig } from "vitepress";
import { sidebar } from "./navigation";

const base = process.env.VITEPRESS_BASE ?? "/kiki/";
const siteUrl = process.env.VITEPRESS_SITE_URL ?? "https://skeswa.github.io/kiki/";

/**
 * The 2026-07 book restructure (glossary and user stories became
 * appendices; chapters renumbered) changed every chapter's URL. These
 * are the pre-restructure paths, kept alive as generated redirect stubs
 * so published links keep working. Keys and values are book-relative
 * slugs; a trailing slash marks a directory index.
 */
const bookRedirects: Record<string, string> = {
  "02-glossary": "appendix-a-glossary",
  "03-user-stories": "appendix-b-user-stories",
  "04-invariants": "02-invariants",
  "05-threads": "03-threads",
  "06-authority": "04-authority",
  "07-cascade": "05-cascade",
  "08-transcript": "06-transcript",
  "09-publishing": "07-publishing",
  "10-metadata": "08-metadata",
  "11-commands": "09-commands",
  "12-interface/": "10-interface/",
  "12-interface/spec": "10-interface/spec",
  "12-interface/storyboard": "10-interface/storyboard",
  "13-configuration": "11-configuration",
  "14-observability": "12-observability",
  "15-architecture/": "13-architecture/",
  "15-architecture/crates": "13-architecture/crates",
  "15-architecture/daemon": "13-architecture/daemon",
  "15-architecture/grpc": "13-architecture/grpc",
  "15-architecture/harness-adapter": "13-architecture/harness-adapter",
  "15-architecture/op-log-watcher": "13-architecture/op-log-watcher",
  "15-architecture/schema": "13-architecture/schema",
  "16-testing": "14-testing",
  "17-build-sequencing": "15-build-sequencing",
  "18-roadmap": "16-roadmap",
  "19-naming": "appendix-c-naming",
  "20-decisions/": "17-decisions/",
  "20-decisions/cascade-outbox": "17-decisions/cascade-outbox",
  "20-decisions/codex-adapter": "17-decisions/codex-adapter",
  "20-decisions/native-evolution": "17-decisions/native-evolution",
  "20-decisions/rejected": "17-decisions/rejected",
  "20-decisions/thread-head-and-sagas": "17-decisions/thread-head-and-sagas",
  "20-decisions/transcript-anchoring": "17-decisions/transcript-anchoring",
};

export default defineConfig({
  lang: "en-US",
  title: "kiki",
  titleTemplate: ":title · kiki",
  description:
    "Give every coding agent its own thread with kiki, a daemon-backed coordinator for jj, Herdr, agent harnesses, and GitHub.",
  base,
  cleanUrls: true,
  rewrites: {
    "reference/README.md": "reference/index.md",
    "reference/book/10-interface/README.md": "reference/book/10-interface/index.md",
    "reference/book/13-architecture/README.md": "reference/book/13-architecture/index.md",
    "reference/book/17-decisions/README.md": "reference/book/17-decisions/index.md",
  },
  lastUpdated: true,
  appearance: "force-dark",
  markdown: {
    config(md) {
      // Render ```mermaid fences as client-side <Mermaid> components instead
      // of highlighted code blocks.
      const fence = md.renderer.rules.fence!;
      md.renderer.rules.fence = (tokens, idx, options, env, self) => {
        const token = tokens[idx]!;
        if (token.info.trim() === "mermaid") {
          return `<Mermaid graph="${encodeURIComponent(token.content)}" />`;
        }
        return fence(tokens, idx, options, env, self);
      };
    },
  },
  sitemap: { hostname: siteUrl },
  head: [
    ["meta", { name: "theme-color", content: "#0b1210" }],
    ["meta", { name: "color-scheme", content: "dark" }],
    ["meta", { property: "og:type", content: "website" }],
    ["meta", { property: "og:site_name", content: "kiki" }],
    // Noto Emoji artwork (Apache 2.0) — attribution in docs/public/favicon.LICENSE.txt.
    ["link", { rel: "icon", type: "image/png", sizes: "128x128", href: `${base}favicon.png` }],
  ],
  async buildEnd(siteConfig) {
    // GitHub Pages is static, so old chapter URLs survive as stub pages
    // that meta-refresh (and JS-replace) to the new location. cleanUrls
    // serving resolves the extensionless old path to `<old>.html`.
    for (const [from, to] of Object.entries(bookRedirects)) {
      const target = `${base}reference/book/${to}`;
      const canonical = new URL(`reference/book/${to}`, siteUrl).toString();
      const stubPath = join(
        siteConfig.outDir,
        "reference/book",
        from.endsWith("/") ? `${from}index.html` : `${from}.html`,
      );
      await mkdir(dirname(stubPath), { recursive: true });
      await writeFile(
        stubPath,
        `<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">` +
          `<title>Redirecting…</title>` +
          `<link rel="canonical" href="${canonical}">` +
          `<meta http-equiv="refresh" content="0; url=${target}">` +
          `<script>location.replace(${JSON.stringify(target)} + location.hash)</script>` +
          `</head><body><p>This chapter moved to <a href="${target}">${canonical}</a>.</p></body></html>\n`,
      );
    }
  },
  transformPageData(pageData) {
    const canonicalPath = pageData.relativePath
      .replace(/(^|\/)(?:README|index)\.md$/, "$1")
      .replace(/\.md$/, "");
    const canonical = new URL(canonicalPath, siteUrl).toString();
    pageData.frontmatter.head ??= [];
    pageData.frontmatter.head.push(["link", { rel: "canonical", href: canonical }]);
    pageData.frontmatter.head.push(["meta", { property: "og:title", content: pageData.title }]);
    if (pageData.description) {
      pageData.frontmatter.head.push([
        "meta",
        { property: "og:description", content: pageData.description },
      ]);
    }
  },
  themeConfig: {
    siteTitle: "kiki",
    nav: [
      {
        text: "guide",
        link: "/reference/book/03-threads",
        activeMatch: "^/reference/book/03-threads",
      },
      {
        text: "reference",
        link: "/reference/",
        activeMatch: "^/reference/(?!book/(?:03-threads|16-roadmap))",
      },
      {
        text: "roadmap",
        link: "/reference/book/16-roadmap",
        activeMatch: "^/reference/book/16-roadmap",
      },
      { text: "home", link: "/", activeMatch: "^/$" },
      { text: "journal ↗", link: "https://github.com/skeswa/kiki/tree/main/journal", noIcon: true },
      { text: "github ↗", link: "https://github.com/skeswa/kiki", noIcon: true },
    ],
    sidebar,
    outline: { level: [2, 3], label: "on this page" },
    search: {
      provider: "local",
      options: {
        detailedView: true,
        translations: {
          button: { buttonText: "search docs", buttonAriaLabel: "search docsK" },
        },
      },
    },
    editLink: {
      pattern: "https://github.com/skeswa/kiki/edit/main/docs/:path",
      text: "edit this page ↗",
    },
    footer: {
      message: "docs/reference · built with VitePress",
      copyright: "MIT © 2026 Sandile Keswa",
    },
    docFooter: { prev: "previous", next: "next" },
    lastUpdated: { text: "last revised", formatOptions: { dateStyle: "medium" } },
  },
});
