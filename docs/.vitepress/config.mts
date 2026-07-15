import { defineConfig } from "vitepress";
import { sidebar } from "./navigation";

const base = process.env.VITEPRESS_BASE ?? "/kiki/";
const siteUrl = process.env.VITEPRESS_SITE_URL ?? "https://skeswa.github.io/kiki/";

export default defineConfig({
  lang: "en-US",
  title: "kiki",
  titleTemplate: ":title · kiki",
  description:
    "Give every coding agent its own thread with kiki, a daemon-backed coordinator for jj, tmux, agent harnesses, and GitHub.",
  base,
  cleanUrls: true,
  rewrites: {
    "reference/README.md": "reference/index.md",
    "reference/book/12-interface/README.md": "reference/book/12-interface/index.md",
    "reference/book/15-architecture/README.md": "reference/book/15-architecture/index.md",
    "reference/book/20-decisions/README.md": "reference/book/20-decisions/index.md",
  },
  lastUpdated: true,
  appearance: "force-dark",
  sitemap: { hostname: siteUrl },
  head: [
    ["meta", { name: "theme-color", content: "#0b1210" }],
    ["meta", { name: "color-scheme", content: "dark" }],
    ["meta", { property: "og:type", content: "website" }],
    ["meta", { property: "og:site_name", content: "kiki" }],
    [
      "link",
      {
        rel: "icon",
        href: "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'%3E%3Crect width='32' height='32' rx='4' fill='%230b1210'/%3E%3Cpath d='M9 23 22 10l2 2-13 13H9v-2Z' fill='%2348d597'/%3E%3Cpath d='m19 9 2-2 4 4-2 2-4-4Z' fill='%23f0a05a'/%3E%3C/svg%3E",
      },
    ],
  ],
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
        link: "/reference/book/05-threads",
        activeMatch: "^/reference/book/05-threads",
      },
      {
        text: "reference",
        link: "/reference/",
        activeMatch: "^/reference/(?!book/(?:05-threads|18-roadmap))",
      },
      {
        text: "roadmap",
        link: "/reference/book/18-roadmap",
        activeMatch: "^/reference/book/18-roadmap",
      },
      { text: "home", link: "/", activeMatch: "^/$" },
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
