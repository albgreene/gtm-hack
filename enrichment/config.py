"""Settings and fixed values for enrichment. Secrets come only from environment variables."""

import os

# Same list as FREE_MAIL in the Hermes qualify-lead worker, so both sides agree on what isn't a company.
FREE_MAIL = {"gmail.com", "googlemail.com", "outlook.com", "hotmail.com", "live.com", "web.de", "gmx.de", "gmx.net",
             "icloud.com", "me.com", "yahoo.com", "t-online.de", "proton.me", "protonmail.com", "aol.com"}

HERMES_URL = os.environ.get("QUALIFY_LEAD_URL",
                            "https://hermes-agent-h0rd.srv2036292.hstgr.cloud/webhooks/qualify-lead")
MAX_PAYLOAD_BYTES = 65536

AIARK_MCP_URL = "https://api.ai-ark.com/v1/mcp"
NEEDLE_MCP_URL = "https://needle.app/mcp/v1"
# The LinkedIn account Needle acts as. Read-only: only the tools below may ever be called with it.
NEEDLE_ACCOUNT = "01a181fb-417f-7f18-a037-e554eec499fd"
NEEDLE_READ_TOOLS = {"needleGetLinkedinProfile", "needleSearchLinkedinPeopleClassic", "needleGetLinkedinCompany",
                     "needleListLinkedinCompanyPosts", "needleListLinkedinCompanyJobs", "needleGetLinkedinJob"}

FIRECRAWL_URL = "https://api.firecrawl.dev/v2"
HUBSPOT_URL = "https://api.hubapi.com"

LLM_BASE_URL = "https://openrouter.ai/api"
LLM_MODEL = os.environ.get("ENRICH_MODEL", "anthropic/claude-opus-5.5")

# Wall-clock budget for one lead; sources that run longer are recorded as errors.
SOURCE_TIMEOUT_S = 90
USER_AGENT = "Mozilla/5.0 (compatible; KugelAudio-enrichment/1.0; +https://kugelaudio.com)"


def env(name: str, default: str = "") -> str:
    return os.environ.get(name, default).strip()
