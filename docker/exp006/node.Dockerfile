# EXP-006 node servers, each in its own prefix (/opt/<name>) so bin names cannot clash.
# --ignore-scripts: no package install hooks run at build time.
FROM node:22-slim
RUN npm install --prefix /opt/filesystem --ignore-scripts --no-audit --no-fund @modelcontextprotocol/server-filesystem@2.0.1
RUN npm install --prefix /opt/memory --ignore-scripts --no-audit --no-fund @modelcontextprotocol/server-memory@2.0.0
RUN npm install --prefix /opt/sequential-thinking --ignore-scripts --no-audit --no-fund @modelcontextprotocol/server-sequential-thinking@2.0.0
RUN npm install --prefix /opt/notion --ignore-scripts --no-audit --no-fund @notionhq/notion-mcp-server@2.6.0
RUN npm install --prefix /opt/playwright --ignore-scripts --no-audit --no-fund @playwright/mcp@0.0.83
RUN npm install --prefix /opt/chrome-devtools --ignore-scripts --no-audit --no-fund chrome-devtools-mcp@1.12.0
RUN npm install --prefix /opt/brave-search --ignore-scripts --no-audit --no-fund @brave/brave-search-mcp-server@2.1.4
RUN npm install --prefix /opt/tavily --ignore-scripts --no-audit --no-fund tavily-mcp@0.2.22
RUN npm install --prefix /opt/firecrawl --ignore-scripts --no-audit --no-fund firecrawl-mcp@3.36.0
RUN npm install --prefix /opt/supabase --ignore-scripts --no-audit --no-fund @supabase/mcp-server-supabase@0.14.0
RUN npm install --prefix /opt/neon --ignore-scripts --no-audit --no-fund @neondatabase/mcp-server-neon@0.6.5
RUN npm install --prefix /opt/mongodb --ignore-scripts --no-audit --no-fund mongodb-mcp-server@3.1.0
RUN npm install --prefix /opt/stripe --ignore-scripts --no-audit --no-fund @stripe/mcp@0.3.3
RUN npm install --prefix /opt/context7 --ignore-scripts --no-audit --no-fund @upstash/context7-mcp@4.4.4
USER 1000:1000
ENV HOME=/tmp
