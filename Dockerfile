FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    && rm -rf /var/lib/apt/lists/*

COPY trading/ trading/
COPY pyproject.toml README.md ./

RUN pip install --no-cache-dir -e ".[all]"

EXPOSE 8501

ENTRYPOINT ["trading"]
CMD ["dashboard"]
