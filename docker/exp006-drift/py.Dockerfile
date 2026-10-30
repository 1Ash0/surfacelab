# EXP-006 drift probe: same packages, LATEST releases (unpinned).
FROM python:3.12-slim
RUN pip install --no-cache-dir mcp-server-git mcp-server-fetch mcp-server-time awslabs.aws-documentation-mcp-server
USER 1000:1000
ENV HOME=/tmp
