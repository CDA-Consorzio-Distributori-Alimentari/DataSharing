SELECT
    TC_Soci_Deposito.TC_Soci_CocaCola_Codice As WholesalerID,
    CASE WHEN TW_Vendite_20.TW_Vendite_Filiale='' THEN '00' ELSE TW_Vendite_20.TW_Vendite_Filiale END AS Filiale,
    --TW_Vendite_20.TI_Clienti_Codice AS Clienti_Codice,
    --TW_Vendite_20.TI_Clienti_Codice_Pdc AS Clienti_Codice_Pdc,
    TW_clienti.TW_Clienti_Codice AS Clienti_Codice,    
    TW_clienti.TW_Clienti_Codice_pdc AS Clienti_Codice_Pdc,    
    TW_Clienti.TW_Clienti_Cap AS Cap,
    TW_Clienti.TW_Clienti_Localita AS Localita,
          
    ISNULL(CAST(TC_Articoli_Coca_Cola.codice_coca_cola AS VARCHAR(24)), 'Null-' + LTRIM(RTRIM(CAST(tc_articoli.TC_Articoli_Codice AS VARCHAR(24))))) AS ArticoliCodiceHbc,
    ISNULL(TC_Articoli_Coca_Cola.descrizione, '') AS ArticoliDescrizioneHbc,
    TC_Articoli.TC_Articoli_Codice AS ArticoliCodice,
    TC_Articoli.TC_Articoli_Descrizione AS ArticoliDescrizione,
    CONVERT(DATE, TW_Vendite_20.TW_Vendite_Data_DDT) AS DataDDT,
    TW_Vendite_20.TW_Vendite_Numero_DDT AS NumeroDDT,
    TW_Vendite_20.TW_Vendite_Pezzi AS Quantita,
    TW_Vendite_20.TW_Vendite_Volume AS Volume,
    TW_Clienti.TC_Sub_Categoria_Codice  AS SubCategoriaCodice,
    TC_Sub_Categoria_Clienti.TC_Sub_Categoria_Descrizione AS SubCategoriaDescrizione,
    
    ISNULL(tc_Coca_Cola.tc_coca_cola_numero_flusso, 1) AS NumeroFlusso
    
FROM TW_Vendite_20
INNER JOIN TW_Clienti ON
    TW_Vendite_20.TC_Soci_Polo = TW_Clienti.TC_Soci_Polo AND
    TW_Vendite_20.TC_Soci_Codice = TW_Clienti.TC_Soci_Codice AND
    TW_Vendite_20.TW_Clienti_Codice = TW_Clienti.TW_Clienti_Codice AND
    TW_Vendite_20.TW_vendite_pdc = TW_Clienti.TW_Clienti_Codice_PDC
INNER JOIN TC_Soci_Deposito ON
    TW_Vendite_20.TC_Soci_Polo = TC_Soci_Deposito.TC_Soci_Polo AND
    TW_Vendite_20.TC_Soci_Codice = TC_Soci_Deposito.TC_Soci_Codice AND
    CASE WHEN TW_Vendite_20.TW_Vendite_Filiale='' THEN '00' ELSE TW_Vendite_20.TW_Vendite_Filiale END = TC_Soci_Deposito.TC_Soci_Filiale
INNER JOIN TC_Articoli ON
    TW_Vendite_20.TC_Articoli_Codice = TC_Articoli.TC_Articoli_Codice
INNER JOIN TC_Soci ON
    TC_Soci.TC_Soci_Codice = TW_Clienti.TC_Soci_Codice AND
    TC_Soci.TC_Soci_Polo = TW_Clienti.TC_Soci_Polo
LEFT JOIN TC_Articoli_Coca_Cola ON
    TC_Articoli_Coca_Cola.tc_articoli_codice = TC_Articoli.tc_articoli_codice
INNER JOIN TC_Sub_Categoria_Clienti ON
    TW_Clienti.TC_Sub_Categoria_Codice = TC_Sub_Categoria_Clienti.TC_Sub_Categoria_Codice
LEFT JOIN (
    SELECT 
        tc_soci_codice, 
        tc_coca_cola_periodo, 
        TC_Soci_CocaCola_Codice, 
        MAX(tc_coca_cola_numero_flusso) + 1 AS tc_coca_cola_numero_flusso
    FROM TC_Coca_cola
    GROUP BY 
        tc_soci_codice,
        TC_Soci_CocaCola_Codice, 
        tc_coca_cola_periodo
) tc_coca_cola ON
    TW_Clienti.TC_Soci_Codice = TC_Coca_cola.TC_Soci_Codice AND
    TW_Vendite_20.TW_Vendite_Periodo = tc_coca_cola.tc_coca_cola_periodo AND
    TC_Soci_Deposito.TC_Soci_CocaCola_Codice = TC_Coca_cola.TC_Soci_CocaCola_Codice
WHERE TC_Articoli.TC_Fornitori_Codice = 4802 
      AND TW_Vendite_20.TC_Soci_Codice = @socioelaborazione
      AND TW_Vendite_20.TW_Vendite_Periodo = @periodoelaborazione 
      AND TC_Articoli.TC_Categorie_Merceologiche_Codice < 14
ORDER BY 
    TC_Soci_Deposito.TC_Soci_CocaCola_Codice,
    TW_Clienti.TC_Soci_Polo,
    TW_Clienti.TC_Soci_Codice,
    TW_Clienti.TW_Clienti_Codice,
    TW_Clienti.TW_Clienti_Codice_Pdc,
    TW_Vendite_20.TW_Vendite_Data_DDT,
    TW_Vendite_20.TW_Vendite_Numero_DDT,
    TC_Articoli.TC_Articoli_Codice;