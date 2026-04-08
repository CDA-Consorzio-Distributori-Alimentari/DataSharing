SET NOCOUNT ON;

/*
    Tabella di tracking TX_DATASHARING_SOCIO
    Convenzione conforme a MANUALE_REGOLE_DATABASE.md e MANUALE_CONFIGURAZIONE_DATASHARING.md

    - Schema: DBO
    - Nome: TX_DATASHARING_SOCIO
    - Tutti i nomi in maiuscolo, underscore, nessun carattere speciale
    - Campi principali:
        - COD_SOCIO: codice socio (CHAR, NOT NULL)
        - COD_DATASHARING: codice data sharing (CHAR, NOT NULL)
        - PERIODO: periodo di riferimento (CHAR, NOT NULL, es. YYYYMM)
        - NOM_FILE: nome file generato (VARCHAR, NOT NULL)
        - DAT_INVIO: data e ora invio (DATETIME2, NOT NULL)
    - Campi di sistema obbligatori per TX_:
        - FLG_DELETE BIT NOT NULL DEFAULT 0
        - FLG_ACTIVE BIT NOT NULL DEFAULT 1
        - FLG_VISIBLE BIT NOT NULL DEFAULT 1
        - ID_USER_INSERT UNIQUEIDENTIFIER NOT NULL
        - TMS_INSERT DATETIME NOT NULL DEFAULT GETDATE()
        - ID_USER_UPDATE UNIQUEIDENTIFIER NULL
        - TMS_UPDATE DATETIME NULL
        - ID_USER_DELETE UNIQUEIDENTIFIER NULL
        - TMS_DELETE DATETIME NULL
    - PK: COD_SOCIO, COD_DATASHARING, PERIODO, NOM_FILE
    - Nessuna tabella di audit
*/

IF OBJECT_ID(N'DBO.TX_DATASHARING_SOCIO', N'U') IS NOT NULL
BEGIN
    DROP TABLE DBO.TX_DATASHARING_SOCIO;
END;

CREATE TABLE DBO.TX_DATASHARING_SOCIO
(
    COD_SOCIO         CHAR(3)      NOT NULL,
    COD_DATASHARING   CHAR(5)      NOT NULL,
    NUM_PERIODO       INT          NOT NULL,
    TMS_INVIO         DATETIME2(0) NOT NULL DEFAULT (DATEADD(MINUTE, DATEDIFF(MINUTE, 0, GETDATE()), 0)),
    NOM_FILE          VARCHAR(255) NOT NULL,    
    COD_STATO             CHAR(3)      NOT NULL, -- Stato invio:
        /*
            'INS' = Inserimento record in tabella di tracking (pre-invio)
            'RUN' = Tentativo di invio in corso
            'OK ' = Invio completato con successo
            'ERR' = Errore durante l'invio
            'WAR' = Inviato con warning/non bloccante
            'DEG' = Debug/prova: generazione file senza invio
            (aggiungere altri codici se necessario)
        */
    DES_ERRORE            VARCHAR(255) NULL,
    TMS_CREAZIONE         DATETIME2(0) NOT NULL DEFAULT (DATEADD(MINUTE, DATEDIFF(MINUTE, 0, GETDATE()), 0)),
    NOM_UTENTE_OPERAZIONE VARCHAR(50)  NULL,
    NOM_HOST_OPERAZIONE   VARCHAR(50)  NULL,



    CONSTRAINT PK_TX_DATASHARING_SOCIO PRIMARY KEY (COD_SOCIO, COD_DATASHARING, NUM_PERIODO, TMS_INVIO)
);

CREATE INDEX IN_TX_DATASHARING_SOCIO ON DBO.TX_DATASHARING_SOCIO (COD_SOCIO, COD_DATASHARING, NUM_PERIODO, TMS_INVIO);
