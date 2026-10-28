# EXP-013 additions: Desktop Commander (node), DuckDuckGo search (python), and git with an empty
# repository at /repo so mcp-server-git can start. --ignore-scripts: no npm install hooks run.
FROM surfacelab/exp006-node:1
USER root
RUN npm install --prefix /opt/desktop-commander --ignore-scripts --no-audit --no-fund @wonderwhy-er/desktop-commander@0.3.1
RUN apt-get update && apt-get install -y --no-install-recommends python3 python3-pip git && rm -rf /var/lib/apt/lists/* \
 && pip3 install --break-system-packages --no-cache-dir duckduckgo-mcp-server==0.7.0 mcp-server-git==2026.10.19 \
 && git init -q /repo && chown -R 1000:1000 /repo
USER 1000:1000
ENV HOME=/tmp
