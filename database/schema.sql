-- ===========================================================================
-- Alerta Rio - modelo de dados (MySQL 8)
--
-- 4 tabelas:
--   sensores  -> pontos de medição do nível do rio (mantidos pela comunidade)
--   leituras  -> cada medição recebida pelo socket UDP
--   alertas   -> mudanças de risco (normal -> atenção -> perigo e volta)
--   abrigos   -> locais seguros para onde as famílias podem ir
--
-- LGPD: repare que não existe NENHUMA tabela de pessoas. O sistema
-- funciona sem saber quem é o morador; ele só precisa saber do rio.
-- ===========================================================================

CREATE DATABASE IF NOT EXISTS alerta_rio
  CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

USE alerta_rio;

CREATE TABLE IF NOT EXISTS sensores (
    id               INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    codigo           VARCHAR(12)  NOT NULL,
    nome             VARCHAR(80)  NOT NULL,
    bairro           VARCHAR(60)  NOT NULL,
    latitude         DECIMAL(9,6) NOT NULL,
    longitude        DECIMAL(9,6) NOT NULL,
    nivel_alerta_cm  SMALLINT UNSIGNED NOT NULL,
    nivel_critico_cm SMALLINT UNSIGNED NOT NULL,
    ativo            TINYINT(1)   NOT NULL DEFAULT 1,
    criado_em        DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    atualizado_em    DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT uq_sensores_codigo UNIQUE (codigo),
    CONSTRAINT chk_sensores_niveis CHECK (nivel_critico_cm > nivel_alerta_cm)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS leituras (
    id            BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    sensor_id     INT UNSIGNED  NOT NULL,
    nivel_cm      DECIMAL(6,1)  NOT NULL,
    registrado_em DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_leituras_sensor_data (sensor_id, registrado_em),
    CONSTRAINT fk_leituras_sensor FOREIGN KEY (sensor_id)
        REFERENCES sensores(id) ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS alertas (
    id          BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    sensor_id   INT UNSIGNED NOT NULL,
    nivel_risco ENUM('normal', 'atencao', 'perigo') NOT NULL,
    nivel_cm    DECIMAL(6,1) NOT NULL,
    mensagem    VARCHAR(200) NOT NULL,
    criado_em   DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_alertas_sensor (sensor_id, id),
    CONSTRAINT fk_alertas_sensor FOREIGN KEY (sensor_id)
        REFERENCES sensores(id) ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS abrigos (
    id            INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    nome          VARCHAR(80)  NOT NULL,
    endereco      VARCHAR(120) NOT NULL,
    bairro        VARCHAR(60)  NOT NULL,
    latitude      DECIMAL(9,6) NOT NULL,
    longitude     DECIMAL(9,6) NOT NULL,
    capacidade    SMALLINT UNSIGNED NOT NULL,
    ocupacao      SMALLINT UNSIGNED NOT NULL DEFAULT 0,
    aceita_pets   TINYINT(1)   NOT NULL DEFAULT 0,  -- muita gente não sai de casa sem o bicho
    acessivel     TINYINT(1)   NOT NULL DEFAULT 0,  -- rampa, banheiro adaptado
    ativo         TINYINT(1)   NOT NULL DEFAULT 1,
    criado_em     DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    atualizado_em DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT chk_abrigos_ocupacao CHECK (ocupacao <= capacidade)
) ENGINE=InnoDB;
