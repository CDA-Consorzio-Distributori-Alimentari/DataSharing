# XML Config Template

Usa questo formato per ogni nuovo cliente XML basato su:
- query SQL
- template XSLT
- sole eccezioni in `xml_mapping`
- sole regole di grouping in `xml_grouping`

## Regole

1. La query deve esporre direttamente i nomi usati dal template XSLT nei `normalize-space(...)`.
2. `xml_mapping` contiene solo eccezioni:
   - rinomina di un campo non 1:1
   - concatenazione di piu colonne in un campo target
   - attributi root richiesti dal template ma non presenti 1:1 nel DataFrame
3. `xml_grouping` contiene solo le chiavi di grouping per le sezioni che hanno figli.
4. Le chiavi di `xml_grouping` devono preferibilmente usare il path sezione del template, ad esempio `Sales/Transaction`.
5. Se il template richiede un attributo root o un campo che non si ricava da DataFrame o `xml_mapping`, il processo va in errore.
6. Se una sezione con figli non ha la relativa entry in `xml_grouping`, il processo va in errore.

## Template Standard

```json
{
  "code": "CL001",
  "name": "New Customer",
  "Campo": "TC_Soci_NewCustomer_Attivo",
  "file_type": "xml",
  "delivery_method": "ftp",
  "fields": "TC_Soci_NewCustomer_Attivo",
  "query_file": "querysql/New_Customer_query.sql",
  "xslt_template": "templatexml/New_Customer_transformation.xslt",
  "xml_mapping": {
    "WholesalerID": "TC_Soci_NewCustomer_Codice",
    "CustomerCode": {
      "fields": ["Clienti_Codice", "Clienti_Codice_Pdc"],
      "separator": "_"
    },
    "InvoiceDate": "DataDDT"
  },
  "xml_grouping": {
    "Sales/Transaction": ["CustomerCode"],
    "AnotherSection/Entry": ["FieldA", "FieldB"]
  },
  "parameters": {
    "DateFrom": "",
    "DateTo": ""
  },
  "ftp_config": {
    "host": "ftp.example.com",
    "user": "ftp_user",
    "password": "ftp_password",
    "port": 21
  },
  "naming_convention": "NEW_CUSTOMER_YYYYMMDDhhmmss"
}
```

## Cosa Va In Query

La query deve gia esporre, quando possibile, le colonne con i nomi richiesti dal template XSLT.

Esempio:

```sql
SELECT
    TC_Soci_CocaCola_Codice AS WholesalerID,
    TW_Vendite_Data_DDT AS DataDDT,
    TW_Vendite_Numero_DDT AS NumeroDDT,
    TW_Vendite_Volume AS Volume,
    TC_Articoli_Codice_CocaCola AS ArticoliCodiceCocaCola
FROM ...
```

## Cosa Va In xml_mapping

Metti qui solo i casi non 1:1.

Esempi:

```json
{
  "WholesalerID": "TC_Soci_CocaCola_Codice",
  "CodiceCliente": {
    "fields": ["Clienti_Codice", "Clienti_Codice_Pdc"],
    "separator": "_"
  }
}
```

## Cosa Va In xml_grouping

Metti qui solo il grouping delle sezioni con figli.

Esempio:

```json
{
  "Sales/Transaction": ["CodiceCliente"],
  "Orders/Order": ["OrderNumber", "OrderDate"]
}
```
