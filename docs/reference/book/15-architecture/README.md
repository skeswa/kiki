# Architecture

This chapter explains the shape of the implementation. Behavioral truth lives in the earlier chapters; architecture exists to make that behavior implementable without smuggling privileged paths through the side door.

Read in this order:

1. [Crate layout](crates.md)
2. [Daemon](daemon.md)
3. [gRPC service](grpc.md)
4. [State schema](schema.md)
5. [Op-log watcher](op-log-watcher.md)
6. [Harness adapter](harness-adapter.md)

The architectural rule is simple: `kkd` owns behavior; clients observe and request. `kk`, `kk-hook`, the overlay, the sidebar, and future UIs all use the same service contract.

## System shape

```mermaid
flowchart LR
    subgraph Clients["Client processes"]
        CLI["kk CLI"]
        TUI["kk overlay TUI"]
        Sidebar["kk sidebar pane"]
        Hook["kk-hook\nexclusive PreToolUse + PostToolBatch sidecar"]
        AgentMcp["Agent MCP client\nread-only transcript tools\n(v1.x polish)"]
        FutureUI["future native / web UI"]
    end

    GrpcSock["~/.config/kiki/kkd.sock\ngRPC over unix socket"]
    McpSock["~/.config/kiki/kkd-mcp.sock\nStreamable HTTP MCP over unix socket\n(v1.x polish)"]
    AdminCred["~/.config/kiki/admin-cred\nbootstrap / broker enrollment only"]
    Broker["enrolled foreground broker\nbegin + display + confirm"]
    Approval["one-shot HumanApproval\nmethod + target + argument + plan digest"]
    HookCred["~/.config/kiki/repos/<repo_id>/credentials/<thread_id>\nread by kk-hook / sidebar / MCP client"]

    AdminCred -. bootstrap .-> Auth
    CLI -. foreground confirmation .-> Broker
    TUI -. foreground confirmation .-> Broker
    Broker -. issues after persisted challenge .-> Approval
    HookCred -. read .-> Hook
    HookCred -. read .-> Sidebar
    HookCred -. read .-> AgentMcp
    CLI --> GrpcSock
    TUI --> GrpcSock
    Sidebar --> GrpcSock
    Hook --> GrpcSock
    FutureUI --> GrpcSock
    AgentMcp --> McpSock

    subgraph Daemon["kkd: single user-scoped daemon"]
        Auth["AuthEnforcer + approval broker\nThreadScoped / HumanApproval\nAdmin bootstrap only"]
        Api["gRPC service\nstable proto contract"]
        McpApi["MCP server\nthread-scoped transcript reads\n(v1.x polish)"]
        Events["server-streaming events"]
        ThreadCtl["ThreadController per thread\nworkspace + tmux + harness lifecycle"]
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
        Tmux["tmux\nsessions and sidebar panes"]
        Harnesses["Claude Code / Codex\nagent sessions + JSONL"]
        Gh["gh / GitHub\nPRs, CI, review comments"]
        Model["cheap model API\nauto metadata drafts"]
    end

    ThreadCtl --> Jj
    ThreadCtl --> Tmux
    ThreadCtl --> Harnesses
    Cascade --> Jj
    Watcher --> Jj
    Transcript --> Harnesses
    Github --> Gh
    Metadata --> Model
```
