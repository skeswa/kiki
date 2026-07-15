<script setup lang="ts">
import { useData } from "vitepress";
import { computed } from "vue";

const { page, frontmatter } = useData();

/**
 * Breadcrumb model: `<root> / <leaf>`, e.g. "reference / chapter 01".
 *
 * Resolution order:
 * 1. `crumb: false` in frontmatter hides the breadcrumb.
 * 2. `crumb: "root / leaf"` in frontmatter overrides it verbatim.
 * 3. Book chapters (`reference/book/NN-*`) render "reference / chapter NN".
 * 4. Any other page renders its top-level section as the root and its
 *    slug (dashes → spaces) as the leaf; section indexes get no leaf.
 */
const crumb = computed(() => {
  const override = frontmatter.value.crumb;
  if (override === false) return null;
  if (typeof override === "string") {
    const [root, ...rest] = override.split("/").map((part: string) => part.trim());
    return { root, leaf: rest.join(" / ") || null };
  }

  const path = page.value.relativePath
    .replace(/(^|\/)(?:README|index)\.md$/, "$1")
    .replace(/\.md$/, "");
  const segments = path.split("/").filter(Boolean);
  if (segments.length === 0) return null;

  const root = segments[0];
  const chapter = path.match(/^reference\/book\/(\d+)-/);
  const leaf = chapter
    ? `chapter ${chapter[1]}`
    : segments.length > 1
      ? segments[segments.length - 1].replace(/-/g, " ")
      : "overview";
  return { root, leaf };
});
</script>

<template>
  <nav v-if="crumb" class="doc-crumb" aria-label="breadcrumb">
    <span class="crumb-root">{{ crumb.root }}</span>
    <template v-if="crumb.leaf">
      <span class="crumb-sep">/</span>
      <span class="crumb-leaf">{{ crumb.leaf }}</span>
    </template>
  </nav>
</template>
