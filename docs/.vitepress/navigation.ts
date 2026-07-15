import type { DefaultTheme } from "vitepress";

/**
 * Renders a chapter number as a dimmed prefix in the sidebar and pager.
 * The literal space keeps the accessible name readable ("01 orientation")
 * wherever the text is flattened, e.g. screen readers and search.
 */
const ch = (no: string, title: string) => `<span class="ch-no">${no}</span> ${title}`;

/**
 * Sidebars are keyed by path prefix so future non-book sections (e.g. a
 * standalone guide under /guide/) can ship their own sidebar without
 * touching the reference book's. Unnumbered pages skip the ch() helper.
 */
const referenceSidebar: DefaultTheme.SidebarItem[] = [
  {
    text: "start here",
    items: [
      { text: "the reference", link: "/reference/" },
      { text: ch("00", "abstract"), link: "/reference/book/00-abstract" },
      { text: ch("01", "orientation"), link: "/reference/book/01-orientation" },
      { text: ch("02", "glossary"), link: "/reference/book/02-glossary" },
      { text: ch("03", "user stories"), link: "/reference/book/03-user-stories" },
    ],
  },
  {
    text: "coordination core",
    items: [
      { text: ch("04", "invariants"), link: "/reference/book/04-invariants" },
      { text: ch("05", "threads"), link: "/reference/book/05-threads" },
      { text: ch("06", "authority"), link: "/reference/book/06-authority" },
      { text: ch("07", "cascade"), link: "/reference/book/07-cascade" },
      { text: ch("08", "transcript"), link: "/reference/book/08-transcript" },
      { text: ch("09", "publishing"), link: "/reference/book/09-publishing" },
      { text: ch("10", "metadata evolution"), link: "/reference/book/10-metadata" },
    ],
  },
  {
    text: "surfaces",
    items: [
      { text: ch("11", "commands"), link: "/reference/book/11-commands" },
      { text: ch("12", "interface"), link: "/reference/book/12-interface/" },
      { text: ch("13", "configuration"), link: "/reference/book/13-configuration" },
      { text: ch("14", "observability"), link: "/reference/book/14-observability" },
    ],
  },
  {
    text: "implementation",
    collapsed: true,
    items: [
      { text: ch("15", "architecture"), link: "/reference/book/15-architecture/" },
      { text: ch("16", "testing"), link: "/reference/book/16-testing" },
      { text: ch("17", "build sequencing"), link: "/reference/book/17-build-sequencing" },
      { text: ch("18", "roadmap"), link: "/reference/book/18-roadmap" },
      { text: ch("19", "naming"), link: "/reference/book/19-naming" },
      { text: ch("20", "decisions"), link: "/reference/book/20-decisions/" },
    ],
  },
];

export const sidebar: DefaultTheme.Sidebar = {
  "/reference/": referenceSidebar,
};
