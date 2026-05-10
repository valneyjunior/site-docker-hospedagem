# Deploy — Hostweb Planos 2026
**Ubuntu 24.04.4 LTS · Docker · Nginx · PostgreSQL · Flask**

---

## Sumário

1. [Requisitos mínimos](#1-requisitos-mínimos)
2. [Preparar o servidor](#2-preparar-o-servidor)
3. [Instalar Docker e Docker Compose](#3-instalar-docker-e-docker-compose)
4. [Enviar o projeto para o servidor](#4-enviar-o-projeto-para-o-servidor)
5. [Configurar variáveis de ambiente](#5-configurar-variáveis-de-ambiente)
6. [Configurar HTTPS com Certbot](#6-configurar-https-com-certbot)
7. [Subir os containers](#7-subir-os-containers)
8. [Verificar a instalação](#8-verificar-a-instalação)
9. [Configurar Webhook do Stripe](#9-configurar-webhook-do-stripe)
10. [Comandos de manutenção](#10-comandos-de-manutenção)
11. [Atualizar o projeto](#11-atualizar-o-projeto)
12. [Troubleshooting](#12-troubleshooting)

---

## 1. Requisitos mínimos

| Recurso   | Mínimo         | Recomendado    |
|-----------|----------------|----------------|
| CPU       | 1 vCPU         | 2 vCPUs        |
| RAM       | 1 GB           | 2 GB           |
| Disco     | 20 GB SSD      | 40 GB SSD      |
| OS        | Ubuntu 24.04.4 LTS | Ubuntu 24.04.4 LTS |
| Portas    | 80, 443        | 80, 443        |

**Pré-requisitos externos:**
- Domínio apontando para o IP do servidor (registro A configurado)
- Conta Stripe com chaves de API e webhook criados
- Conta SMTP para envio de e-mails (Gmail App Password, SendGrid, etc.)

---

## 2. Preparar o servidor

Conecte-se via SSH e execute os passos abaixo como usuário com `sudo`.

```bash
# Atualizar pacotes do sistema
sudo apt update && sudo apt upgrade -y

# Instalar dependências essenciais
sudo apt install -y \
  curl \
  git \
  ufw \
  ca-certificates \
  gnupg \
  lsb-release

# Configurar firewall (UFW)
sudo ufw allow OpenSSH
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw --force enable
sudo ufw status
```

---

## 3. Instalar Docker e Docker Compose

```bash
# Adicionar repositório oficial do Docker
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg \
  | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg

echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
  https://download.docker.com/linux/ubuntu \
  $(lsb_release -cs) stable" \
  | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# Instalar Docker Engine + Compose plugin
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

# Adicionar usuário atual ao grupo docker (evita usar sudo em cada comando)
sudo usermod -aG docker $USER
newgrp docker

# Verificar instalação
docker --version
docker compose version
```

---

## 4. Enviar o projeto para o servidor

Escolha uma das duas abordagens:

### Opção A — Git (recomendado)

```bash
# No servidor, clonar o repositório
cd /opt
sudo git clone https://github.com/<seu-usuario>/hostweb-planos-2026-docker.git hostweb
sudo chown -R $USER:$USER /opt/hostweb
cd /opt/hostweb
```

### Opção B — SCP / SFTP (upload manual)

No seu computador local (PowerShell ou terminal):

```bash
# Copiar todo o projeto via SCP
scp -r "C:\Users\valney.junior\OneDrive - hostweb.cloud\Documentos\vscode\Hostweb-planos-2026-docker" \
  usuario@IP_DO_SERVIDOR:/opt/hostweb
```

Depois no servidor:
```bash
cd /opt/hostweb
```

---

## 5. Configurar variáveis de ambiente

O arquivo `.env` **não é incluído no repositório** por segurança. Crie-o a partir do template:

```bash
cp .env.example .env
nano .env
```

Preencha cada variável:

```dotenv
# ── PostgreSQL ────────────────────────────────────────────────────────────
# Senha forte para o banco de dados (mínimo 24 caracteres aleatórios)
POSTGRES_PASSWORD=SenhaForteAqui2026!

# ── Stripe ────────────────────────────────────────────────────────────────
# Chave secreta do Stripe (painel Stripe → Developers → API Keys)
STRIPE_SECRET_KEY=sk_live_...

# Segredo do webhook (painel Stripe → Developers → Webhooks → Signing secret)
# ATENÇÃO: começa com "whsec_", NÃO com "sk_" ou "pk_"
STRIPE_WEBHOOK_SECRET=whsec_...

# ── SMTP ──────────────────────────────────────────────────────────────────
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=seu-email@gmail.com
# Gmail: use App Password (Conta Google → Segurança → Senhas de app)
SMTP_PASS=xxxx xxxx xxxx xxxx
EMAIL_FROM=noreply@seudominio.com.br
EMAIL_REPLY=comercial@hostweb.com.br

# ── URLs (substituir pelo domínio real) ───────────────────────────────────
SUCCESS_URL=https://seudominio.com.br/sucesso.html?session_id={CHECKOUT_SESSION_ID}
CANCEL_URL=https://seudominio.com.br/?cancelado=1
VERIFICACAO_URL=https://seudominio.com.br/verificar-aceite

# ── Flask ─────────────────────────────────────────────────────────────────
PORT=8080
```

Ajuste as permissões do arquivo:

```bash
chmod 600 .env
```

---

## 6. Configurar HTTPS com Certbot

A abordagem recomendada é usar o **Nginx do host** como proxy reverso com SSL/TLS, repassando o tráfego para o Nginx do Docker (porta 80 interna).

### 6.1 Instalar Nginx e Certbot no host

```bash
sudo apt install -y nginx certbot python3-certbot-nginx
```

### 6.2 Alterar a porta do Docker para não conflitar com o Nginx do host

Edite `docker-compose.yml` e mude a porta do nginx:

```yaml
  nginx:
    ports:
      - "8080:80"   # era "80:80"
```

> O Nginx do host vai escutar nas portas 80 e 443 e repassar para o Docker na porta 8080.

### 6.3 Criar o virtual host no Nginx do host

```bash
sudo nano /etc/nginx/sites-available/hostweb
```

Cole o conteúdo abaixo (substitua `seudominio.com.br`):

```nginx
server {
    listen 80;
    server_name seudominio.com.br www.seudominio.com.br;

    location / {
        proxy_pass         http://127.0.0.1:8080;
        proxy_set_header   Host              $host;
        proxy_set_header   X-Real-IP         $remote_addr;
        proxy_set_header   X-Forwarded-For   $proxy_add_x_forwarded_for;
        proxy_set_header   X-Forwarded-Proto $scheme;
        proxy_read_timeout 60s;
    }
}
```

```bash
# Ativar o site e testar configuração
sudo ln -s /etc/nginx/sites-available/hostweb /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### 6.4 Emitir certificado SSL com Let's Encrypt

```bash
sudo certbot --nginx -d seudominio.com.br -d www.seudominio.com.br \
  --non-interactive --agree-tos -m juridico@hostweb.com.br
```

O Certbot atualiza automaticamente o virtual host com as diretivas SSL e cria um cron para renovação. Verifique:

```bash
sudo certbot renew --dry-run
```

---

## 7. Subir os containers

```bash
cd /opt/hostweb

# Construir imagens e subir em background
docker compose up -d --build

# Acompanhar os logs na inicialização
docker compose logs -f
```

Aguarde até ver as mensagens:
- `postgres: database system is ready to accept connections`
- `flask: [INFO] Starting gunicorn`
- `nginx: start worker processes`

---

## 8. Verificar a instalação

```bash
# Status dos containers (todos devem estar "Up")
docker compose ps

# Teste HTTP local
curl -I http://localhost:8080

# Teste HTTPS via domínio (de fora do servidor)
curl -I https://seudominio.com.br

# Verificar health do banco de dados
docker compose exec postgres pg_isready -U hostweb -d hostweb

# Verificar endpoint de saúde da API Flask
curl http://localhost:8080/health
```

Acesse `https://seudominio.com.br` no navegador e confirme:
- Página de planos carrega normalmente
- Seletores de período funcionam (preços atualizam)
- Botão "Contratar Agora" redireciona para `/aceite/`

---

## 9. Configurar Webhook do Stripe

O endpoint de webhook está em `/webhook` (roteado pelo Nginx para o Flask).

1. Acesse o painel Stripe: **Developers → Webhooks → Add endpoint**
2. URL: `https://seudominio.com.br/webhook`
3. Eventos a escutar:
   - `checkout.session.completed`
   - `payment_intent.payment_failed`
4. Copie o **Signing secret** (`whsec_...`) e cole em `.env` → `STRIPE_WEBHOOK_SECRET`
5. Reinicie o Flask para carregar a variável:

```bash
docker compose restart flask
```

---

## 10. Comandos de manutenção

```bash
# Ver logs em tempo real
docker compose logs -f flask
docker compose logs -f nginx

# Reiniciar um serviço específico
docker compose restart flask

# Parar tudo
docker compose down

# Parar e remover volumes (ATENÇÃO: apaga o banco de dados)
docker compose down -v

# Backup do banco de dados
docker compose exec postgres pg_dump -U hostweb hostweb \
  > backup_$(date +%Y%m%d_%H%M%S).sql

# Restaurar backup
docker compose exec -T postgres psql -U hostweb hostweb < backup_20260504_120000.sql

# Acessar o shell do container Flask
docker compose exec flask bash

# Acessar o psql
docker compose exec postgres psql -U hostweb -d hostweb
```

---

## 11. Atualizar o projeto

```bash
cd /opt/hostweb

# Puxar alterações do repositório
git pull origin main

# Reconstruir apenas a imagem Flask (se houver mudanças no backend)
docker compose up -d --build flask

# Ou reconstruir tudo
docker compose up -d --build
```

> Arquivos do frontend (`frontend/`) são servidos diretamente pelo Nginx via volume — não exigem rebuild, apenas um `docker compose restart nginx`.

---

## 12. Troubleshooting

### Container não sobe

```bash
# Ver erro detalhado
docker compose logs flask
docker compose logs postgres
```

### Erro 502 Bad Gateway

O Nginx do host não consegue alcançar o Nginx do Docker.

```bash
# Verificar se o container está rodando na porta 8080
docker compose ps
ss -tlnp | grep 8080
```

### Banco de dados não inicializa

```bash
# Remover o volume e recriar (perde dados existentes)
docker compose down -v
docker compose up -d
```

### Certificado SSL não renova automaticamente

```bash
sudo systemctl status certbot.timer
sudo certbot renew --dry-run
```

### Variáveis de ambiente não carregam

```bash
# Verificar se .env existe e tem as variáveis corretas
cat .env | grep -v "^#" | grep -v "^$"

# Recarregar após editar o .env
docker compose up -d
```

### Webhook do Stripe retorna 400

Certifique-se de que `STRIPE_WEBHOOK_SECRET` começa com `whsec_` e não com `sk_` ou `pk_`.

---

## Estrutura do projeto

```
hostweb-planos-2026-docker/
├── frontend/               # Site estático (servido pelo Nginx)
│   ├── index.html
│   ├── termos.html
│   ├── sucesso.html
│   └── assets/
│       ├── css/styles.css
│       ├── js/scripts.js
│       └── img/
├── backend/                # API Flask
│   ├── app.py
│   ├── utils.py
│   ├── requirements.txt
│   ├── Dockerfile
│   ├── init.sql            # Schema inicial do PostgreSQL
│   ├── blueprints/
│   │   └── aceite.py
│   ├── static/             # CSS/JS do formulário de aceite
│   └── templates/
│       └── aceite.html
├── nginx/
│   └── nginx.conf          # Roteamento Nginx → Flask
├── docker-compose.yml
├── .env                    # NÃO versionar (ignorado pelo .gitignore)
└── .env.example            # Template das variáveis
```

---

*Hostweb Data Center e Serviços LTDA EPP — CNPJ 07.797.967/0001-60 — Fortaleza, CE*
