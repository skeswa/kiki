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
    ],
  },
  {
    text: "coordination core",
    items: [
      { text: ch("02", "invariants"), link: "/reference/book/02-invariants" },
      { text: ch("03", "threads"), link: "/reference/book/03-threads" },
      { text: ch("04", "authority"), link: "/reference/book/04-authority" },
      { text: ch("05", "cascade"), link: "/reference/book/05-cascade" },
      { text: ch("06", "transcript"), link: "/reference/book/06-transcript" },
      { text: ch("07", "publishing"), link: "/reference/book/07-publishing" },
      { text: ch("08", "metadata evolution"), link: "/reference/book/08-metadata" },
    ],
  },
  {
    text: "surfaces",
    items: [
      { text: ch("09", "commands"), link: "/reference/book/09-commands" },
      { text: ch("10", "interface"), link: "/reference/book/10-interface/" },
      { text: ch("11", "configuration"), link: "/reference/book/11-configuration" },
      { text: ch("12", "observability"), link: "/reference/book/12-observability" },
    ],
  },
  {
    text: "implementation",
    collapsed: true,
    items: [
      { text: ch("13", "architecture"), link: "/reference/book/13-architecture/" },
      { text: ch("14", "testing"), link: "/reference/book/14-testing" },
      { text: ch("15", "build sequencing"), link: "/reference/book/15-build-sequencing" },
      { text: ch("16", "roadmap"), link: "/reference/book/16-roadmap" },
      { text: ch("17", "decisions"), link: "/reference/book/17-decisions/" },
    ],
  },
  {
    text: "appendices",
    collapsed: true,
    items: [
      { text: ch("A", "glossary"), link: "/reference/book/appendix-a-glossary" },
      { text: ch("B", "user stories"), link: "/reference/book/appendix-b-user-stories" },
      { text: ch("C", "naming"), link: "/reference/book/appendix-c-naming" },
    ],
  },
];

export const sidebar: DefaultTheme.Sidebar = {
  "/reference/": referenceSidebar,
};
