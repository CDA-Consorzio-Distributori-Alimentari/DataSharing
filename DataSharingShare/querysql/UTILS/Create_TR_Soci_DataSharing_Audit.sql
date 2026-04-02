SET NOCOUNT ON;

/*
    Audit track dedicato a dbo.TR_Soci_DataSharing.

    Lo script:
    - elimina i trigger di audit esistenti se presenti
    - elimina e ricrea la tabella dbo.TR_Soci_DataSharing_AU
    - crea i trigger per INSERT, UPDATE e DELETE

    Nota:
    - la tabella dbo.TR_Soci_DataSharing deve esistere gia
    - SESSION_CONTEXT(N'NOM_USER') traccia l'utente applicativo quando disponibile
    - in fallback vengono usati SYSTEM_USER, HOST_NAME() e APP_NAME()
*/

IF OBJECT_ID(N'[dbo].[TRI_TR_Soci_DataSharing_AU_INS]', N'TR') IS NOT NULL
BEGIN
    DROP TRIGGER [dbo].[TRI_TR_Soci_DataSharing_AU_INS];
END;

IF OBJECT_ID(N'[dbo].[TRU_TR_Soci_DataSharing_AU_UPD]', N'TR') IS NOT NULL
BEGIN
    DROP TRIGGER [dbo].[TRU_TR_Soci_DataSharing_AU_UPD];
END;

IF OBJECT_ID(N'[dbo].[TRD_TR_Soci_DataSharing_AU_DEL]', N'TR') IS NOT NULL
BEGIN
    DROP TRIGGER [dbo].[TRD_TR_Soci_DataSharing_AU_DEL];
END;

IF OBJECT_ID(N'[dbo].[TR_Soci_DataSharing_AU]', N'U') IS NOT NULL
BEGIN
    DROP TABLE [dbo].[TR_Soci_DataSharing_AU];
END;

CREATE TABLE [dbo].[TR_Soci_DataSharing_AU]
(
    [ID_AUDIT]                              INT IDENTITY(1,1) NOT NULL,
    [DES_OPERAZIONE]                        VARCHAR(10)       NOT NULL,
    [TMS_OPERAZIONE]                        DATETIME2(0)      NOT NULL CONSTRAINT [DF_TR_Soci_DataSharing_AU_TMS_OPERAZIONE] DEFAULT SYSDATETIME(),

    [TC_Soci_Codice_OLD]                    VARCHAR(20)       NULL,
    [TC_Soci_Ragione_Sociale_OLD]           VARCHAR(255)      NULL,
    [DataSharing_Code_OLD]                  VARCHAR(20)       NULL,
    [DataSharing_Nome_OLD]                  VARCHAR(100)      NULL,
    [WholesalerID_OLD]                      VARCHAR(50)       NULL,
    [Flag_Attivo_OLD]                       BIT               NULL,
    [Flag_Usa_Nuovo_Strumento_OLD]          BIT               NULL,
    [DataAggiornamento_OLD]                 DATETIME2(0)      NULL,

    [TC_Soci_Codice_NEW]                    VARCHAR(20)       NULL,
    [TC_Soci_Ragione_Sociale_NEW]           VARCHAR(255)      NULL,
    [DataSharing_Code_NEW]                  VARCHAR(20)       NULL,
    [DataSharing_Nome_NEW]                  VARCHAR(100)      NULL,
    [WholesalerID_NEW]                      VARCHAR(50)       NULL,
    [Flag_Attivo_NEW]                       BIT               NULL,
    [Flag_Usa_Nuovo_Strumento_NEW]          BIT               NULL,
    [DataAggiornamento_NEW]                 DATETIME2(0)      NULL,

    [NOM_USER]                              VARCHAR(255)      NOT NULL,
    [NOM_HOST]                              VARCHAR(255)      NOT NULL,
    [DES_SESSION]                           VARCHAR(255)      NOT NULL,
    [TMS_INSERIMENTO]                       DATETIME2(0)      NOT NULL CONSTRAINT [DF_TR_Soci_DataSharing_AU_TMS_INSERIMENTO] DEFAULT SYSDATETIME(),

    CONSTRAINT [PK_TR_Soci_DataSharing_AU]
        PRIMARY KEY CLUSTERED ([ID_AUDIT])
);

GO

CREATE TRIGGER [dbo].[TRI_TR_Soci_DataSharing_AU_INS]
ON [dbo].[TR_Soci_DataSharing]
AFTER INSERT
AS
BEGIN
    SET NOCOUNT ON;

    INSERT INTO [dbo].[TR_Soci_DataSharing_AU]
    (
        [DES_OPERAZIONE],
        [TC_Soci_Codice_NEW],
        [TC_Soci_Ragione_Sociale_NEW],
        [DataSharing_Code_NEW],
        [DataSharing_Nome_NEW],
        [WholesalerID_NEW],
        [Flag_Attivo_NEW],
        [Flag_Usa_Nuovo_Strumento_NEW],
        [DataAggiornamento_NEW],
        [NOM_USER],
        [NOM_HOST],
        [DES_SESSION]
    )
    SELECT
        'INSERT',
        i.[TC_Soci_Codice],
        i.[TC_Soci_Ragione_Sociale],
        i.[DataSharing_Code],
        i.[DataSharing_Nome],
        i.[WholesalerID],
        i.[Flag_Attivo],
        i.[Flag_Usa_Nuovo_Strumento],
        i.[DataAggiornamento],
        COALESCE(NULLIF(CONVERT(VARCHAR(128), SESSION_CONTEXT(N'NOM_USER')), ''), SYSTEM_USER),
        HOST_NAME(),
        APP_NAME()
    FROM inserted AS i;
END;

GO

CREATE TRIGGER [dbo].[TRU_TR_Soci_DataSharing_AU_UPD]
ON [dbo].[TR_Soci_DataSharing]
AFTER UPDATE
AS
BEGIN
    SET NOCOUNT ON;

    INSERT INTO [dbo].[TR_Soci_DataSharing_AU]
    (
        [DES_OPERAZIONE],
        [TC_Soci_Codice_OLD],
        [TC_Soci_Ragione_Sociale_OLD],
        [DataSharing_Code_OLD],
        [DataSharing_Nome_OLD],
        [WholesalerID_OLD],
        [Flag_Attivo_OLD],
        [Flag_Usa_Nuovo_Strumento_OLD],
        [DataAggiornamento_OLD],
        [TC_Soci_Codice_NEW],
        [TC_Soci_Ragione_Sociale_NEW],
        [DataSharing_Code_NEW],
        [DataSharing_Nome_NEW],
        [WholesalerID_NEW],
        [Flag_Attivo_NEW],
        [Flag_Usa_Nuovo_Strumento_NEW],
        [DataAggiornamento_NEW],
        [NOM_USER],
        [NOM_HOST],
        [DES_SESSION]
    )
    SELECT
        'UPDATE',
        d.[TC_Soci_Codice],
        d.[TC_Soci_Ragione_Sociale],
        d.[DataSharing_Code],
        d.[DataSharing_Nome],
        d.[WholesalerID],
        d.[Flag_Attivo],
        d.[Flag_Usa_Nuovo_Strumento],
        d.[DataAggiornamento],
        i.[TC_Soci_Codice],
        i.[TC_Soci_Ragione_Sociale],
        i.[DataSharing_Code],
        i.[DataSharing_Nome],
        i.[WholesalerID],
        i.[Flag_Attivo],
        i.[Flag_Usa_Nuovo_Strumento],
        i.[DataAggiornamento],
        COALESCE(NULLIF(CONVERT(VARCHAR(128), SESSION_CONTEXT(N'NOM_USER')), ''), SYSTEM_USER),
        HOST_NAME(),
        APP_NAME()
    FROM inserted AS i
    INNER JOIN deleted AS d
        ON d.[TC_Soci_Codice] = i.[TC_Soci_Codice]
       AND d.[DataSharing_Code] = i.[DataSharing_Code];
END;

GO

CREATE TRIGGER [dbo].[TRD_TR_Soci_DataSharing_AU_DEL]
ON [dbo].[TR_Soci_DataSharing]
AFTER DELETE
AS
BEGIN
    SET NOCOUNT ON;

    INSERT INTO [dbo].[TR_Soci_DataSharing_AU]
    (
        [DES_OPERAZIONE],
        [TC_Soci_Codice_OLD],
        [TC_Soci_Ragione_Sociale_OLD],
        [DataSharing_Code_OLD],
        [DataSharing_Nome_OLD],
        [WholesalerID_OLD],
        [Flag_Attivo_OLD],
        [Flag_Usa_Nuovo_Strumento_OLD],
        [DataAggiornamento_OLD],
        [NOM_USER],
        [NOM_HOST],
        [DES_SESSION]
    )
    SELECT
        'DELETE',
        d.[TC_Soci_Codice],
        d.[TC_Soci_Ragione_Sociale],
        d.[DataSharing_Code],
        d.[DataSharing_Nome],
        d.[WholesalerID],
        d.[Flag_Attivo],
        d.[Flag_Usa_Nuovo_Strumento],
        d.[DataAggiornamento],
        COALESCE(NULLIF(CONVERT(VARCHAR(128), SESSION_CONTEXT(N'NOM_USER')), ''), SYSTEM_USER),
        HOST_NAME(),
        APP_NAME()
    FROM deleted AS d;
END;

GO