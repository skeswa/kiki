import DefaultTheme from "vitepress/theme";
import "@fontsource/ibm-plex-mono/latin-400.css";
import "@fontsource/ibm-plex-mono/latin-400-italic.css";
import "@fontsource/ibm-plex-mono/latin-500.css";
import "@fontsource/ibm-plex-mono/latin-600.css";
import KikiHome from "./KikiHome.vue";
import SlotCycle from "./SlotCycle.vue";
import "./theme.css";

export default {
  extends: DefaultTheme,
  enhanceApp({ app }) {
    app.component("KikiHome", KikiHome);
    app.component("SlotCycle", SlotCycle);
  },
};
