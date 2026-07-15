import type { DefaultTheme } from "vitepress";

export const sidebar: DefaultTheme.Sidebar = [
  {
    text: "start here",
    items: [
      { text: "the reference", link: "/reference/" },
      { text: "00  abstract", link: "/reference/book/00-abstract" },
      { text: "01  orientation", link: "/reference/book/01-orientation" },
      { text: "02  glossary", link: "/reference/book/02-glossary" },
      { text: "03  user stories", link: "/reference/book/03-user-stories" },
    ],
  },
  {
    text: "coordination core",
    items: [
      { text: "04  invariants", link: "/reference/book/04-invariants" },
      { text: "05  threads", link: "/reference/book/05-threads" },
      { text: "06  authority", link: "/reference/book/06-authority" },
      { text: "07  cascade", link: "/reference/book/07-cascade" },
      { text: "08  transcript", link: "/reference/book/08-transcript" },
      { text: "09  publishing", link: "/reference/book/09-publishing" },
      { text: "10  metadata evolution", link: "/reference/book/10-metadata" },
    ],
  },
  {
    text: "surfaces",
    items: [
      { text: "11  commands", link: "/reference/book/11-commands" },
      { text: "12  interface", link: "/reference/book/12-interface/" },
      { text: "13  configuration", link: "/reference/book/13-configuration" },
      { text: "14  observability", link: "/reference/book/14-observability" },
    ],
  },
  {
    text: "implementation",
    collapsed: true,
    items: [
      { text: "15  architecture", link: "/reference/book/15-architecture/" },
      { text: "16  testing", link: "/reference/book/16-testing" },
      { text: "17  build sequencing", link: "/reference/book/17-build-sequencing" },
      { text: "18  roadmap", link: "/reference/book/18-roadmap" },
      { text: "19  naming", link: "/reference/book/19-naming" },
      { text: "20  decisions", link: "/reference/book/20-decisions/" },
    ],
  },
];
