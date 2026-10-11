# LeetCode Study MCP

Read-only local MCP server for your full solved list, random unseen problems,
and review of your own submissions. Recommendations default to free Medium
problems outside NC150 and return only IDs, titles, and links. No pattern hints.

## Install (Mac/Linux, Python 3.10+)

Clone the repository and install the MCP SDK:

```bash
git clone https://github.com/raghavkaashyap/lc-mcp.git
cd lc-mcp
python3 -m venv .venv
.venv/bin/pip install 'mcp>=1.12,<2'
```

The server uses the official MCP Python SDK's maintained v1 interface, pinned
below v2: https://py.sdk.modelcontextprotocol.io/v1/ .

## Configure your local MCP client

Add this server entry to a client that supports local stdio MCP servers.
Replace BOTH absolute paths with your cloned repository location. The host must launch
`server.py` using this virtual environment's Python.

```json
{
  "mcpServers": {
    "leetcode": {
      "command": "/ABSOLUTE/PATH/lc-mcp/.venv/bin/python",
      "args": ["/ABSOLUTE/PATH/lc-mcp/server.py"],
      "env": {
        "LEETCODE_USERNAME": "YOUR_USERNAME",
        "LEETCODE_SESSION": "YOUR_LOCAL_SESSION_COOKIE",
        "LEETCODE_CSRF_TOKEN": "YOUR_LOCAL_CSRF_COOKIE"
      }
    }
  }
}
```

Find `LEETCODE_SESSION` and `csrftoken` in your browser's developer tools under
Storage/Application → Cookies → https://leetcode.com while logged in.
Enter their values only in your local MCP configuration; do not paste them
into chat or commit them. They provide access to your account. Refresh them
locally if LeetCode expires the session. No API key or paid AI service is needed.

This repository does not automatically install a connector into this conversation.
It is a local stdio server, not a public HTTPS endpoint. A client that requires
remote MCP needs a separate hosting/authentication setup.

## Export fallback (no cookies in MCP config)

If direct requests get HTTP 403, open LeetCode while signed in and run the
contents of `export-catalog.js` in the browser developer console. Read it first:
it only fetches the same site's problem catalog and downloads JSON.

Configure these environment variables instead:

```json
{
  "LEETCODE_USERNAME": "YOUR_USERNAME",
  "LEETCODE_CATALOG_FILE": "/ABSOLUTE/PATH/leetcode-catalog.json"
}
```

With this mode, `solved_problems` and `recommend_problems` work offline from
the snapshot. Re-export after solving more problems. Account verification and
submission-code tools still require live session access. Keep your exported
history private. The export has no session cookies.

## Tools

- `account_status`: verifies the session and optional expected username.
- `solved_problems`: complete solved catalog, with count consistency checks.
- `recommend_problems`: random free unseen problems; NC150 excluded by default.
  Optional difficulty, extra excluded IDs, reproducible seed, and cache refresh.
- `recent_accepted_submissions`: public recent activity, explicitly marked partial.
- `problem_submissions`: your submission IDs for a problem slug; paginate by offset.
- `submission_code`: fetch code for an accessible submission ID for review.

Example requests to your connected assistant:

> Give me 10 unseen mediums outside NC150. Only list names and links.
> Read my submissions for accounts-merge and review my most recent accepted code.

The assistant can reason about code returned by the server; this server does
not contain a separate AI recommender. It randomly samples eligible problems.
It does not yet balance batches by topic or infer mastery from past attempts.

## Validation and limits

```bash
python3 -m unittest discover -s tests -v
.venv/bin/python tests/smoke_mcp.py
```

Nine core tests and a real MCP stdio initialization/tool-discovery test passed
in the build environment. Live LeetCode returned HTTP 403 there. Authenticated
catalog, submission endpoints, and the browser export therefore still need
validation with your account. LeetCode's web endpoints are unofficial and can
change. Server errors are sanitized, redirects are disabled, and no mutations
or code submissions are exposed. The catalog is cached for five minutes;
pass `refresh=true` after completing a problem. Missing/invalid authentication
never silently falls back to incomplete public history.
