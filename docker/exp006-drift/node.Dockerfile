# EXP-006 drift probe: same packages, LATEST releases (dist-tag latest, explicit so npm cannot fall back to an older engine-compatible release). EXP-006 node servers, each in its own prefix (/opt/<name>) so bin names cannot clash.
# --ignore-scripts: no package install hooks run at build time.
FROM node:22-slim
RUN npm install --prefix /opt/filesystem --ignore-scripts --no-audit --no-fund @modelcontextprotocol/server-filesystem@latest
RUN npm install --prefix /opt/memory --ignore-scripts --no-audit --no-fund @modelcontextprotocol/server-memory@latest
RUN npm install --prefix /opt/sequential-thinking --ignore-scripts --no-audit --no-fund @modelcontextprotocol/server-sequential-thinking@latest
RUN npm install --prefix /opt/notion --ignore-scripts --no-audit --no-fund @notionhq/notion-mcp-server@latest
RUN npm install --prefix /opt/playwright --ignore-scripts --no-audit --no-fund @playwright/mcp@latest
RUN npm install --prefix /opt/chrome-devtools --ignore-scripts --no-audit --no-fund chrome-devtools-mcp@latest
RUN npm install --prefix /opt/brave-search --ignore-scripts --no-audit --no-fund @brave/brave-search-mcp-server@latest
RUN npm install --prefix /opt/tavily --ignore-scripts --no-audit --no-fund tavily-mcp@latest
RUN npm install --prefix /opt/firecrawl --ignore-scripts --no-audit --no-fund firecrawl-mcp@latest
RUN npm install --prefix /opt/supabase --ignore-scripts --no-audit --no-fund @supabase/mcp-server-supabase@latest
RUN npm install --prefix /opt/neon --ignore-scripts --no-audit --no-fund @neondatabase/mcp-server-neon@latest
RUN npm install --prefix /opt/mongodb --ignore-scripts --no-audit --no-fund mongodb-mcp-server@latest
RUN npm install --prefix /opt/stripe --ignore-scripts --no-audit --no-fund @stripe/mcp@latest
RUN npm install --prefix /opt/context7 --ignore-scripts --no-audit --no-fund @upstash/context7-mcp@latest
USER 1000:1000
ENV HOME=/tmp
