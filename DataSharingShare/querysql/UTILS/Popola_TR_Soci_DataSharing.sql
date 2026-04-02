SET NOCOUNT ON;

/*
    Normalizza i flag di abilitazione presenti in dbo.TC_Soci
    dentro una tabella relazionale dbo.TR_Soci_DataSharing.

    Note:
    - la tabella target viene eliminata e ricreata a ogni esecuzione
    - vengono considerati solo i soci attivi (TC_Soci_Socio_Attivo = 1)
    - viene generata una riga per ogni combinazione socio/data sharing
    - Flag_Attivo indica se il socio e abilitato a quel data sharing
    - Flag_Usa_Nuovo_Strumento indica se il data sharing deve essere gestito da questo applicativo
    - Ferrero non viene incluso perche al momento non e configurato in config.json
*/

IF OBJECT_ID(N'[dbo].[TR_Soci_DataSharing]', N'U') IS NOT NULL
BEGIN
    DROP TABLE [dbo].[TR_Soci_DataSharing];
END;

BEGIN
    CREATE TABLE [dbo].[TR_Soci_DataSharing]
    (
        [TC_Soci_Codice]            VARCHAR(20)  NOT NULL,
        [TC_Soci_Ragione_Sociale]   VARCHAR(255) NULL,
        [DataSharing_Code]          VARCHAR(20)  NOT NULL,
        [DataSharing_Nome]          VARCHAR(100) NOT NULL,
        [WholesalerID]              VARCHAR(50)  NULL,
        [Flag_Attivo]               BIT          NOT NULL,
        [Flag_Usa_Nuovo_Strumento]  BIT          NOT NULL,
        [DataAggiornamento]         DATETIME2(0) NOT NULL,
        CONSTRAINT [PK_TR_Soci_DataSharing]
            PRIMARY KEY CLUSTERED ([TC_Soci_Codice], [DataSharing_Code])
    );
END;

;WITH SourceRows AS
(
    SELECT
        s.[TC_Soci_Codice],
        s.[TC_Soci_Ragione_Sociale],
        ds.[DataSharing_Code],
        ds.[DataSharing_Nome],
        CASE
            WHEN ds.[DataSharing_Code] IN ('CC001', 'CC002')
                THEN NULLIF(LTRIM(RTRIM(s.[TC_Soci_CocaCola_Codice])), '')
            ELSE NULL
        END AS [WholesalerID],
        CAST(ds.[Flag_Attivo] AS BIT) AS [Flag_Attivo],
        CAST(CASE WHEN ds.[DataSharing_Code] IN ('CC001', 'CC002') THEN 1 ELSE 0 END AS BIT) AS [Flag_Usa_Nuovo_Strumento],
        SYSDATETIME() AS [DataAggiornamento]
    FROM [dbo].[TC_Soci] AS s
    CROSS APPLY
    (
        VALUES
            ('CC001', 'Coca Cola V1', ISNULL(s.[TC_Soci_CocaCola_Attivo], 0)),
            ('CC002', 'Coca Cola V2', ISNULL(s.[TC_Soci_CocaCola_In_Chiaro], 0)),
            ('CA001', 'Campari',      ISNULL(s.[TC_Soci_Campari_Attivo], 0)),
            ('DI001', 'DIAGEO',       ISNULL(s.[TC_Soci_DIAGEO_Attivo], 0)),
            ('RB001', 'RedBull',      ISNULL(s.[TC_Soci_RedBull_Attivo], 0)),
            ('MA001', 'Martini',      ISNULL(s.[TC_Soci_Martini_Attivo], 0))
    ) AS ds ([DataSharing_Code], [DataSharing_Nome], [Flag_Attivo])
    WHERE ISNULL(s.[TC_Soci_Socio_Attivo], 0) = 1
)
INSERT INTO [dbo].[TR_Soci_DataSharing]
(
    [TC_Soci_Codice],
    [TC_Soci_Ragione_Sociale],
    [DataSharing_Code],
    [DataSharing_Nome],
    [WholesalerID],
    [Flag_Attivo],
    [Flag_Usa_Nuovo_Strumento],
    [DataAggiornamento]
)
SELECT
    [TC_Soci_Codice],
    [TC_Soci_Ragione_Sociale],
    [DataSharing_Code],
    [DataSharing_Nome],
    [WholesalerID],
    [Flag_Attivo],
    [Flag_Usa_Nuovo_Strumento],
    [DataAggiornamento]
FROM SourceRows;

SELECT
    [TC_Soci_Codice],
    [TC_Soci_Ragione_Sociale],
    [DataSharing_Code],
    [DataSharing_Nome],
    [WholesalerID],
    [Flag_Attivo],
    [Flag_Usa_Nuovo_Strumento],
    [DataAggiornamento]
FROM [dbo].[TR_Soci_DataSharing]
ORDER BY [TC_Soci_Codice], [DataSharing_Code];