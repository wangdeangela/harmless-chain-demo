#!/usr/bin/env bash
# 部署 OpenAEV（Docker Compose，端口 8888，避免与 8080 冲突）
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(dirname "$SCRIPT_DIR")"
OAE_DIR="$ROOT/openaev-docker"

if [[ ! -d "$OAE_DIR" ]]; then
  echo "克隆 OpenAEV Docker 仓库..."
  git clone --depth 1 https://github.com/OpenAEV-Platform/docker.git "$OAE_DIR"
fi

cd "$OAE_DIR"

if [[ ! -f .env ]]; then
  echo "生成 .env 配置..."
  ADMIN_TOKEN=$(python3 -c "import uuid; print(uuid.uuid4())")
  REG_TOKEN=$(openssl rand -hex 32 2>/dev/null || python3 -c "import secrets; print(secrets.token_hex(32))")
  HEALTH_KEY=$(openssl rand -hex 16 2>/dev/null || python3 -c "import secrets; print(secrets.token_hex(16))")
  ENC_KEY=$(openssl rand -hex 16 2>/dev/null || python3 -c "import secrets; print(secrets.token_hex(16))")
  ENC_SALT=$(openssl rand -hex 8 2>/dev/null || python3 -c "import secrets; print(secrets.token_hex(8))")

  cp .env.sample .env
  # macOS sed
  sed -i '' "s/POSTGRES_USER=ChangeMe/POSTGRES_USER=openaev/" .env
  sed -i '' "s/POSTGRES_PASSWORD=ChangeMe/POSTGRES_PASSWORD=openaev_demo_pass/" .env
  sed -i '' "s/MINIO_ROOT_USER=ChangeMeAccess/MINIO_ROOT_USER=openaevaccess/" .env
  sed -i '' "s/MINIO_ROOT_PASSWORD=ChangeMeKey/MINIO_ROOT_PASSWORD=openaevkey123/" .env
  sed -i '' "s/RABBITMQ_DEFAULT_USER=ChangeMe/RABBITMQ_DEFAULT_USER=openaev/" .env
  sed -i '' "s/RABBITMQ_DEFAULT_PASS=ChangeMe/RABBITMQ_DEFAULT_PASS=openaev_rabbit/" .env
  sed -i '' "s/ELASTIC_MEMORY_SIZE=4G/ELASTIC_MEMORY_SIZE=2G/" .env
  sed -i '' "s/OPENAEV_PORT=8080/OPENAEV_PORT=8888/" .env
  sed -i '' "s/OPENAEV_ADMIN_PASSWORD=changeme/OPENAEV_ADMIN_PASSWORD=OpenAEV@Demo2026/" .env
  sed -i '' "s/OPENAEV_ADMIN_TOKEN=00000000-0000-0000-0000-000000000000/OPENAEV_ADMIN_TOKEN=${ADMIN_TOKEN}/" .env
  sed -i '' "s/PLATFORM_REGISTRATION_TOKEN=ChangeMeWithGeneratedRandomString/PLATFORM_REGISTRATION_TOKEN=${REG_TOKEN}/" .env
  sed -i '' "s/OPENAEV_HEALTHCHECK_KEY=ChangeMe/OPENAEV_HEALTHCHECK_KEY=${HEALTH_KEY}/" .env
  sed -i '' "s/OPENAEV_ADMIN_ENCRYPTION_KEY=/OPENAEV_ADMIN_ENCRYPTION_KEY=${ENC_KEY}/" .env
  sed -i '' "s/OPENAEV_ADMIN_ENCRYPTION_SALT=/OPENAEV_ADMIN_ENCRYPTION_SALT=${ENC_SALT}/" .env

  echo "OPENAEV_ADMIN_TOKEN=${ADMIN_TOKEN}" > "$ROOT/config/openaev.env"
  echo "OPENAEV_URL=http://127.0.0.1:8888" >> "$ROOT/config/openaev.env"
  echo "OPENAEV_ADMIN_EMAIL=admin@filigran.io" >> "$ROOT/config/openaev.env"
  echo "OPENAEV_ADMIN_PASSWORD=OpenAEV@Demo2026" >> "$ROOT/config/openaev.env"
fi

echo "启动 OpenAEV 栈（首次拉镜像可能需要 5–15 分钟）..."
docker compose -p openaev -f docker-compose.yml up -d

echo ""
echo "OpenAEV 部署中，请等待服务就绪后访问:"
echo "  URL:  http://127.0.0.1:8888"
echo "  账号: admin@filigran.io / OpenAEV@Demo2026"
echo "  凭证: $ROOT/config/openaev.env"
