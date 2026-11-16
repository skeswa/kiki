# Architecture

This chapter explains the shape of the implementation. Behavioral truth lives in the earlier chapters; architecture exists to make that behavior implementable without smuggling privileged paths through the side door.

Read in this order:

1. [Crate layout](crates.md)
2. [Daemon](daemon.md)
3. [Terminal runtime](terminal-runtime.md)
4. [gRPC service](grpc.md)
5. [State schema](schema.md)
6. [Op-log watcher](op-log-watcher.md)
7. [Harness adapter](harness-adapter.md)

The architectural rule is simple: `kkd` owns behavior; clients observe and request. `kk`, the pane launcher, `kk-hook`, the overlay, the optional `ui` pane, and future UIs all use the same service contract. Terminals are hosted by a dedicated Herdr server that `kkd` drives through `TerminalRuntime`; which terminal a human is looking at belongs to each Herdr client and is requested by `kk` through `TerminalClient`.

## System shape

```mermaid
flowchart LR
    subgraph Clients["Client processes"]
        CLI["kk CLI\nTerminalClient: caller-local focus, attach"]
        TUI["kk overlay TUI\n(v1.x)"]
        UiPane["kk ui role pane\n(v1.x, optional)"]
        Launcher["pane launcher\nhidden kk subcommand\ndirect child of every role pane"]
        Hook["kk-hook\nexclusive PreToolUse + PostToolBatch sidecar"]
        HookLauncher["hook launcher\nper thread, hook side\nbatch admission cache"]
        AgentMcp["Agent MCP client\nread-only transcript tools\n(v1.x polish)"]
        FutureUI["future native / web UI"]
    end

    GrpcSock["~/.config/kiki/kkd.sock\ngRPC over unix socket"]
    McpSock["~/.config/kiki/kkd-mcp.sock\nStreamable HTTP MCP over unix socket\n(v1.x polish)"]
    AdminCred["~/.config/kiki/admin-cred\nbootstrap / broker enrollment only"]
    Broker["enrolled foreground broker\nbegin + display + confirm"]
    Approval["one-shot HumanApproval\nmethod + target + argument + plan digest"]
    HookCred["~/.config/kiki/repos/<repo_id>/credentials/<thread_id>\nread by kk-hook / pane launcher / ui pane / MCP client"]

    AdminCred -. bootstrap .-> Auth
    CLI -. foreground confirmation .-> Broker
    TUI -. foreground confirmation .-> Broker
    Broker -. issues after persisted challenge .-> Approval
    HookCred -. read .-> Hook
    HookCred -. read .-> Launcher
    HookCred -. read .-> UiPane
    HookCred -. read .-> AgentMcp
    CLI --> GrpcSock
    TUI --> GrpcSock
    UiPane --> GrpcSock
    Launcher --> GrpcSock
    Hook --> GrpcSock
    HookLauncher --> GrpcSock
    HookLauncher -. answers for a dead sidecar .-> Hook
    FutureUI --> GrpcSock
    AgentMcp --> McpSock

    subgraph Daemon["kkd: single user-scoped daemon"]
        Auth["AuthEnforcer + approval broker\nThreadScoped / HumanApproval\nAdmin bootstrap only"]
        Api["gRPC service\nstable proto contract"]
        McpApi["MCP server\nthread-scoped transcript reads\n(v1.x polish)"]
        Events["server-streaming events"]
        ThreadCtl["ThreadController per thread\nworkspace + terminal group + harness lifecycle"]
        TermRt["TerminalRuntime\nensure server / provision / observe / close / publish / notify"]
        ProcSup["ProcessSupervisor\nidentity, freeze, verified resume and exit,\nholder inventory, orphan scan"]
        Cascade["CascadeOrchestrator\nclassify / reconcile / batch barrier / acknowledge"]
        Watcher["jj op-log watcher\nexternal op detection"]
        Transcript["ThreadTranscriptStore\nJSONL tail + consented recall\n(v1.x)"]
        Metadata["MetadataLedger + AICompose\nauto-describe / auto-rename\n(v1.x)"]
        Github["GitHub poller / publisher\n(v1.x)"]
        Config["ConfigLoader\nminimal acceptance keys\nfull layering in v1.x"]
    end

    GrpcSock --> Auth --> Api
    McpSock --> Auth --> McpApi
    Api --> Events
    Api --> ThreadCtl
    ThreadCtl --> TermRt
    ThreadCtl --> ProcSup
    Api --> Cascade
    Api --> Transcript
    Api --> Metadata
    Api --> Github
    Api --> Config
    McpApi --> Transcript
    Watcher --> Cascade
    Watcher --> Transcript

    subgraph State["Persistent state"]
        UserDb["~/.config/kiki/state.db\nrepo registry, presenters, unscoped audit"]
        RepoDb["~/.config/kiki/repos/<repo_id>/state.db\nthreads, credentials, audit, transcripts\n(centralized; no state inside the source repo)"]
    end

    Auth --> UserDb
    Approval -. validate and claim .-> Auth
    Auth --> RepoDb
    Api --> UserDb
    Api --> RepoDb
    Transcript --> RepoDb
    Metadata --> RepoDb
    Cascade --> RepoDb
    Watcher --> RepoDb

    subgraph Tools["External tools kk coordinates"]
        Jj["jj / git repo\nworkspaces, bookmarks, op log"]
        Herdr["dedicated Herdr server (session: kiki)\nstarted only by kkd, outside the terminal application\none terminal group per thread\nrole panes, native sidebar, toasts"]
        OsProc["local OS\nprocesses and workspace holders"]
        Harnesses["Claude Code / Codex\nagent sessions + JSONL"]
        Gh["gh / GitHub\nPRs, CI, review comments"]
        Model["cheap model API\nauto metadata drafts"]
    end

    ThreadCtl --> Jj
    TermRt -- "JSON socket API" --> Herdr
    ProcSup --> OsProc
    CLI -. "focus / attach" .-> Herdr
    Herdr -. "direct argv child of each role pane" .-> Launcher
    Launcher -. "agent role: starts as its child\nafter the launch gate opens" .-> Harnesses
    Cascade --> Jj
    Watcher --> Jj
    Transcript --> Harnesses
    Github --> Gh
    Metadata --> Model
```
