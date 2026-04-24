# Guida Operativa Utente DataSharing

## Cos'e il programma

Il programma serve a:

- generare il file richiesto per uno specifico data sharing
- salvare il file nella cartella condivisa aziendale
- inviare il file al destinatario configurato
- opzionalmente inviare una mail finale di recap, se il flag dedicato e attivo

Puoi creare questi flussi in tre modi diversi:
1. partendo dal data sharing e scegliendo i soci
2. partendo dal socio e scegliendo i data sharing
3. tramite la modalità strategy

## Cosa viene consegnato all'utente

L'utente riceve una cartella gia pronta con questi file:
- `datasharing_windows.exe`
- `config.json`
- `GUIDA_UTENTE_DATASHARING.md`

Il file `config.json` deve rimanere nella stessa cartella degli eseguibili.

## Dove puo essere copiato

Il programma va copiato sul tuo PC, ad esempio sul Desktop o nella cartella Documenti.

Esempi di cartelle adatte:

- `C:\Users\<nome utente>\Desktop\DataSharing`
- `C:\Users\<nome utente>\Documents\DataSharing`

Importante:

- copiare sempre tutta la cartella, non solo l'exe
- non separare `datasharing_windows.exe` da `config.json`
- non separare `datasharing.exe` da `config.json`
- non rinominare i file di configurazione

## Requisito importante: utente di dominio

Per poter usare correttamente il programma, l'utente che lo avvia deve essere un utente di dominio autorizzato.

In pratica il programma funziona se:

1. il PC e collegato al dominio aziendale e l'utente ha fatto accesso con il proprio utente di dominio
2. oppure il programma viene avviato con `Esegui come altro utente` usando un utente di dominio autorizzato

Se il PC non è in dominio, oppure il programma viene lanciato con un utente non autorizzato, l'elaborazione non parte.

Se non sai se il tuo utente è autorizzato, chiedi agli amministratori di sistema.

## Come capire quale file usare

Nella cartella consegnata sono presenti due eseguibili:

- `datasharing_windows.exe`: versione con finestra grafica, uso consigliato
- `datasharing.exe`: versione a riga di comando

Se non hai un'esigenza specifica, usa sempre `datasharing_windows.exe`.

## Avvio normale del programma

Se sei gia entrato in Windows con il tuo utente aziendale di dominio:

1. apri la cartella dove hai il programma
2. fai doppio clic su `datasharing_windows.exe`
3. attendi l'apertura della finestra

Se il programma si apre normalmente, puoi usarlo.

## Come usare il programma con Run As

Se il PC non è aperto con l'utente di dominio corretto, oppure devi usare un altro utente aziendale autorizzato, puoi avviare il programma come altro utente.

Su Windows il comando si chiama di solito `Esegui come altro utente`.

Passi da seguire:

1. vai nella cartella dove si trova `datasharing_windows.exe`
2. tieni premuto il tasto `Shift` sulla tastiera
3. mentre tieni premuto `Shift`, fai clic con il tasto destro su `datasharing_windows.exe`
4. scegli `Esegui come altro utente`
5. inserisci l'utente di dominio nel formato aziendale richiesto, per esempio `CDA\nome.cognome` oppure `nome.cognome@cdaweb.it`
6. inserisci la password
7. premi `OK`

Se tutto e corretto, il programma si aprira usando quell'utente.

## Se non vedi la voce Esegui come altro utente

Su alcuni PC la voce non compare subito.

In questo caso prova cosi:

1. tieni premuto `Shift`
2. fai clic destro sul file
3. controlla se compare `Esegui come altro utente`

Se ancora non compare, chiedi supporto al reparto IT o a chi gestisce il PC.

## Come usare la versione con finestra grafica

Aprendo `datasharing_windows.exe` compare una finestra guidata.

L'uso normale e questo:

1. scegliere il data sharing dalla lista
2. scegliere se il periodo e annuale (`YYYY`) oppure mensile (`YYYYMM`)
3. inserire il periodo
4. selezionare uno o piu soci abilitati
5. premere `Avvia elaborazione`

La finestra mostra anche:

- l'avanzamento percentuale
- il dettaglio passo per passo dell'elaborazione
- l'esito finale per ogni socio

Se il periodo non e corretto, il programma mostra un messaggio.

## Significato del periodo

Il periodo puo essere scritto in due modi:

- `YYYYMM` per un singolo mese, per esempio `202603`
- `YYYY` per un intero anno, per esempio `2026`

Esempi:

- `202603` significa marzo 2026
- `2026` significa tutto l'anno 2026

## Quando usare il flag MAIL RECAP

Nella finestra principale puo essere presente il flag `MAIL RECAP`.

Questo flag serve per attivare o disattivare la mail interna di riepilogo.

Regola pratica:

- se il flag e spento, nessuna mail di recap viene inviata
- se il flag e acceso, viene inviata la mail di recap

Per le elaborazioni annuali viene inviata una sola mail complessiva per socio, non una mail per ogni mese.

## Dove vengono salvati i file

La cartella condivisa aziendale usata dal programma e:

```text
\\cdabackup\DataSharing
```

Le cartelle principali sono:

- `\\cdabackup\DataSharing\LOG`
- `\\cdabackup\DataSharing\OutPut`
- `\\cdabackup\DataSharing\querysql`
- `\\cdabackup\DataSharing\templatexml`

Per l'utente finale sono importanti soprattutto:

- `LOG`: contiene il file di log
- `OutPut`: contiene i file prodotti

## Dove trovare il file generato

I file prodotti vengono salvati in:

```text
\\cdabackup\DataSharing\OutPut\<codice socio>\<codice data sharing>
```

Esempio:

```text
\\cdabackup\DataSharing\OutPut\7\CC002
```

Quindi, se elabori il socio `7` per il data sharing `CC002`, il file finale sara in quella cartella.

## Cosa succede durante l'elaborazione

Quando il programma parte:

1. controlla automaticamente se l'utente che lo sta eseguendo e' autorizzato
2. controlla se il socio è abilitato al data sharing richiesto
3. genera il file
4. salva il file nella cartella condivisa
5. prova a pubblicarlo o inviarlo sul canale previsto
6. se il recap e attivo, invia anche la mail finale di riepilogo

Se il socio non è abilitato, l'elaborazione non prosegue.

## Come leggere il nome del file

Il nome del file dipende dal data sharing configurato.

In alcuni casi il processo di invio produce anche un file con estensione `.ok`.

Se non lo vedi nella tua cartella, non significa necessariamente che manchi, perchè prodotto nella destinazione utente


## La mail di recap

La mail di riepilogo interno e opzionale ed e disattivata di default.

Quando il flag `MAIL RECAP` e attivo, la mail arriva alla casella:

- `dwh@cdaweb.it`

Importante:

- l'esito `OK` arriva solo se il file e' stato consegnato con esito positivo
- se c'e un errore di generazione o di invio, viene inviata una mail con oggetto `ERRORE` anche se il flag `MAIL RECAP` non e' attivo
- in modalita `DEBUG` la mail di recap non viene inviata

La mail riporta:

- esito finale `OK` oppure `KO`
- codice e nome del data sharing
- codice e nome del socio
- periodo elaborato
- modalita di invio
- destinatario o destinazione dell'invio
- elenco dei file inviati
- percorso locale del file salvato
- messaggio finale del processo

## Come capire se e andato tutto bene

Di norma e tutto corretto quando:

1. il programma termina senza errori
2. il file compare nella cartella `\\cdabackup\DataSharing\OutPut\...`
3. se la mail di recap arriva con esito `OK`, significa che il file e' stato consegnato con esito positivo
4. se arriva una mail con oggetto `ERRORE`, significa che l'elaborazione o l'invio non sono andati a buon fine

## Come capire se il file e stato inviato

Per capire se il file e' stato davvero inviato, non basta vedere il file nella cartella `OutPut`.

Il file nella cartella `OutPut` significa che il file e' stato creato.

Per considerarlo anche inviato correttamente, controlla almeno uno di questi punti:

1. se la mail di recap e' attiva, la mail arriva con esito `OK`
3. se arriva una mail con oggetto `ERRORE`, nel corpo trovi i dettagli del problema.
2. controlla che non ci siano errori nel log applicativo \\cdabackup\DataSharing\Log

## Cosa controllare se qualcosa non va

Controllare in questo ordine:

1. di aver aperto il programma con un utente autorizzato
2. che il codice socio sia corretto
3. che il periodo sia corretto
4. che il codice data sharing sia corretto
5. che il file sia presente nella cartella condivisa
6. controlla se e arrivata una mail di recap `OK` oppure una mail con oggetto `ERRORE`
7. se la mail e presente, leggi il messaggio e i dettagli dell'errore

Se la mail riporta `KO`, oppure il file non compare, controllare anche il log applicativo in:

```text
\\cdabackup\DataSharing\LOG\data_sharing.log
```

## Problemi frequenti

### Il programma non si apre o dice che non sei autorizzato

Cause possibili:

- non sei entrato in Windows con il tuo utente di dominio
- stai usando un PC non in dominio
- hai aperto il programma con un utente locale del PC
- non fai parte del gruppo autorizzato

Cosa fare:

1. chiudi il programma
2. prova ad aprirlo con `Esegui come altro utente`
3. usa il tuo utente di dominio autorizzato
4. se il problema continua, contatta il supporto IT

### Il file c'e ma non sembra inviato

In questo caso il file puo essere stato creato correttamente ma non pubblicato. Se la mail di recap e attiva, la mail indica a chi e stato inviato oppure segnala che la pubblicazione non e stata eseguita.

Se arriva una mail con oggetto `ERRORE`, controlla i dettagli presenti nel corpo della mail e poi verifica il log.

### Non trovo il file

Controlla prima la cartella del socio e poi quella del data sharing dentro:

```text
\\cdabackup\DataSharing\OutPut
```

Se il file non c'e, l'elaborazione potrebbe non essere arrivata alla fine.

### Ho copiato il programma sul mio PC ma non parte

Controlla questi punti:

1. hai copiato tutta la cartella, non solo l'exe
2. `config.json` è nella stessa cartella dell'exe
3. il PC è in dominio oppure hai usato `Esegui come altro utente`
4. l'utente usato è autorizzato

## Quando chiedere aiuto

Chiedi supporto quando:

- il programma segnala utente non autorizzato
- il file non viene creato
- il file non compare nella cartella condivisa
- la mail di recap manca quando dovrebbe arrivare
- non riesci a usare `Esegui come altro utente`
- il socio o il data sharing elaborati non sono quelli attesi