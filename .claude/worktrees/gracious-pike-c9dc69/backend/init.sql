CREATE TABLE IF NOT EXISTS aceites (
    id            SERIAL       PRIMARY KEY,
    protocolo     VARCHAR(20)  UNIQUE NOT NULL,
    nome          TEXT         NOT NULL,
    email         TEXT         NOT NULL,
    cpf_cnpj      TEXT         NOT NULL,
    empresa       TEXT,
    plano         TEXT         NOT NULL,
    plan_id       TEXT,
    domain        TEXT,
    ip            VARCHAR(45),
    user_agent    TEXT,
    timestamp_utc TIMESTAMPTZ  NOT NULL,
    timestamp_brt TEXT,
    versao_termos TEXT,
    hash_sha256   CHAR(64),
    criado_em     TIMESTAMPTZ  DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_aceites_protocolo ON aceites (protocolo);
CREATE INDEX IF NOT EXISTS idx_aceites_email     ON aceites (email);

-- Registra cada tentativa de provisionamento cPanel pós-pagamento
CREATE TABLE IF NOT EXISTS provisionamentos (
    id               SERIAL       PRIMARY KEY,
    session_stripe   TEXT         UNIQUE NOT NULL,  -- chave de idempotência
    protocolo_aceite VARCHAR(20),
    nome             TEXT,
    email            TEXT         NOT NULL,
    domain           TEXT,
    plano            TEXT,
    plan_id          TEXT,
    servidor         TEXT,
    cpanel_user      TEXT,
    -- pendente_manual | criando | ativo | erro
    status           TEXT         NOT NULL DEFAULT 'pendente',
    erro_msg         TEXT,
    criado_em        TIMESTAMPTZ  DEFAULT NOW(),
    atualizado_em    TIMESTAMPTZ  DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_prov_email  ON provisionamentos (email);
CREATE INDEX IF NOT EXISTS idx_prov_domain ON provisionamentos (domain);
CREATE INDEX IF NOT EXISTS idx_prov_status ON provisionamentos (status);
