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
        Hook["kk-hook\nClaude Code PreToolUse sidecar"]
        AgentMcp["Agent MCP client\nread-only transcript tools\n(stretch/post-v1)"]
        FutureUI["future native / web UI"]
    end

    GrpcSock["~/.kiki/kkd.sock\ngRPC over unix socket"]
    McpSock["~/.kiki/kkd-mcp.sock\nStreamable HTTP MCP over unix socket\n(stretch/post-v1)"]
    AdminCred["~/.kiki/admin-cred\nread by kk CLI / TUI"]
    HookCred["<workspace>/.kiki/hook-cred\nread by kk-hook / sidebar / MCP client"]

    AdminCred -. read .-> CLI
    AdminCred -. read .-> TUI
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
        Auth["AuthEnforcer\nAdmin / ThreadScoped"]
        Api["gRPC service\nstable proto contract"]
        McpApi["MCP server\nthread-scoped transcript reads\n(stretch/post-v1)"]
        Events["server-streaming events"]
        ThreadCtl["ThreadController per thread\nworkspace + tmux + harness lifecycle"]
        Cascade["CascadeOrchestrator\npause / rebase / inject / acknowledge"]
        Watcher["jj op-log watcher\nexternal op detection"]
        Transcript["ThreadTranscriptStore\nJSONL tail + local recall"]
        Metadata["MetadataLedger + AICompose\nauto-describe / auto-rename"]
        Github["GitHub poller / publisher"]
        Config["ConfigLoader\nlayered TOML + thread sqlite"]
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
        UserDb["~/.kiki/state.db\nrepo registry + daemon meta"]
        RepoDb["<repo>/.kiki/state.db\nthreads, credentials, audit, transcripts"]
    end

    Auth --> UserDb
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
        Claude["Claude Code\nagent sessions + JSONL"]
        Gh["gh / GitHub\nPRs, CI, review comments"]
        Model["cheap model API\nauto metadata drafts"]
    end

    ThreadCtl --> Jj
    ThreadCtl --> Tmux
    ThreadCtl --> Claude
    Cascade --> Jj
    Watcher --> Jj
    Transcript --> Claude
    Github --> Gh
    Metadata --> Model
```
