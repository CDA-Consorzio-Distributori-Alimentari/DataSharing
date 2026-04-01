# Deploy Server DataSharing

La cartella `deploy` viene popolata automaticamente dallo script:

```powershell
.\build_exe.ps1
```

Contenuto del pacchetto da copiare sul server:

- `datasharing.exe`
- `datasharing_windows.exe`
- `config.json`, se presente nel progetto al momento della build
- `config.local.json`, se presente nel progetto al momento della build
- `config.template.json`
- `README_DEPLOY.md`

Regole operative:

- `datasharing.exe`, `datasharing_windows.exe` e `config.json` devono stare nella stessa cartella sul server
- `config.local.json` e opzionale e sovrascrive i valori di `config.json`
- `artifacts_root_path` deve puntare alla share corretta, normalmente `\\cdabackup\DataSharing`

Prerequisiti minimi sul server:

- accesso al database SQL Server configurato in `config.json`
- driver ODBC SQL Server installato
- accesso di rete a `\\cdabackup\DataSharing`
- raggiungibilita SMTP verso `spamfight.mdsnet.it:26`
- raggiungibilita FTP o altri endpoint previsti dai data sharing configurati

Comandi utili:

```powershell
.\datasharing.exe --list-datasharing
.\datasharing.exe --period 202603 --datasharing CC002 --socio 40
.\datasharing_windows.exe
```

Controlli dopo il deploy:

- esecuzione del comando `--list-datasharing`
- presenza del file di log in `\\cdabackup\DataSharing\LOG\data_sharing.log`
- generazione del file atteso in `\\cdabackup\DataSharing\OutPut\<socio>\<datasharing>`
- recap mail verso `dwh@cdaweb.it`