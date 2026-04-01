# Manuale Configurazione Data Sharing

Questo documento unifica:

- configurazione dei percorsi applicativi
- configurazione dei data sharing XML

## 1. Concetti Base

Il progetto distingue due aree:

- root del progetto: e la cartella del repository e viene rilevata automaticamente dal codice
- root degli artefatti: e la cartella che contiene `LOG`, `OutPut`, `querysql` e `templatexml`

## 2. Configurazione Percorsi

Nel file `config.json` il campo principale e:

```json
"artifacts_root_path": "\\\\cdabackup\\DataSharing"
```

Nella configurazione standard basta modificare questo solo campo: tutte le altre cartelle (`LOG`, `OutPut`, `querysql`, `templatexml`) vengono risolte automaticamente sotto questa root.

Con questa impostazione il progetto usa automaticamente:

- `\\cdabackup\DataSharing\LOG`
- `\\cdabackup\DataSharing\OutPut`
- `\\cdabackup\DataSharing\querysql`
- `\\cdabackup\DataSharing\templatexml`

All'avvio, leggendo `config.json`, il progetto crea automaticamente:

- le cartelle base degli artefatti
- le sottocartelle `querysql/{COD_datasharing}` per ogni voce configurata
- le sottocartelle `templatexml/{COD_datasharing}` per i data sharing di tipo XML

Le cartelle `OutPut/{cod_socio}/{COD_datasharing}` non possono essere precreate da configurazione, perche il codice socio e noto solo al momento dell'elaborazione, quindi vengono create a runtime quando parte l'export.

### Struttura query e template

Le query SQL e i template XSLT vengono organizzati per codice data sharing:

- `querysql/{COD_datasharing}/nome_query.sql`
- `templatexml/{COD_datasharing}/nome_template.xslt`

Esempi:

- `querysql/CC001/Coca_Cola_V1_query.sql`
- `templatexml/CC001/Coca_Cola_V1_transformation.xslt`
- `querysql/CC002/Coca_Cola_V2_query.sql`
- `templatexml/CC002/Coca_Cola_V2_transformation.xslt`

### Struttura output generati

I file prodotti vengono salvati dentro `OutPut` con questa convenzione:

- `OutPut/{cod_socio}/{COD_datasharing}/nomefile`

Esempi:

- `OutPut/2/CC001/CWHS_CodiceSAPCocaCola_2_20260401113000.xml`
- `OutPut/7/DI001/CWHS_CodiceSAPDIAGEO_2_20260401113000.csv`

### Share di rete

Per usare una net share di rete, imposta una UNC completa:

```json
"artifacts_root_path": "\\\\server\\share\\DataSharing"
```

In questo caso il progetto usera automaticamente:

- `\\server\share\DataSharing\LOG`
- `\\server\share\DataSharing\OutPut`
- `\\server\share\DataSharing\querysql`
- `\\server\share\DataSharing\templatexml`

### Compatibilita

- `working_folder` e opzionale e normalmente non serve piu
- `shared_root_path` resta supportato per compatibilita, ma il nome consigliato e `artifacts_root_path`

### Override locale consigliato

Per evitare di modificare il file base condiviso dal team, il progetto supporta anche `config.local.json`.

Regole operative:

- `config.json` resta il file base comune
- `config.local.json` contiene solo le differenze locali o sensibili
- in caso di duplicati, i valori di `config.local.json` sovrascrivono quelli di `config.json`
- per `data_sharing_options` il merge avviene per `code`

Esempi di utilizzo tipici:

- credenziali FTP diverse tra ambienti
- share di rete locale diversa tra PC o server
- attivazione temporanea di `DEBUG` per test controllati
- parametri SMTP o destinatari di recap diversi tra ambienti

## 3. Struttura Configurazione XML

Per ogni nuovo cliente XML la configurazione si basa su:

- query SQL
- template XSLT
- sole eccezioni in `xml_mapping`
- sole regole di grouping in `xml_grouping`

## 4. Regole XML

1. La query deve esporre direttamente i nomi usati dal template XSLT nei `normalize-space(...)`.
2. `xml_mapping` contiene solo eccezioni:
   - rinomina di un campo non 1:1
   - concatenazione di piu colonne in un campo target
   - attributi root richiesti dal template ma non presenti 1:1 nel DataFrame
3. `xml_grouping` contiene solo le chiavi di grouping per le sezioni che hanno figli.
4. Le chiavi di `xml_grouping` devono preferibilmente usare il path sezione del template, ad esempio `Sales/Transaction`.
5. Se il template richiede un attributo root o un campo che non si ricava da DataFrame o `xml_mapping`, il processo va in errore.
6. Se una sezione con figli non ha la relativa entry in `xml_grouping`, il processo va in errore.

## 5. Template Standard Config JSON

Esempio di configurazione per un nuovo data sharing XML:

```json
{
  "code": "CL001",
  "name": "New Customer",
  "Campo": "TC_Soci_NewCustomer_Attivo",
  "file_type": "xml",
  "delivery_method": "ftp",
  "fields": "TC_Soci_NewCustomer_Attivo",
  "query_file": "New_Customer_query.sql",
  "xslt_template": "New_Customer_transformation.xslt",
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
  "naming_variables": {
    "TRACK_ID": "1"
  },
  "naming_convention": "NEW_CUSTOMER_YYYYMMDDhhmmss"
}
```

Nota sui path nel JSON:

- `query_file` puo essere solo il nome file se il file si trova in `querysql/{COD_datasharing}`
- `xslt_template` puo essere solo il nome file se il template si trova in `templatexml/{COD_datasharing}`
- se serve, entrambi possono anche essere configurati con path assoluti

### Placeholder ufficiali in naming_convention

`naming_convention` supporta due famiglie di placeholder:

- placeholder data legacy gia presenti in `config.placeholders`, ad esempio `YYYYMMDDhhmmss`
- placeholder nominati nel formato `{NOME_CAMPO}`

Placeholder nominati ufficialmente supportati:

- `{SOCIO}`: codice socio richiesto
- `{PERIODO}`: periodo richiesto nel formato `YYYYMM`
- `{YYYY_PERIODO}`: anno del periodo richiesto
- `{MM_PERIODO}`: mese del periodo richiesto
- `{DATASHARING_CODE}`: codice del data sharing, ad esempio `CC001`
- `{FILE_TYPE}`: tipo file, ad esempio `xml` o `csv`
- `{NOME_COLONNA_QUERY}`: qualunque colonna disponibile nel primo record della query, ad esempio `{WholesalerID}`
- `{NOME_VARIABILE}`: qualunque variabile definita in `naming_variables`

### naming_variables

`naming_variables` è opzionale e serve solo per costanti di tracciato o varianti che non arrivano dalla query.

Esempio:

```json
"naming_variables": {
  "TRACK_ID": "1"
}
```

### Convenzione consigliata

Per convenzioni stabili e leggibili, usa questo schema:

```json
"naming_convention": "{WholesalerID}_{MM_PERIODO}_{YYYY_PERIODO}_1"
```

Esempi:

```json
{
  "code": "CC001",
  "naming_convention": "{WholesalerID}_{MM_PERIODO}_{YYYY_PERIODO}_1"
}
```

```json
{
  "code": "CC002",
  "naming_convention": "{WholesalerID}_{MM_PERIODO}_{YYYY_PERIODO}_2"
}
```

Se il suffisso è fisso, mettilo direttamente nel `naming_convention` invece di usare `naming_variables`.

Questa convenzione vale in modo uniforme per XML, CSV ed Excel.

## 6. Cosa Va Nella Query SQL

La query deve esporre, quando possibile, le colonne con i nomi richiesti dal template XSLT.

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

## 7. Cosa Va In xml_mapping

`xml_mapping` va usato solo per i casi non 1:1.

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

## 8. Cosa Va In xml_grouping

`xml_grouping` va usato solo per il grouping delle sezioni con figli.

Esempio:

```json
{
  "Sales/Transaction": ["CodiceCliente"],
  "Orders/Order": ["OrderNumber", "OrderDate"]
}
```

## 9. Convenzione Operativa Consigliata

Per aggiungere un nuovo data sharing XML:

1. creare o copiare la query SQL dentro `querysql/{COD_datasharing}`
2. creare o copiare il template XSLT dentro `templatexml/{COD_datasharing}`
3. aggiungere la nuova voce in `data_sharing_options` nel `config.json`
4. usare `xml_mapping` solo per le eccezioni reali
5. usare `xml_grouping` solo dove il template ha sezioni annidate
6. verificare che output e log finiscano sotto la root definita da `artifacts_root_path`

## 10. Configurazione Invio e Recap

L'invio operativo e il recap finale usano la sezione `mail_config` del file di configurazione.

Esempio:

```json
"mail_config": {
  "smtp_server": "spamfight.mdsnet.it",
  "port": 26,
  "user": "email_user",
  "password": "email_password",
  "sender_email": "dwh@cdaweb.it",
  "summary_sender_email": "norepy@cdaweb.it",
  "summary_recipient": "dwh@cdaweb.it"
}
```

Significato dei campi:

- `sender_email`: mittente standard per eventuali invii verso destinatari esterni al data sharing
- `summary_sender_email`: mittente usato per la mail di recap interna
- `summary_recipient`: casella che riceve il riepilogo finale di ogni elaborazione

Contenuto del recap:

- esito dell'elaborazione
- codice e nome del data sharing
- codice e nome del socio
- periodo elaborato
- modalita di consegna
- destinatario o destinazione dell'invio
- elenco file inviati, incluso l'eventuale `.ok`
- percorso locale del file generato
- messaggio sintetico finale

Oggetto del recap:

- `DataSharing <Nome Data Sharing> - <Codice Socio> <Nome Socio>`

## 11. Comportamento in DEBUG

Quando `DEBUG` e impostato a `true`:

- il file viene comunque generato e salvato localmente
- la pubblicazione esterna viene saltata
- il tracking Coca Cola non viene scritto su database
- il recap mail indica che la pubblicazione non e stata eseguita

Questa modalita e utile per testare naming, query, generazione file e salvataggio locale senza spedire nulla all'esterno.

## 12. Note FTP

Per le opzioni con `delivery_method: ftp`:

- il file viene inviato all'host configurato nel blocco `ftp_config`
- se `create_ok_file` e `true`, dopo il file principale viene caricato anche il marker `.ok`
- il recap finale elenca entrambi i file quando presenti
