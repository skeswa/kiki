<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from "vue";

const props = withDefaults(
  defineProps<{
    phrases: string[];
    interval?: number;
  }>(),
  { interval: 2600 },
);

const active = ref(0);
let timer: ReturnType<typeof setInterval> | undefined;

onMounted(() => {
  if (props.phrases.length < 2 || window.matchMedia("(prefers-reduced-motion: reduce)").matches)
    return;
  timer = setInterval(() => {
    active.value = (active.value + 1) % props.phrases.length;
  }, props.interval);
});

onBeforeUnmount(() => clearInterval(timer));
</script>

<template>
  <span class="slot-cycle" aria-live="polite">
    <Transition name="slot-swap" mode="out-in">
      <span :key="phrases[active]">{{ phrases[active] }}</span>
    </Transition>
  </span>
</template>
