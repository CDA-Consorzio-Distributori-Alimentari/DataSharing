## Manuale Regole di Nomenclatura e Struttura Database (MS-SQL)

### NOTE IMPORTANTI SUGLI SCHEMI
- gli scripot di creazione delle tabelle, indici, trigger e oggetti devono essere salvati $projectFolder$\CDA\CDABackEnd\Database\Scripts\sql\
- gli script di crete saranno Create_<nome_tabella>.sql
- gli script di foreinkey fk_<nomeforeinkey>.sql
- **In ogni script di creazione deve essere inclusa solo la tabella principale a cui lo script si riferisce. Non includere la creazione di altre tabelle non direttamente correlate nello stesso script.**
- Tutte le tabelle, indici, trigger e oggetti di **configurazione del sistema** devono essere creati nello **schema `CFG`**.
- Tutte le tabelle, indici, trigger e oggetti che riguardano **il DWH** (acquisti, vendite, clienti, fornitori, soci, ecc.) devono essere creati nello **schema `DBO`**.
- Tutte le tabelle e viste dedicate allo **scambio dati con altri sistemi** devono essere create:
  - nello **schema `TI`** per dati in ingresso,
  - nello **schema `TO`** per dati in uscita.
- Eventuali spazi nei nomi di tabelle, colonne, indici, trigger e oggetti devono essere sempre sostituiti da underscore (`_`).
- non sono ammessi nomi di accentati e altri caratteri speciali al di fuori dell'underscore_
---

### 1. Convenzioni di Nomenclatura

- Tutti i nomi di tabelle, colonne, indici, trigger sono in **maiuscolo** e senza spazi.
- Gli spazi sono sempre sostituiti da underscore (`_`).
- **Schema**:
  - `CFG`: per oggetti di configurazione del sistema.
  - `DBO`: per oggetti DWH (acquisti, vendite, clienti, fornitori, soci, ecc.).
  - `TI`/`TO`: per scambio dati con altri sistemi (TI = ingresso, TO = uscita).
- **Formato nome tabella/vista**: `ZZ_DDDDDDDDDDDDDDDDd`
  - `ZZ`: prefisso tipologia (2 caratteri, es. TA, TD, TR, TE, TW, TH, TX per tabelle; VA, VD, VR, VE, VH, VW, VX per viste)
  - `DDD...`: descrizione parlante (min 3, max 27 caratteri, nome completo < 30 caratteri)
  - Separatore: underscore `_` tra prefisso e descrizione
- **Tipologie**:
  - **Tabelle**:
    - `TA_`: tabella anagrafica
    - `TD_`: tabella di dominio/tipo
    - `TR_`: tabella di relazione
    - `TE_`: tabella eventi
    - `TW_`: tabella di appoggio non visibile all'utente
    - `TH_`: tabella per DWH
    - `TX_`: tabella di eccezioni/log
  - **Viste** (usano 'V' al posto di 'T'):
    - `VA_`: vista di tabella anagrafica
    - `VD_`: vista di tabella di dominio
    - `VR_`: vista di tabella di relazione
    - `VE_`: vista di tabella eventi
    - `VH_`: vista per DWH
    - `VW_`: vista di working
    - `VX_`: vista di eccezioni/log
- **Indici**: `IN_<NOME_TABELLA>_<DESCRIZIONE>`
- **Trigger**: `CFG.TRI_<NOME_TABELLA>_AU_INS`, `CFG.TRU_<NOME_TABELLA>_AU_UPD`, `CFG.TRD_<NOME_TABELLA>_AU_DEL`
- **Tabelle di audit**: `<NOME_TABELLA>_AU` (solo per TA_ e TD_)

---

### 2. Convenzioni sui Nomi dei Campi

- **ID_...**   : Chiave primaria. Tipi consigliati: `INT` o `UNIQUEIDENTIFIER`.
- **COD_...**  : Codice. **Deve essere definito come `CHAR(x) NOT NULL`** (di solito `CHAR(3)`, ma la lunghezza può variare in base al dominio). Non utilizzare `VARCHAR` o permettere valori nulli.
- **DES_...**  : Descrizione. Tipo consigliato: `VARCHAR`.
- **NOM_...**  : Nome. Tipo consigliato: `VARCHAR`.
- **FLG_...**  : Flag booleano (0/1). Tipo consigliato: `BIT NOT NULL` (default 0).
- **TMS_...**  : Timestamp. Tipi consigliati: `DATETIME` o `DATETIME2`.

**Altri prefissi utilizzabili:**
- **PRC_...** : Percentuale. Tipo: `DECIMAL(32,15)`
- **NUM_...** : Numero intero. Tipo: `INTEGER`
- **QTA_...** : Quantità. Tipo: `DECIMAL(32,15)`
- **DAT_...** : Data (formato dd/mm/aaaa). Tipo: `DATE`
- **IMP_...** : Importo. Tipo: `DECIMAL(32,15)`
- **VAL_...** : Valore generico. Tipo: `DECIMAL(32,15)`
- **GEO_...** : Coordinata georeferenziazione. Tipo: `DECIMAL(9,6)`
- **ORA_...** : Ora. Tipo: `TIME`
- **PRB_...** : Probabilità (range 0-1). Tipo: `DECIMAL(6,5)`

**Riepilogo sintetico:**
| Prefisso | Significato                   | Tipo consigliato         |
|----------|-------------------------------|-------------------------|
| ID_      | Chiave primaria               | INT/UNIQUEIDENTIFIER    |
| COD_     | Codice                        | CHAR(x) NOT NULL        |
| DES_     | Descrizione                   | VARCHAR                 |
| NOM_     | Nome                          | VARCHAR                 |
| FLG_     | Flag (0/1)                    | BIT NOT NULL            |
| IMP_     | Importo                       | DECIMAL(32,15)          |
| VAL_     | Valore generico               | DECIMAL(32,15)          |
| GEO_     | Coordinata georeferenziazione | DECIMAL(9,6)            |
| ORA_     | Ora                           | TIME                    |
| PRC_     | Percentuale                   | DECIMAL(32,15)          |
| NUM_     | Numero intero                 | INTEGER                 |
| QTA_     | Quantità                      | DECIMAL(32,15)          |
| DAT_     | Data                          | DATE                    |
| PRB_     | Probabilità (0-1)             | DECIMAL(6,5)            |
| TMS_     | Timestamp                     | DATETIME/DATETIME2      |

---

### 3. Struttura Tabelle di Relazione (TR_)

- Chiave primaria composta (es. ID_MENU, ID_USER)
- Campi obbligatori di sistema:
  - `FLG_DELETE` BIT NOT NULL DEFAULT 0
  - `FLG_ACTIVE` BIT NOT NULL DEFAULT 1
  - `FLG_VISIBLE` BIT NOT NULL DEFAULT 1
  - `ID_USER_INSERT` UNIQUEIDENTIFIER NOT NULL
  - `TMS_INSERT` DATETIME NOT NULL DEFAULT GETDATE()
  - `ID_USER_UPDATE` UNIQUEIDENTIFIER NULL
  - `TMS_UPDATE` DATETIME NULL
  - `ID_USER_DELETE` UNIQUEIDENTIFIER NULL
  - `TMS_DELETE` DATETIME NULL
- Questi campi **non sono visibili/modificabili dalla UI** e vanno gestiti solo dal backend.
- Questi campi vanno messi in fondo allo script di creazione della tabella, ovvero dopo i campi previsti per la tabella.
- La cancellazione è sempre **logica**: si imposta `FLG_DELETE=1`, `ID_USER_DELETE` e `TMS_DELETE`.
- Gli script SQL devono includere la cancellazione di oggetti esistenti (DROP TABLE/INDEX).
- Le tabelle TR_ **non hanno** tabelle di audit.
- veranno impostati appositi job di pulizia per eliminare i record con `FLG_DELETE=1` dopo un certo periodo (es. 2 anni).
- se non è possibile valorizzare con l'utente autenticato nell'applicazione,  si può usare `SYSTEM_USER` nei trigger SQL o `USER` in T-SQL.

---

### 4. Struttura Tabelle Anagrafiche (TA_) e di Dominio (TD_)
- Campi obbligatori di sistema:
  - `COD_REFSTR`  AS ('ABC-'+right('00000'+CONVERT([varchar](5),[ID_KEY_TABLE]),(5))),
  - `FLG_DELETE` BIT NOT NULL DEFAULT 0
  - `FLG_ACTIVE` BIT NOT NULL DEFAULT 1
- Questi campi **non sono visibili/modificabili dalla UI** e vanno gestiti solo dal backend.
- Il campo calcolato COD_REFSTR viene gestito come una colonna "computed" (calcolata) in SQL Server. Non è un campo fisico, ma il suo valore viene generato automaticamente dal database ogni volta che si legge la riga.

La formula:

'ABC-' è un prefisso fisso che identifica come acronimo la tabella stessa:
  -SOC per socio
  -JOB per job 
  -ROL per ruolo

-right('00000'+CONVERT([varchar](5),[ID_KEY_TABLE]),(5)) prende il valore della chiave primaria ID_KEY_TABLE, lo converte in stringa, lo precede con zeri fino a 5 cifre, e ne prende le ultime 5 cifre.
Questo campo serve per avere un codice identificativo leggibile, strutturato e univoco, utile per referenze esterne o visualizzazione, senza duplicare dati. Non è modificabile dalla UI o dal backend: viene calcolato dal database in tempo reale.



- Oltre ai campi specifici, **devono avere** la tabella di audit `<NOME_TABELLA>_AU`.
- La tabella di audit contiene:
  - `ID_AUDIT` INT IDENTITY(1,1) PRIMARY KEY
  - `DES_OPERAZIONE` VARCHAR(10) NOT NULL
  - `TMS_OPERAZIONE` DATETIME NOT NULL DEFAULT GETDATE()
  - Tutti i campi della tabella originale con suffissi `_OLD` e `_NEW`
  - `NOM_USER`, `NOM_HOST`, `DES_SESSION`:
    - **NOM_USER**: nome utente che ha eseguito l’operazione (`SYSTEM_USER` nei trigger SQL, utente autenticato in applicazione)
    - **NOM_HOST**: nome della macchina/host da cui è partita l’operazione (`HOST_NAME()`)
    - **DES_SESSION**: info sulla sessione applicativa (`APP_NAME()` o identificativo sessione)
    - Questi valori sono impostati automaticamente dai trigger di audit o dal backend applicativo.
  - `TMS_INSERIMENTO` DATETIME NOT NULL DEFAULT GETDATE(): indica l’ora di inserimento o modifica della riga nella tabella di audit.
- Tre trigger (insert, update, delete) popolano la tabella di audit.
- se non è possibile valorizzare con l'utente autenticato nell'applicazione,  si può usare `SYSTEM_USER` nei trigger SQL o `USER` in T-SQL.
- **Nota:** Nelle tabelle di dominio (TD_) è frequente che il campo `COD_...` sia utilizzato come chiave primaria.
- Tutte le tabelle anagrafiche (prefisso TA_) **devono** includere i seguenti campi obbligatori:
  - `FLG_DELETE BIT NOT NULL DEFAULT 0`
  - `FLG_ACTIVE BIT NOT NULL DEFAULT 0`
- Questi campi devono essere presenti anche nella rispettiva tabella di audit, sia come `<NOME_CAMPO>_OLD` che `<NOME_CAMPO>_NEW`.
- I trigger di audit devono gestire i valori di questi campi sia in inserimento, aggiornamento che cancellazione.
- **Non utilizzare più il campo `FLG_ATTIVO`**: sostituirlo sempre con `FLG_ACTIVE`.
- Tutti i campi che iniziano con `COD_` **devono essere definiti come** `CHAR(x) NOT NULL` (di solito `CHAR(3)`, ma la lunghezza può variare in base al dominio). Non utilizzare `VARCHAR` o permettere valori nulli per i campi `COD_`.
- La regola si applica anche alle tabelle di audit (sia OLD che NEW).

---

### 5. Script di Creazione

- Ogni script deve:
  1. Droppare trigger, tabelle di audit, tabelle principali, indici se esistenti (in quest'ordine)
  2. Creare la tabella principale
  3. Creare la tabella di audit (solo per TA_ e TD_)
  4. Creare indici e trigger
- **In ogni script di creazione deve essere inclusa solo la tabella principale a cui lo script si riferisce. Non includere la creazione di altre tabelle non direttamente correlate nello stesso script.**

---

### 6. Modelli C#

- I campi di sistema sono decorati con `[Browsable(false)]` e `[ScaffoldColumn(false)]`.
- I commenti devono chiarire che questi campi sono gestiti solo dal backend.

---

### 7. Backend

- In fase di insert: valorizzare `ID_USER_INSERT` e `TMS_INSERT`.
- In fase di update: valorizzare `ID_USER_UPDATE` e `TMS_UPDATE`.
- In fase di cancellazione logica: valorizzare `FLG_DELETE=1`, `ID_USER_DELETE`, `TMS_DELETE`.
- Le query di lettura devono escludere i record con `FLG_DELETE=1`.

---

### 8. Regole Speciali per Schemi TO e TI (Scambio Dati)

- Il nome delle tabelle/viste deve essere quello deciso nel documento di interscambio (maiuscolo o minuscolo, spazi sostituiti da underscore).
- I nomi delle colonne non avranno prefissi ma riporteranno il nome deciso nel documento di interscambio.
- **I nomi delle colonne/campi devono mantenere lo stesso case (maiuscole/minuscole) del documento di interscambio, sostituendo solo gli spazi con underscore (`_`).**
- Non sono ammessi caratteri accentati o speciali diversi dall'underscore.
- non avranno chiave, reference o unique 
- Tutti i tipi delle colonne saranno `VARCHAR` secondo la lunghezza decisa.
- Le colonne possono essere `NULL` o `NOT NULL` secondo specifica.
- **Non** devono mai avere tabelle di audit o trigger di audit.
- non verranno usate(valorizzate) dalla web app ma dai SSIS.
- la web app funger� da orchestratore per l'inserimento dei dati.
- Prima dello scarico in produzione, le tabelle schema TO. e TI devono essere create con script di partenza che includano la cancellazione di oggetti esistenti (DROP TABLE/INDEX).
- la web app tramite apposite tabelle di configurazione potra modificare lo schema delle tabelle dello schema TO. e TI.
- - **Campi obbligatori** (sempre presenti in tutte le tabelle  schema TO. e TI.):
  - `ID_SOCIO` INTEGER NOT NULL
  - `COD_JOB` UNIQUEIDENTIFIER NULL
  - `NUM_RIGA` INTEGER NOT NULL
  - `NOM_FILE` VARCHAR(255)
  - `DAT_INSERIMENTO` DATETIME NOT NULL DEFAULT GETDATE()
- Prima dell'inserimento, i dati devono essere cancellati per socio.

## Regole aggiuntive per tabelle TI e TO

Le tabelle con prefisso **TI** e **TO** devono rispettare anche le seguenti regole:

- `ID_SOCIO`, `COD_JOB` e `NUM_RIGA` costituiscono la chiave logica della tabella
- il primo campo della tabella deve essere `ID_SOCIO`
- gli ultimi campi della tabella devono essere, nell'ordine:
    - `COD_JOB`
    - `DAT_CARICAMENTO`
    - `NOM_FILE`
    - `NUM_RIGA`

Questa struttura e obbligatoria per tutte le tabelle `TI` e `TO`.

- Esempio DDL:
CREATE TABLE TO.NOME_TABELLA_ (
    ID_SOCIO INTEGER NOT NULL,
    -- campi di interfaccia come da documento di interscambio
    COD_JOB UNIQUEIDENTIFIER NULL,
    NOM_FILE VARCHAR(255),
    DAT_INSERIMENTO DATETIME NOT NULL DEFAULT GETDATE()
);

CREATE TABLE TI.NOME_TABELLA_ (
    ID_SOCIO INTEGER NOT NULL,
    -- campi di interfaccia come da documento di interscambio
    COD_JOB UNIQUEIDENTIFIER NULL,
    NOM_FILE VARCHAR(255),
    DAT_INSERIMENTO DATETIME NOT NULL DEFAULT GETDATE()
);

---

### 9. Tracking Operazioni e Gestione Sessioni

- Tutte le operazioni effettuate dagli utenti (login, logout, creazione, modifica, cancellazione, reset password, attivazione/disattivazione) devono essere tracciate nella tabella `TE_USERTRACK` (tabella eventi).
- La gestione delle sessioni, login/logout e tentativi di accesso deve essere implementata tramite la tabella `TE_USERSESSION` (tabella eventi).
- La tabella TE_USERSESSION utilizza il campo `ID_USERSESSION` di tipo `UNIQUEIDENTIFIER` (GUID) come token di sessione, compatibile con la gestione sessioni ASP.NET/AJAX.
- La tabella di gestione utenti (anagrafica) � `TA_USERLOGIN`.

---

### NOTE FINALI

- Solo le tabelle TA_ e TD_ hanno la tabella di audit e i relativi trigger.
- Le tabelle TR_, TO_, TI_ **non** hanno audit.
- Le viste seguono la stessa regola di nomenclatura delle tabelle, ma con il prefisso 'V' al posto di 'T' (es. VA_, VD_, VR_, VE_, VH_, VW_, VX_).
- Tutte le regole valgono per MS-SQL.

## Note

- In caso di modifica di tabelle TA_ già esistenti, rimuovere eventuali colonne `FLG_ATTIVO` e sostituirle con `FLG_ACTIVE`.
- Gli script Python e c# di generazione automatica devono rispettare queste regole.

### Nota sulla creazione della tabella TA_RUOLO

La tabella `TA_RUOLO` è la tabella anagrafica centrale per la gestione dei ruoli.  
La sua creazione deve essere gestita nello script `Create_TA_RUOLO.sql`, che include anche la tabella di audit e i trigger di audit.

## schema script create per tabelle TA_ e TD_
-- ===========================================
-- ATTENZIONE: Prima di eseguire questo script assicurati di aver cancellato tutte le tabelle che hanno foreign key verso CFG.<TA_NOME_TABELLA>.
-- In particolare, la tabella CFG.TR_MENU_UTENTE dipende da CFG.<TA_NOME_TABELLA> tramite la FK FK_TR_MENU_UTENTE_ID_MENU.
-- Cancella prima CFG.TR_MENU_UTENTE se presente!


## INIZIO SCRIPT CREZIONE TA
-- ===========================================
-- DROP OGGETTI SE ESISTENTI (ORDER: TRIGGER, FK, MAIN TABLE, INDEX)
-- ===========================================

IF OBJECT_ID('CFG.TRI_<TA_NOME_TABELLA>_AU_INS', 'TR') IS NOT NULL DROP TRIGGER CFG.TRI_<TA_NOME_TABELLA>_AU_INS;
IF OBJECT_ID('CFG.TRU_<TA_NOME_TABELLA>_AU_UPD', 'TR') IS NOT NULL DROP TRIGGER CFG.TRU_<TA_NOME_TABELLA>_AU_UPD;
IF OBJECT_ID('CFG.TRD_<TA_NOME_TABELLA>_AU_DEL', 'TR') IS NOT NULL DROP TRIGGER CFG.TRD_<TA_NOME_TABELLA>_AU_DEL;

IF OBJECT_ID('CFG.FK_<TA_NOME_TABELLA>_ID_MENU_PADRE', 'F') IS NOT NULL
    ALTER TABLE CFG.<TA_NOME_TABELLA> DROP CONSTRAINT FK_<TA_NOME_TABELLA>_ID_MENU_PADRE;

IF OBJECT_ID('CFG.<TA_NOME_TABELLA>_AU', 'U') IS NOT NULL DROP TABLE CFG.<TA_NOME_TABELLA>_AU;
IF OBJECT_ID('CFG.<TA_NOME_TABELLA>', 'U') IS NOT NULL DROP TABLE CFG.<TA_NOME_TABELLA>;

IF EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'IN_<TA_NOME_TABELLA>_COD_<tabella>' AND object_id = OBJECT_ID('CFG.<TA_NOME_TABELLA>'))
    DROP INDEX IN_<TA_NOME_TABELLA>_COD_<tabella> ON CFG.<TA_NOME_TABELLA>;

-- ===========================================
-- CREAZIONE TABELLA ANAGRAFICA <TA_NOME_TABELLA>
-- ===========================================

CREATE TABLE CFG.<TA_NOME_TABELLA> (
    ID_<tabella>         INT IDENTITY(1,1) NOT NULL,
    COD_REFSTR           AS ('<ACRONIMO>-' + RIGHT('00000' + CONVERT(VARCHAR(5), 
ID_<tabella>), 5)),    
    DES_<tabella>        VARCHAR(100) NOT NULL,
    COD_<TD_tabella>        CHAR(3) NOT NULL,
    -- altri campi specifici...
    
    FLG_DELETE           BIT NOT NULL DEFAULT 0,
    FLG_ACTIVE           BIT NOT NULL DEFAULT 1,
    CONSTRAINT PK_<TA_NOME_TABELLA> PRIMARY KEY (ID_<tabella>)
);

CREATE UNIQUE INDEX IN_<TD_NOME_TABELLA>_COD_<td_tabella> ON CFG.<TD_NOME_TABELLA> (COD_<td_tabella>);

-- ===========================================
-- CREAZIONE TABELLA DI AUDIT
-- ===========================================

CREATE TABLE CFG.<TA_NOME_TABELLA>_AU (
    ID_AUDIT                INT IDENTITY(1,1) PRIMARY KEY,
    DES_OPERAZIONE          VARCHAR(10) NOT NULL,
    TMS_OPERAZIONE          DATETIME NOT NULL DEFAULT GETDATE(),

    -- OLD VALUES
    ID_MENU_OLD             INT          NULL,
    DES_MENU_OLD            VARCHAR(100) NULL,
    ID_MENU_PADRE_OLD       INT          NULL,
    ORDINE_OLD              INT          NULL,
    FLG_DELETE_OLD          BIT          NULL,
    FLG_ACTIVE_OLD          BIT          NULL,

    -- NEW VALUES
    ID_MENU_NEW             INT          NULL,
    DES_MENU_NEW            VARCHAR(100) NULL,
    ID_MENU_PADRE_NEW       INT          NULL,
    ORDINE_NEW              INT          NULL,
    FLG_DELETE_NEW          BIT          NULL,
    FLG_ACTIVE_NEW          BIT          NULL,

    NOM_USER                VARCHAR(128) NULL,
    NOM_HOST                VARCHAR(128) NULL,
    DES_SESSION             VARCHAR(128) NULL,
    TMS_INSERIMENTO         DATETIME NOT NULL DEFAULT GETDATE()
);
GO
-- ===========================================
-- TRIGGER INSERT AUDIT
-- ===========================================

CREATE TRIGGER CFG.TRI_<TA_NOME_TABELLA>_AU_INS
ON CFG.<TA_NOME_TABELLA>
AFTER INSERT
AS
BEGIN
    SET NOCOUNT ON;
    INSERT INTO CFG.<TA_NOME_TABELLA>_AU (
        DES_OPERAZIONE, TMS_OPERAZIONE,
        ID_<tabella>_OLD, COD_<tabella>_OLD, DES_<tabella>_OLD,.....,FLG_DELETE_OLD, FLG_ACTIVE_OLD,
        ID_<tabella>_NEW, COD_<tabella>_NEW, DES_<tabella>_NEW,.....,FLG_DELETE_NEW, FLG_ACTIVE_NEW,
        NOM_USER, NOM_HOST, DES_SESSION
    )
    SELECT
        'INSERT', GETDATE(),
        NULL, NULL, NULL, NULL, NULL,
        I.ID_<tabella>, I.COD_<tabella>, I.DES_<tabella>,.....,I.FLG_DELETE, I.FLG_ACTIVE,
        SYSTEM_USER, HOST_NAME(), APP_NAME()
    FROM INSERTED I;
END
GO

-- ===========================================
-- TRIGGER UPDATE AUDIT
-- ===========================================

CREATE TRIGGER CFG.TRU_<TA_NOME_TABELLA>_AU_UPD
ON CFG.<TA_NOME_TABELLA>
AFTER UPDATE
AS
BEGIN
    SET NOCOUNT ON;
    INSERT INTO CFG.<TA_NOME_TABELLA>_AU (
        DES_OPERAZIONE, TMS_OPERAZIONE,
        ID_<tabella>_OLD, COD_<tabella>_OLD, DES_<tabella>_OLD,.....,FLG_DELETE_OLD, FLG_ACTIVE_OLD,
        ID_<tabella>_NEW, COD_<tabella>_NEW, DES_<tabella>_NEW,.... ,FLG_DELETE_NEW, FLG_ACTIVE_NEW,
        NOM_USER, NOM_HOST, DES_SESSION
    )
    SELECT
        'UPDATE', GETDATE(),
        D.ID_<tabella>, D.COD_<tabella>, D.DES_<tabella>,.....,D.FLG_DELETE, D.FLG_ACTIVE,
        I.ID_<tabella>, I.COD_<tabella>, I.DES_<tabella>,.....,I.FLG_DELETE, I.FLG_ACTIVE,
        SYSTEM_USER, HOST_NAME(), APP_NAME()
    FROM DELETED D
    INNER JOIN INSERTED I ON D.ID_<tabella> = I.ID_<tabella>;
END
GO

-- ===========================================
-- TRIGGER DELETE AUDIT
-- ===========================================

CREATE TRIGGER CFG.TRD_<TA_NOME_TABELLA>_AU_DEL
ON CFG.<TA_NOME_TABELLA>
AFTER DELETE
AS
BEGIN
    SET NOCOUNT ON;
    INSERT INTO CFG.<TA_NOME_TABELLA>_AU (
        DES_OPERAZIONE, TMS_OPERAZIONE,
        ID_<tabella>_OLD, COD_<tabella>_OLD, DES_<tabella>_OLD,.....,FLG_DELETE_OLD, FLG_ACTIVE_OLD,
        ID_<tabella>_NEW, COD_<tabella>_NEW, DES_<tabella>_NEW,.....,FLG_DELETE_NEW, FLG_ACTIVE_NEW,
        NOM_USER, NOM_HOST, DES_SESSION
    )
    SELECT
        'DELETE', GETDATE(),
        D.ID_<tabella>, D.COD_<tabella>, D.DES_<tabella>,.....,D.FLG_DELETE, D.FLG_ACTIVE,
        NULL, NULL, NULL, NULL, NULL,
        SYSTEM_USER, HOST_NAME(), APP_NAME()
    FROM DELETED D;
END
GO

## fine 

## INIZIO SCRIPT CREZIONE TD
-- ===========================================
-- DROP OGGETTI SE ESISTENTI (ORDER: TRIGGER, MAIN TABLE, INDEX)
-- ===========================================

IF OBJECT_ID('CFG.TRI_<TD_NOME_TABELLA>_AU_INS', 'TR') IS NOT NULL DROP TRIGGER CFG.TRI_<TD_NOME_TABELLA>_AU_INS;
IF OBJECT_ID('CFG.TRU_<TD_NOME_TABELLA>_AU_UPD', 'TR') IS NOT NULL DROP TRIGGER CFG.TRU_<TD_NOME_TABELLA>_AU_UPD;
IF OBJECT_ID('CFG.TRD_<TD_NOME_TABELLA>_AU_DEL', 'TR') IS NOT NULL DROP TRIGGER CFG.TRD_<TD_NOME_TABELLA>_AU_DEL;

IF OBJECT_ID('CFG.<TD_NOME_TABELLA>_AU', 'U') IS NOT NULL DROP TABLE CFG.<TD_NOME_TABELLA>_AU;
IF OBJECT_ID('CFG.<TD_NOME_TABELLA>', 'U') IS NOT NULL DROP TABLE CFG.<TD_NOME_TABELLA>;

IF EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'IN_<TD_NOME_TABELLA>_COD_<td_tabella>' AND object_id = OBJECT_ID('CFG.<TD_NOME_TABELLA>'))
    DROP INDEX IN_<TD_NOME_TABELLA>_COD_<td_tabella> ON CFG.<TD_NOME_TABELLA>;

-- ===========================================
-- CREAZIONE TABELLA DOMINIO <TD_NOME_TABELLA>
-- ===========================================

CREATE TABLE CFG.<TD_NOME_TABELLA> (
    COD_<td_tabella>     CHAR(3) NOT NULL,
    DES_<td_tabella>     VARCHAR(100) NOT NULL,
    FLG_DELETE           BIT NOT NULL DEFAULT 0,
    FLG_ACTIVE           BIT NOT NULL DEFAULT 1,
    CONSTRAINT PK_<TD_NOME_TABELLA> PRIMARY KEY (COD_<td_tabella>)
);

CREATE UNIQUE INDEX IN_<TD_NOME_TABELLA>_COD_<td_tabella> ON CFG.<TD_NOME_TABELLA> (COD_<td_tabella>);

-- ===========================================
-- CREAZIONE TABELLA DI AUDIT
-- ===========================================

CREATE TABLE CFG.<TD_NOME_TABELLA>_AU (
    ID_AUDIT            INT IDENTITY(1,1) PRIMARY KEY,
    DES_OPERAZIONE      VARCHAR(10) NOT NULL,
    TMS_OPERAZIONE      DATETIME NOT NULL DEFAULT GETDATE(),

    -- OLD VALUES
    COD_<td_tabella>_OLD   CHAR(3) NULL,
    DES_<td_tabella>_OLD   VARCHAR(100) NULL,
    FLG_DELETE_OLD         BIT NULL,
    FLG_ACTIVE_OLD         BIT NULL,

    -- NEW VALUES
    COD_<td_tabella>_NEW   CHAR(3) NULL,
    DES_<td_tabella>_NEW   VARCHAR(100) NULL,
    FLG_DELETE_NEW         BIT NULL,
    FLG_ACTIVE_NEW         BIT NULL,

    NOM_USER            VARCHAR(128) NULL,
    NOM_HOST            VARCHAR(128) NULL,
    DES_SESSION         VARCHAR(128) NULL,
    TMS_INSERIMENTO     DATETIME NOT NULL DEFAULT GETDATE()
);

-- ===========================================
-- TRIGGER INSERT AUDIT
-- ===========================================

CREATE TRIGGER CFG.TRI_<TD_NOME_TABELLA>_AU_INS
ON CFG.<TD_NOME_TABELLA>
AFTER INSERT
AS
BEGIN
    SET NOCOUNT ON;
    INSERT INTO CFG.<TD_NOME_TABELLA>_AU (
        DES_OPERAZIONE, TMS_OPERAZIONE,
        COD_<td_tabella>_OLD, DES_<td_tabella>_OLD, FLG_DELETE_OLD, FLG_ACTIVE_OLD,
        COD_<td_tabella>_NEW, DES_<td_tabella>_NEW, FLG_DELETE_NEW, FLG_ACTIVE_NEW,
        NOM_USER, NOM_HOST, DES_SESSION
    )
    SELECT
        'INSERT', GETDATE(),
        NULL, NULL, NULL, NULL,
        I.COD_<td_tabella>, I.DES_<td_tabella>, I.FLG_DELETE, I.FLG_ACTIVE,
        SYSTEM_USER, HOST_NAME(), APP_NAME()
    FROM INSERTED I;
END
GO

-- ===========================================
-- TRIGGER UPDATE AUDIT
-- ===========================================

CREATE TRIGGER CFG.TRU_<TD_NOME_TABELLA>_AU_UPD
ON CFG.<TD_NOME_TABELLA>
AFTER UPDATE
AS
BEGIN
    SET NOCOUNT ON;
    INSERT INTO CFG.<TD_NOME_TABELLA>_AU (
        DES_OPERAZIONE, TMS_OPERAZIONE,
        COD_<td_tabella>_OLD, DES_<td_tabella>_OLD, FLG_DELETE_OLD, FLG_ACTIVE_OLD,
        COD_<td_tabella>_NEW, DES_<td_tabella>_NEW, FLG_DELETE_NEW, FLG_ACTIVE_NEW,
        NOM_USER, NOM_HOST, DES_SESSION
    )
    SELECT
        'UPDATE', GETDATE(),
        D.COD_<td_tabella>, D.DES_<td_tabella>, D.FLG_DELETE, D.FLG_ACTIVE,
        I.COD_<td_tabella>, I.DES_<td_tabella>, I.FLG_DELETE, I.FLG_ACTIVE,
        SYSTEM_USER, HOST_NAME(), APP_NAME()
    FROM DELETED D
    INNER JOIN INSERTED I ON D.COD_<td_tabella> = I.COD_<td_tabella>;
END
GO

-- ===========================================
-- TRIGGER DELETE AUDIT
-- ===========================================

CREATE TRIGGER CFG.TRD_<TD_NOME_TABELLA>_AU_DEL
ON CFG.<TD_NOME_TABELLA>
AFTER DELETE
AS
BEGIN
    SET NOCOUNT ON;
    INSERT INTO CFG.<TD_NOME_TABELLA>_AU (
        DES_OPERAZIONE, TMS_OPERAZIONE,
        COD_<td_tabella>_OLD, DES_<td_tabella>_OLD, FLG_DELETE_OLD, FLG_ACTIVE_OLD,
        COD_<td_tabella>_NEW, DES_<td_tabella>_NEW, FLG_DELETE_NEW, FLG_ACTIVE_NEW,
        NOM_USER, NOM_HOST, DES_SESSION
    )
    SELECT
        'DELETE', GETDATE(),
        D.COD_<td_tabella>, D.DES_<td_tabella>, D.FLG_DELETE, D.FLG_ACTIVE,
        NULL, NULL, NULL, NULL,
        SYSTEM_USER, HOST_NAME(), APP_NAME()
    FROM DELETED D;
END
GO
## fine

## schema script create per tabelle TE_ (eventi)
-- ===========================================
-- DROP OGGETTI SE ESISTENTI (ORDER: MAIN TABLE, INDEX)
-- ===========================================

IF OBJECT_ID('CFG.<TE_NOME_TABELLA>', 'U') IS NOT NULL DROP TABLE CFG.<TE_NOME_TABELLA>;

-- ===========================================
-- CREAZIONE TABELLA DI TRACKING OPERAZIONI UTENTE (EVENTI)
-- ===========================================

CREATE TABLE CFG.<TE_NOME_TABELLA> (
    CREATE TABLE CFG.TE_USERSESSION (
    ID_USERSESSION    INT IDENTITY(1,1) PRIMARY KEY,
    ID_USER           UNIQUEIDENTIFIER NOT NULL,
    TMS_OPERAZIONE    DATETIME NOT NULL DEFAULT GETDATE(),
    DES_OPERAZIONE    VARCHAR(50) NOT NULL, -- es: LOGIN, LOGOUT, CREATE, UPDATE, DELETE, RESET_PASSWORD, ACTIVATE, DEACTIVATE
    DES_DETTAGLIO     VARCHAR(255) NULL,    -- dettagli aggiuntivi sull'operazione
    NOM_HOST          VARCHAR(128) NULL,
    DES_SESSION       VARCHAR(128) NULL
)
## regola di nomenclatura per le tabelle TR_ (relazioni)
-- ===========================================
-- DROP OGGETTI SE ESISTENTI (ORDER: MAIN TABLE, INDEX)
-- ===========================================

IF OBJECT_ID('CFG.<TR_NOME_TABELLA>', 'U') IS NOT NULL DROP TABLE CFG.<TR_NOME_TABELLA>;

IF EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'IN_<TR_NOME_TABELLA>' AND object_id = OBJECT_ID('CFG.<TR_NOME_TABELLA>'))
    DROP INDEX IN_<TR_NOME_TABELLA> ON CFG.<TR_NOME_TABELLA>;

-- ===========================================
-- CREAZIONE TABELLA DI RELAZIONE MENU_ACTION_UTENTE
-- ===========================================

CREATE TABLE CFG.<TR_NOME_TABELLA> (
    ID_<ta_tabella_1>           INT    NOT NULL,
    ID_<ta_tabella_2>           INT    NOT NULL,
    ID_<ta_tabella_3>           INT    NOT NULL,
     -- altri campi specifici...
    FLG_DELETE      BIT         NOT NULL DEFAULT 0,
    FLG_ACTIVE      BIT         NOT NULL DEFAULT 1,
    FLG_VISIBLE     BIT         NOT NULL DEFAULT 1,
    ID_USER_INSERT      INT    NOT NULL,
    TMS_INSERT          DATETIME            NOT NULL DEFAULT GETDATE(),
    ID_USER_UPDATE      INT    NULL,
    TMS_UPDATE          DATETIME            NULL,
    ID_USER_DELETE      INT    NULL,
    TMS_DELETE          DATETIME            NULL,
    CONSTRAINT PK_<TR_NOME_TABELLA> PRIMARY KEY ( ID_<ta_tabella_1> ,  ID_<ta_tabella_2> ,  ID_<ta_tabella_3> )
);

CREATE INDEX IN_<TR_NOME_TABELLA> ON CFG.<TR_NOME_TABELLA> ( ID_<ta_tabella_1> ,  ID_<ta_tabella_2> ,  ID_<ta_tabella_3> );

##fine 