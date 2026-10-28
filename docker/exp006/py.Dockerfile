# EXP-006 Python servers, pinned.
FROM python:3.12-slim
RUN pip install --no-cache-dir mcp-server-git==2026.10.19 mcp-server-fetch==2026.10.24 mcp-server-time==2026.10.19 awslabs.aws-documentation-mcp-server==1.2.3
USER 1000:1000
ENV HOME=/tmp
