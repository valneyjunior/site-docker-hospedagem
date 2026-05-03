CREATE TABLE IF NOT EXISTS aceites (
    id            SERIAL       PRIMARY KEY,
    protocolo     VARCHAR(20)  UNIQUE NOT NULL,
    nome          TEXT         NOT NULL,
    email         TEXT         NOT NULL,
    cpf_cnpj      TEXT         NOT NULL,
    empresa       TEXT,
    plano         TEXT         NOT NULL,
    plan_id       TEXT,
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
