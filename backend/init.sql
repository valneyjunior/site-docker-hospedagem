CREATE TABLE IF NOT EXISTS aceites (
    id                  SERIAL       PRIMARY KEY,
    protocolo           VARCHAR(20)  UNIQUE NOT NULL,
    nome                TEXT         NOT NULL,
    email               TEXT         NOT NULL,
    cpf_cnpj            TEXT         NOT NULL,
    empresa             TEXT,
    plano               TEXT         NOT NULL,
    plan_id             TEXT,
    dominio             TEXT,
    telefone            TEXT,
    asaas_customer_id   TEXT,
    ip                  VARCHAR(45),
    user_agent          TEXT,
    timestamp_utc       TIMESTAMPTZ  NOT NULL,
    timestamp_brt       TEXT,
    versao_termos       TEXT,
    hash_sha256         CHAR(64),
    criado_em           TIMESTAMPTZ  DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_aceites_protocolo  ON aceites (protocolo);
CREATE INDEX IF NOT EXISTS idx_aceites_email      ON aceites (email);
CREATE INDEX IF NOT EXISTS idx_aceites_customer   ON aceites (asaas_customer_id);

CREATE TABLE IF NOT EXISTS provisionamentos (
    id                  SERIAL       PRIMARY KEY,
    aceite_id           INTEGER      REFERENCES aceites(id),
    asaas_payment_id    TEXT         UNIQUE,
    asaas_customer_id   TEXT,
    dominio             TEXT,
    plano               TEXT,
    whm_package         TEXT,
    cpanel_username     TEXT,
    status              TEXT         DEFAULT 'pendente',
    erro_msg            TEXT,
    provisionado_em     TIMESTAMPTZ,
    criado_em           TIMESTAMPTZ  DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_prov_payment  ON provisionamentos (asaas_payment_id);
CREATE INDEX IF NOT EXISTS idx_prov_customer ON provisionamentos (asaas_customer_id);
