# Auditoria de Segurança — Hostweb Planos 2026 (Docker)
**OWASP Top 10 · Pré-produção · Sistema de Transações Financeiras**
Data: 2026-05-03 · Versão: 1.0

---

## Sumário Executivo

**Criticidade Geral: ALTA**

Sistema envolve coleta de dados pessoais sensíveis (CPF/CNPJ), aceite jurídico com validade legal (LGPD, Marco Civil) e transações financeiras via Stripe. Foram identificadas **13 vulnerabilidades**, incluindo **3 críticas** que devem ser corrigidas **antes de qualquer exposição à internet** ou uso com dados reais.

| Criticidade | Total | Corrigido | Pendente |
|:---|:---:|:---:|:---:|
| 🔴 Crítica | 3 | 0 | 3 |
| 🟠 Alta | 4 | 0 | 4 |
| 🟡 Média | 4 | 0 | 4 |
| 🔵 Baixa | 2 | 0 | 2 |

> **Ação imediata obrigatória:** V-001 (credenciais no Git) e V-002 (webhook mal configurado) devem ser resolvidos antes de qualquer teste com chaves live do Stripe.

---

## Tabela de Vulnerabilidades

| ID | OWASP | Arquivo | Tipo | Criticidade | Status |
|:---|:------|:--------|:-----|:------------|:-------|
| V-001 | A02:2021 | `.env` | Credenciais reais rastreadas pelo Git | 🔴 Crítica | 🔲 Pendente |
| V-002 | A08:2021 | `.env` | Webhook secret inválido — verificação Stripe falha | 🔴 Crítica | 🔲 Pendente |
| V-003 | A01:2021 | `blueprints/aceite.py` | `/aceite/gerar` sem autenticação — aceites fraudulentos | 🔴 Crítica | 🔲 Pendente |
| V-004 | A01:2021 | `blueprints/aceite.py` | `/aceite/verificar` expõe PII completo sem autenticação | 🟠 Alta | 🔲 Pendente |
| V-005 | A02:2021 | `docker-compose.yml` | HTTP sem TLS — dados financeiros e PII em texto claro | 🟠 Alta | 🔲 Pendente |
| V-006 | A04:2021 | `blueprints/aceite.py` | Sem rate limiting — spam, exaustão de API Stripe | 🟠 Alta | 🔲 Pendente |
| V-007 | A05:2021 | `app.py` | CORS irrestrito em API financeira | 🟠 Alta | 🔲 Pendente |
| V-008 | A04:2021 | `blueprints/aceite.py` | IP forjável via X-Forwarded-For — comprometimento de prova jurídica | 🟡 Média | 🔲 Pendente |
| V-009 | A03:2021 | `blueprints/aceite.py` | CPF/CNPJ e e-mail sem validação server-side | 🟡 Média | 🔲 Pendente |
| V-010 | A05:2021 | `nginx/nginx.conf` | Headers de segurança HTTP ausentes | 🟡 Média | 🔲 Pendente |
| V-011 | A01:2021 | `app.py` | `/get-session` expõe dados Stripe sem autenticação | 🟡 Média | 🔲 Pendente |
| V-012 | A09:2021 | múltiplos | Logging via `print()` — sem auditoria estruturada | 🔵 Baixa | 🔲 Pendente |
| V-013 | A04:2021 | `utils.py` | Sem pool de conexões — risco de connection leak | 🔵 Baixa | 🔲 Pendente |

---

## V-001 — Credenciais Reais Rastreadas pelo Git 🔲 PENDENTE

**Localização:** `.env` na raiz do projeto

**OWASP:** A02:2021 — Falhas Criptográficas

**Problema:** O arquivo `.env` contém a senha do PostgreSQL, a chave secreta do Stripe (`sk_test_...`) e o webhook secret. Verificado que **o arquivo está ativamente rastreado pelo Git** (`git ls-files .env` retorna `.env`). Não existe `.gitignore` no projeto. Qualquer `git push` expõe essas credenciais publicamente ou para todos os colaboradores com acesso ao repositório.

**Impacto:** Acesso total ao banco de dados de aceites (CPF/CNPJ, e-mails, IPs), capacidade de criar cobranças via API Stripe, violação da LGPD por exposição de dados pessoais.

**Ação imediata (executar no terminal):**
```bash
# 1. Criar .gitignore
echo ".env" > .gitignore
echo "__pycache__/" >> .gitignore
echo "*.pyc" >> .gitignore
echo ".env.local" >> .gitignore

# 2. Remover .env do rastreamento Git (mantém o arquivo localmente)
git rm --cached .env

# 3. Commitar a remoção
git add .gitignore
git commit -m "chore: remover .env do rastreamento Git — credenciais sensíveis"
```

**Verificação:**
```bash
git check-ignore -v .env   # deve retornar ".gitignore:1:.env  .env"
git status                 # .env não deve aparecer como tracked
```

**Se o .env já foi commitado anteriormente, as credenciais estão no histórico Git.** Nesse caso, além dos passos acima, é obrigatório rotacionar todas as credenciais:
- Gerar nova senha PostgreSQL
- Revogar e gerar novo `sk_test_...` no painel Stripe
- Gerar novo Webhook Secret no painel Stripe

**Boas práticas no docker-compose.yml:**
```yaml
# Forçar erro se variável não definida — falha explícita em vez de silenciosa
environment:
  POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:?Erro: POSTGRES_PASSWORD nao definido}
```

---

## V-002 — Webhook Secret Inválido — Verificação Stripe Comprometida 🔲 PENDENTE

**Localização:** `.env` — variável `STRIPE_WEBHOOK_SECRET`

**OWASP:** A08:2021 — Falhas de Integridade de Software e Dados

**Problema:** O valor configurado em `STRIPE_WEBHOOK_SECRET` é uma chave pública do Stripe (`pk_test_...`), não um webhook signing secret. Os secrets de webhook do Stripe obrigatoriamente iniciam com `whsec_`. A linha no código que usa essa variável:

```python
# app.py:135
event = stripe.Webhook.construct_event(payload, sig_header, WEBHOOK_SECRET)
```

Com um valor `pk_test_...` nesse campo, `construct_event()` **lançará `SignatureVerificationError` em todo webhook legítimo do Stripe**, ignorando silenciosamente eventos de pagamento confirmado (`checkout.session.completed`). Isso significa que:
- E-mails de boas-vindas nunca serão enviados após pagamento real
- Renovações e cancelamentos não serão processados
- O endpoint retornará 400 para todos os eventos legítimos do Stripe

**Correção:**
```bash
# 1. No painel Stripe → Developers → Webhooks → seu endpoint
# 2. Copiar o "Signing secret" (começa com whsec_...)
# 3. Atualizar no .env:
STRIPE_WEBHOOK_SECRET=whsec_SEU_VALOR_AQUI

# 4. Reiniciar o container Flask
docker compose restart flask
```

**Verificação:**
```bash
# Testar webhook com Stripe CLI
stripe listen --forward-to localhost/webhook
stripe trigger checkout.session.completed
# Deve retornar {"status":"ok"} 200, não {"error":"Invalid signature"} 400
```

---

## V-003 — `/aceite/gerar` sem Autenticação — Geração de Aceites Fraudulentos 🔲 PENDENTE

**Localização:** `backend/blueprints/aceite.py` — rota `POST /aceite/gerar`

**OWASP:** A01:2021 — Quebra de Controle de Acesso

**Problema:** O endpoint `/aceite/gerar` é descrito no código como "uso interno/admin", mas não possui nenhuma proteção de acesso. Qualquer pessoa com conhecimento da URL pode:

1. Criar registros de aceite fraudulentos no banco com dados de terceiros
2. Gerar PDFs oficiais com logotipo e linguagem jurídica da Hostweb para qualquer nome, CPF e plano
3. Forjar evidências de aceite com dados falsos

```python
# ❌ VULNERÁVEL — blueprints/aceite.py:459
@aceite_bp.route("/gerar", methods=["POST"])
def gerar_aceite():
    """Gera e retorna PDF de aceite para download (uso interno/admin)."""
    data     = request.get_json(force=True)
    nome     = (data.get("nome", "") or "").strip()
    # ... sem qualquer verificação de autenticação
    _salvar_aceite(...)   # salva no banco
    return send_file(pdf_buf, ...)  # retorna PDF
```

**Impacto:** Além da fraude documental, inunda o banco com registros falsos que comprometem a integridade do audit trail jurídico — pilar central da validade do aceite digital sob LGPD e Marco Civil.

**Correção — Opção A (token estático, simples):**
```python
# utils.py — adicionar
ADMIN_TOKEN = os.getenv("ADMIN_TOKEN", "")

# blueprints/aceite.py — adicionar decorator
from functools import wraps
from flask import request, jsonify
from utils import ADMIN_TOKEN

def require_admin_token(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get("X-Admin-Token", "")
        if not ADMIN_TOKEN or token != ADMIN_TOKEN:
            return jsonify({"erro": "Não autorizado."}), 401
        return f(*args, **kwargs)
    return decorated

@aceite_bp.route("/gerar", methods=["POST"])
@require_admin_token
def gerar_aceite():
    ...
```

```bash
# .env
ADMIN_TOKEN=gere_com_python3_-c_"import_secrets;print(secrets.token_hex(32))"
```

**Correção — Opção B (remover o endpoint):** Se o PDF é gerado automaticamente no fluxo `/aceite/confirmar`, este endpoint separado pode ser eliminado completamente.

---

## V-004 — `/aceite/verificar` Expõe PII Completo sem Autenticação 🔲 PENDENTE

**Localização:** `backend/blueprints/aceite.py` — rota `GET /aceite/verificar`

**OWASP:** A01:2021 — Quebra de Controle de Acesso

**Problema:** O endpoint retorna todas as colunas da tabela `aceites` para qualquer protocolo informado, sem autenticação:

```python
# ❌ VULNERÁVEL — blueprints/aceite.py:501
cur.execute("SELECT * FROM aceites WHERE protocolo = %s", (protocolo,))
row = cur.fetchone()
...
return jsonify({"valido": True, **data})
# Retorna: nome, email, cpf_cnpj, ip, user_agent, timestamp_utc, empresa, plano...
```

O formato do protocolo `HW-XXXXXXXXXX` (10 caracteres hex = ~1 trilhão de combinações) é tecnicamente difícil de enumerar, mas a exposição de CPF/CNPJ, IP e e-mail completos viola o **princípio da minimização de dados** da LGPD (art. 6º, III).

**Correção:**
```python
# ✅ CORRETO — retornar apenas dados necessários para verificação pública
return jsonify({
    "valido":        True,
    "protocolo":     data["protocolo"],
    "plano":         data["plano"],
    "versao_termos": data["versao_termos"],
    "hash_sha256":   data["hash_sha256"],
    "timestamp_utc": data["timestamp_utc"],
    # Mascarar dados sensíveis para verificação pública
    "nome":          data["nome"].split()[0] + " ***",
    "email":         data["email"][:3] + "***@" + data["email"].split("@")[1],
})
```

Para acesso completo (uso interno), aplicar o mesmo `@require_admin_token` do V-003.

---

## V-005 — HTTP sem TLS 🔲 PENDENTE

**Localização:** `docker-compose.yml`

**OWASP:** A02:2021 — Falhas Criptográficas

**Problema:**
```yaml
# ❌ nginx expõe apenas porta 80 — HTTP puro
ports:
  - "80:80"
```

CPF/CNPJ, e-mail, dados do cartão (via Stripe.js — mitigado pelo Stripe, mas metadados expostos), protocolo de aceite e IP do cliente trafegam sem criptografia. Viola LGPD art. 46 (medidas de segurança) e ISO 27001/27002.

**Correção (produção com Let's Encrypt):**
```yaml
# docker-compose.yml
nginx:
  ports:
    - "80:80"
    - "443:443"
  volumes:
    - ./nginx/nginx.conf:/etc/nginx/conf.d/default.conf:ro
    - ./frontend:/usr/share/nginx/html:ro
    - /etc/letsencrypt:/etc/letsencrypt:ro
    - /var/www/certbot:/var/www/certbot:ro
```

```nginx
# nginx/nginx.conf — adicionar bloco HTTPS e redirect
server {
    listen 80;
    server_name seudominio.com.br;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl;
    server_name seudominio.com.br;

    ssl_certificate     /etc/letsencrypt/live/seudominio.com.br/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/seudominio.com.br/privkey.pem;
    ssl_protocols       TLSv1.2 TLSv1.3;
    ssl_ciphers         HIGH:!aNULL:!MD5;

    # ... resto da configuração existente
}
```

---

## V-006 — Sem Rate Limiting 🔲 PENDENTE

**Localização:** `backend/blueprints/aceite.py` — rota `POST /aceite/confirmar`

**OWASP:** A04:2021 — Design Inseguro

**Problema:** Nenhum endpoint possui proteção contra chamadas em massa. Em `/aceite/confirmar`, cada chamada:
1. Salva um registro no PostgreSQL
2. Faz uma chamada à API do Stripe (cria sessão de checkout)
3. Envia um e-mail via SMTP

Um script simples pode esgotar o limite da API Stripe, gerar custos de e-mail e encher o banco com dados falsos em segundos.

**Correção — usando Flask-Limiter:**
```bash
# requirements.txt — adicionar
Flask-Limiter==3.7.0
```

```python
# app.py
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://"  # em produção: Redis
)
```

```python
# blueprints/aceite.py
from app import limiter

@aceite_bp.route("/confirmar", methods=["POST"])
@limiter.limit("10 per minute; 30 per hour")
def confirmar_aceite():
    ...

@aceite_bp.route("/gerar", methods=["POST"])
@limiter.limit("20 per minute")
def gerar_aceite():
    ...
```

---

## V-007 — CORS Irrestrito 🔲 PENDENTE

**Localização:** `backend/app.py` — linha 13

**OWASP:** A05:2021 — Configuração de Segurança Incorreta

**Problema:**
```python
# ❌ VULNERÁVEL — permite qualquer origem
CORS(app)
```

`CORS(app)` sem restrições permite que qualquer site da web faça requisições autenticadas para a API. Em um contexto de aplicação financeira, isso viabiliza ataques CSRF e permite que sites maliciosos façam chamadas à API em nome de usuários autenticados.

**Correção:**
```python
# ✅ CORRETO — restringir às origens conhecidas
ALLOWED_ORIGINS = os.getenv(
    "ALLOWED_ORIGINS",
    "http://localhost,http://localhost:80"
).split(",")

CORS(app, origins=ALLOWED_ORIGINS, methods=["GET", "POST"], supports_credentials=False)
```

```bash
# .env — em produção
ALLOWED_ORIGINS=https://seudominio.com.br,https://www.seudominio.com.br
```

---

## V-008 — IP Forjável via X-Forwarded-For 🔲 PENDENTE

**Localização:** `backend/blueprints/aceite.py` — função `_capturar_metadados()`

**OWASP:** A04:2021 — Design Inseguro

**Problema:**
```python
# ❌ — header controlável pelo cliente
ip_raw = request.headers.get("X-Forwarded-For", request.remote_addr or "")
return { "ip": ip_raw.split(",")[0].strip(), ... }
```

O header `X-Forwarded-For` pode ser injetado pelo cliente com qualquer valor (`X-Forwarded-For: 1.2.3.4`). Para um aceite digital com validade jurídica, o IP é um elemento de prova. Um usuário pode forjar um IP diferente do real, comprometendo a evidência.

O nginx do projeto configura corretamente `X-Real-IP` e `X-Forwarded-For`. O problema é que Flask também aceita o header se enviado diretamente.

**Correção:**
```python
# blueprints/aceite.py — capturar IP apenas do proxy confiável
def _capturar_metadados():
    # X-Real-IP setado pelo nginx — mais confiável que X-Forwarded-For
    ip = (
        request.headers.get("X-Real-IP")
        or request.remote_addr
        or "desconhecido"
    )
    # Validar formato básico (IPv4/IPv6)
    import re
    if not re.match(r'^[\d\.:a-fA-F]+$', ip):
        ip = "invalido"
    ...
```

Complementar com configuração do Gunicorn para confiar apenas no proxy nginx:
```python
# Dockerfile CMD ou gunicorn.conf.py
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "--workers", "2",
     "--timeout", "60", "--forwarded-allow-ips", "nginx",
     "app:app"]
```

---

## V-009 — CPF/CNPJ e E-mail sem Validação Server-Side 🔲 PENDENTE

**Localização:** `backend/blueprints/aceite.py` — rota `POST /aceite/confirmar`

**OWASP:** A03:2021 — Injeção / Validação de Entrada

**Problema:** O aceite jurídico armazena CPF/CNPJ como texto livre sem qualquer validação de formato ou dígito verificador. O e-mail só é verificado no lado do cliente. Dados inválidos comprometem a validade jurídica do aceite e podem gerar disputas com clientes que aleguem não ter assinado.

```python
# ❌ — apenas presença verificada, não formato
cpf_cnpj = (data.get("cpf_cnpj", "") or "").strip()
if not all([nome, email, cpf_cnpj, plan_id, aceito, lgpd]):
    return jsonify({"erro": "..."}), 400
```

**Correção:**
```python
import re

def validar_cpf(cpf: str) -> bool:
    cpf = re.sub(r'\D', '', cpf)
    if len(cpf) != 11 or cpf == cpf[0] * 11:
        return False
    for i in range(9, 11):
        soma = sum(int(cpf[j]) * (i + 1 - j) for j in range(i))
        if int(cpf[i]) != (soma * 10 % 11) % 10:
            return False
    return True

def validar_cnpj(cnpj: str) -> bool:
    cnpj = re.sub(r'\D', '', cnpj)
    if len(cnpj) != 14:
        return False
    pesos1 = [5,4,3,2,9,8,7,6,5,4,3,2]
    pesos2 = [6,5,4,3,2,9,8,7,6,5,4,3,2]
    def calc(cn, pesos):
        s = sum(int(cn[i]) * pesos[i] for i in range(len(pesos)))
        r = s % 11
        return 0 if r < 2 else 11 - r
    return int(cnpj[12]) == calc(cnpj, pesos1) and int(cnpj[13]) == calc(cnpj, pesos2)

def validar_email(email: str) -> bool:
    return bool(re.match(r'^[^@\s]+@[^@\s]+\.[^@\s]+$', email))

# No confirmar_aceite():
doc = re.sub(r'\D', '', cpf_cnpj)
if len(doc) == 11:
    if not validar_cpf(cpf_cnpj):
        return jsonify({"erro": "CPF inválido."}), 400
elif len(doc) == 14:
    if not validar_cnpj(cpf_cnpj):
        return jsonify({"erro": "CNPJ inválido."}), 400
else:
    return jsonify({"erro": "CPF (11 dígitos) ou CNPJ (14 dígitos) inválido."}), 400

if not validar_email(email):
    return jsonify({"erro": "E-mail inválido."}), 400
```

---

## V-010 — Headers de Segurança HTTP Ausentes no nginx 🔲 PENDENTE

**Localização:** `nginx/nginx.conf`

**OWASP:** A05:2021 — Configuração de Segurança Incorreta

**Problema:** Nenhum header de segurança HTTP está configurado no nginx. Sem esses headers, o browser não recebe instruções de segurança, expondo a aplicação a clickjacking, MIME sniffing e injeção de conteúdo.

**Correção:**
```nginx
# nginx/nginx.conf — adicionar dentro do bloco server {}
add_header X-Frame-Options           "DENY"                              always;
add_header X-Content-Type-Options    "nosniff"                           always;
add_header X-XSS-Protection          "1; mode=block"                     always;
add_header Referrer-Policy           "strict-origin-when-cross-origin"   always;
add_header Permissions-Policy        "camera=(), microphone=(), geolocation=()" always;

# Adicionar após configurar HTTPS (V-005):
add_header Strict-Transport-Security "max-age=31536000; includeSubDomains; preload" always;

# CSP — ajustar conforme fontes CDN usadas
add_header Content-Security-Policy
  "default-src 'self';
   script-src 'self' https://cdnjs.cloudflare.com;
   style-src 'self' 'unsafe-inline' https://cdnjs.cloudflare.com;
   img-src 'self' data: https://hostweb.com.br;
   font-src 'self' https://cdnjs.cloudflare.com;
   connect-src 'self';
   frame-ancestors 'none';"   always;
```

---

## V-011 — `/get-session` Expõe Dados Stripe sem Autenticação 🔲 PENDENTE

**Localização:** `backend/app.py` — rota `GET /get-session`

**OWASP:** A01:2021 — Quebra de Controle de Acesso

**Problema:** O endpoint retorna e-mail do cliente, valor total, nome do plano e metadados da sessão Stripe (incluindo protocolo de aceite) para qualquer `session_id` válido:

```python
# app.py:116 — sem autenticação
@app.route("/get-session", methods=["GET"])
def get_session():
    session_id = request.args.get("session_id", "").strip()
    s = stripe.checkout.Session.retrieve(session_id)
    return jsonify({
        "customer_email": ...,
        "amount_total": ...,
        "plan_name": ...,
        "metadata": meta,  # inclui protocolo_aceite
    })
```

Session IDs do Stripe aparecem na URL (`sucesso.html?session_id=cs_...`) e podem ser expostos via histórico do browser, logs de servidor ou referrer headers.

**Correção — restringir resposta ao mínimo necessário:**
```python
@app.route("/get-session", methods=["GET"])
def get_session():
    session_id = request.args.get("session_id", "").strip()
    if not session_id or not session_id.startswith("cs_"):
        return jsonify({"error": "session_id inválido"}), 400
    try:
        s    = stripe.checkout.Session.retrieve(session_id)
        meta = dict(s.get("metadata") or {})
        return jsonify({
            "plan_name":      meta.get("plan_name", ""),
            "protocolo":      meta.get("protocolo_aceite", ""),
            # Não retornar email completo — mascarar
            "email_hint":     (s.get("customer_email") or "")[:3] + "***",
            "amount_total":   s.get("amount_total"),
        })
    except stripe.error.StripeError as e:
        return jsonify({"error": str(e.user_message)}), 400
```

---

## V-012 — Logging via `print()` sem Estrutura Auditável 🔲 PENDENTE

**Localização:** `backend/app.py`, `backend/blueprints/aceite.py`

**OWASP:** A09:2021 — Falhas de Registro e Monitoramento

**Problema:** Todas as operações sensíveis usam `print()`:

```python
print(f"Pagamento confirmado | Plano: {plano} | E-mail: {email}")
print(f"E-mail confirmação enviado → {email_cliente} | {protocolo}")
print(f"Falha e-mail confirmação: {e}")
```

Saída de `print()` vai para stdout do container. Sem timestamp estruturado, nível de severidade, correlação de request, nem persistência além do `docker logs`. Para um sistema com obrigação LGPD de registrar tratamento de dados pessoais, isso é insuficiente.

**Correção:**
```python
# app.py — substituir prints por logging estruturado
import logging, json
from datetime import datetime, timezone

logging.basicConfig(
    level=logging.INFO,
    format='{"time":"%(asctime)s","level":"%(levelname)s","msg":%(message)s}',
    datefmt='%Y-%m-%dT%H:%M:%SZ'
)
logger = logging.getLogger("hostweb")

# Uso:
logger.info(json.dumps({
    "event":     "pagamento_confirmado",
    "plano":     plano,
    "protocolo": protocolo,
    "email":     email[:3] + "***",  # mascarar PII em logs
}))
logger.error(json.dumps({"event": "email_falha", "erro": str(e)}))
```

---

## V-013 — Sem Pool de Conexões ao Banco 🔲 PENDENTE

**Localização:** `backend/utils.py` — função `get_db()`

**OWASP:** A04:2021 — Design Inseguro

**Problema:**
```python
# utils.py:26 — nova conexão a cada chamada
def get_db():
    return psycopg2.connect(os.getenv("DATABASE_URL"))
```

Com 2 workers Gunicorn e picos de acesso, cada requisição abre e fecha uma conexão TCP com o PostgreSQL. Sem pool, sob carga há risco de esgotar conexões disponíveis no PostgreSQL (`max_connections = 100` no padrão) e de latência de handshake TCP em cada request.

**Correção:**
```python
# utils.py — usar psycopg2.pool
from psycopg2 import pool as pg_pool

_pool = None

def get_pool():
    global _pool
    if _pool is None:
        _pool = pg_pool.ThreadedConnectionPool(
            minconn=1,
            maxconn=10,
            dsn=os.getenv("DATABASE_URL")
        )
    return _pool

def get_db():
    return get_pool().getconn()

def release_db(conn):
    get_pool().putconn(conn)
```

```python
# blueprints/aceite.py — usar release em vez de close
conn = get_db()
try:
    with conn:
        with conn.cursor() as cur:
            cur.execute(...)
finally:
    release_db(conn)  # devolve ao pool em vez de fechar
```

---

## Proteções Adicionais Recomendadas

### CSRF em Formulários

O formulário de aceite envia dados via `fetch()` com `Content-Type: application/json`. Browsers não fazem requisições cross-origin com JSON sem CORS permitir, o que mitiga parcialmente CSRF. Após corrigir V-007 (CORS restrito), o risco de CSRF fica baixo. Para garantia total em produção:

```python
# Flask-WTF com CSRF token
from flask_wtf.csrf import CSRFProtect
csrf = CSRFProtect(app)
```

### Variáveis de Ambiente Obrigatórias

```python
# app.py — validar na inicialização, não em runtime
REQUIRED_ENV = ["STRIPE_SECRET_KEY", "STRIPE_WEBHOOK_SECRET", "DATABASE_URL"]
missing = [k for k in REQUIRED_ENV if not os.getenv(k)]
if missing:
    raise RuntimeError(f"Variáveis de ambiente faltando: {missing}")
```

### Timeout de Sessão Stripe

Sessões Stripe expiram em 24h por padrão. Definir explicitamente para 30 minutos reduz a janela de phishing com links copiados:

```python
session = stripe.checkout.Session.create(
    ...
    expires_at=int((datetime.now(timezone.utc).timestamp()) + 1800),  # 30 min
)
```

---

## Checklist Pré-Produção

### 🔴 Obrigatório (bloqueante para go-live)
- [ ] **V-001**: `.env` removido do Git + credenciais rotacionadas
- [ ] **V-002**: `STRIPE_WEBHOOK_SECRET` corrigido para `whsec_...` + teste com Stripe CLI
- [ ] **V-003**: `/aceite/gerar` protegido com token de admin ou removido
- [ ] **V-005**: HTTPS configurado via nginx + Let's Encrypt

### 🟠 Alta prioridade (antes do primeiro usuário real)
- [ ] **V-004**: `/aceite/verificar` com retorno mascarado de PII
- [ ] **V-006**: Rate limiting via Flask-Limiter em `/aceite/confirmar`
- [ ] **V-007**: CORS restrito às origens do domínio de produção
- [ ] **V-010**: Headers de segurança HTTP adicionados ao nginx
- [ ] **V-011**: `/get-session` com retorno minimizado

### 🟡 Médio prazo (primeiro sprint pós-lançamento)
- [ ] **V-008**: IP capturado de `X-Real-IP` com validação de formato
- [ ] **V-009**: Validação de CPF/CNPJ e e-mail server-side
- [ ] **V-012**: Substituir `print()` por `logging` estruturado
- [ ] **V-013**: Pool de conexões psycopg2

### Extras recomendados
- [ ] CSRF token para formulários HTML
- [ ] Validação de variáveis de ambiente obrigatórias na inicialização
- [ ] Timeout explícito de 30min nas sessões Stripe
- [ ] Teste com OWASP ZAP antes do go-live
- [ ] Rotação periódica do `ADMIN_TOKEN` e `STRIPE_WEBHOOK_SECRET`

---

## Histórico de Versões

| Versão | Data | Alteração |
|:-------|:-----|:----------|
| 1.0 | 2026-05-03 | Auditoria inicial — 13 vulnerabilidades identificadas |

---

*Sistema processa dados pessoais sensíveis (CPF/CNPJ) e transações financeiras. Recomenda-se teste de penetração com OWASP ZAP e revisão jurídica da trilha de auditoria antes do go-live com chaves Stripe live.*
