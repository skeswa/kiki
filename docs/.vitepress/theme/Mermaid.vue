<script setup lang="ts">
import { onMounted, ref } from "vue";

const props = defineProps<{ graph: string }>();

const svg = ref("");
const failed = ref(false);

let seq = 0;

onMounted(async () => {
  const { default: mermaid } = await import("mermaid");
  // Mermaid measures text while laying out nodes; wait for the site's
  // webfont so those measurements match what actually renders.
  await document.fonts.ready;
  mermaid.initialize({
    startOnLoad: false,
    theme: "base",
    themeVariables: {
      darkMode: true,
      background: "#0b1210",
      primaryColor: "#16211d",
      primaryTextColor: "#d7e0dc",
      primaryBorderColor: "#4a5a54",
      secondaryColor: "#101915",
      tertiaryColor: "#101915",
      lineColor: "#8aa39a",
      clusterBkg: "#101915",
      clusterBorder: "#3a4a44",
      edgeLabelBackground: "#0b1210",
      fontFamily: '"IBM Plex Mono", monospace',
    },
  });
  try {
    const id = `kiki-mermaid-${++seq}-${Math.random().toString(36).slice(2)}`;
    const { svg: rendered } = await mermaid.render(id, decodeURIComponent(props.graph));
    svg.value = rendered;
  } catch (error) {
    failed.value = true;
    console.error("mermaid render failed", error);
  }
});
</script>

<template>
  <pre v-if="failed" class="kiki-mermaid-fallback">{{ decodeURIComponent(props.graph) }}</pre>
  <div v-else class="kiki-mermaid" v-html="svg"></div>
</template>

<style scoped>
.kiki-mermaid {
  margin: 16px 0;
  display: flex;
  justify-content: center;
  overflow-x: auto;
}

.kiki-mermaid :deep(svg) {
  max-width: 100%;
  height: auto;
}

/* Mermaid measures labels outside VitePress's .vp-doc styles, but the
   rendered labels sit inside them, where `.vp-doc p` inflates line-height
   and margins beyond what mermaid measured — clipping label text. Match
   the measurement styles exactly. */
.kiki-mermaid :deep(svg p),
.kiki-mermaid :deep(svg span) {
  line-height: normal;
  margin: 0;
}

.kiki-mermaid-fallback {
  overflow-x: auto;
}
</style>
