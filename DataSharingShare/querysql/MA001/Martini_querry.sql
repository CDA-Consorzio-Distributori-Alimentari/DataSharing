
SELECT
    v.TW_Vendite_Numero_DDT AS NumFattura,
    ROW_NUMBER() OVER (ORDER BY TW_Vendite_Numero_DDT) AS RowNum,
    a.TC_Articoli_Codice AS CodiceProdotto,
    a.TC_Articoli_Descrizione AS DescProdotto,
    f.TC_Fornitori_Ragione_Sociale AS Fabbricante,
    '' AS CodiceProdFab,
    '' AS EAN13,
    v.TW_Vendite_Pezzi - v.TW_Vendite_Omaggi AS Quantita,
    'UV' AS UM,
    '0.0' AS NU1,
    '0.0' AS NU2,
    v.TW_Vendite_Valore AS Importo,
    v.TW_Vendite_Data_DDT AS dataDDT,
    SUBSTRING(TW_Vendite_Data_DDT, 1, 4) AS esercizio,
    v.Ti_Clienti_Codice + '-' + v.Ti_Clienti_Codice_pdc AS CodiceCliente,
    '' AS NomeCliente,
    '' AS RagioneSociale,
    '' AS PIva,
    '' AS Indirizzo,
    c.TW_Clienti_Localita AS [Comune (normalizzato)],
    c.tw_clienti_cap AS CAP,
    v.TW_Vendite_Filiale AS Magazzino,
    '' AS DESCMagazzino,
    c.TW_Clienti_Agente AS CodAgente,
    '' AS NomeAgente,
    '0.0' AS NU3,
    '' AS NU4,
    c.TC_Sub_Categoria_Codice AS tipocliente,
    '' AS NU5,
    '(' + mc.TC_Macro_Categoria_Descrizione + ') (' + cc.TC_Categoria_Descrizione + ') (' + sc.TC_sub_Categoria_Descrizione + ')' AS descTipoCliente
FROM TW_Vendite_20 v
inner join TC_Articoli a on a.TC_Articoli_Codice = v.TC_Articoli_Codice
inner join TC_Fornitori f on f.TC_Fornitori_Codice = a.TC_Fornitori_Codice
inner join TW_Clienti c on c.TW_Clienti_Codice = v.TW_Clienti_Codice
inner join TC_Macro_Categoria_Clienti mc on mc.TC_Macro_Categoria_Codice = c.TC_Macro_Categoria_Codice
inner join TC_Sub_Categoria_Clienti sc on sc.TC_Sub_Categoria_Codice = c.TC_Sub_Categoria_Codice    
inner join TC_Categoria_Clienti cc on cc.TC_Categoria_Codice = c.TC_Categoria_Codice
and c.TW_Clienti_Codice_PDC = v.TW_Vendite_Pdc
WHERE v.TW_Vendite_Periodo = @periodoelaborazione 
AND v.TC_Soci_Codice = @socioelaborazione
