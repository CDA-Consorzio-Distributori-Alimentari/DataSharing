# Guida Operativa Utente DataSharing

Questa guida e pensata per un utente non tecnico che deve lanciare il programma, controllare i file prodotti e leggere la mail finale di recap.

## Dove si trova l'eseguibile

L'applicazione puo essere distribuita anche come eseguibile Windows:

```text
datasharing.exe
```

Quando viene consegnata in formato exe, il file `config.json` deve stare nella stessa cartella dell'eseguibile.

## A cosa serve

Il programma DataSharing:

- genera il file richiesto per uno specifico data sharing
- salva il file nella cartella condivisa aziendale
- invia il file al destinatario configurato
- manda una mail finale di recap con il riepilogo dell'operazione

## Come lanciare il programma

Per eseguire il programma servono tre informazioni:

- `--socio`: codice socio
- `--period`: periodo da elaborare
- `--datasharing`: codice del data sharing

Comando tipo:

```powershell
datasharing.exe --period 2026 --datasharing CC002 --socio 7
```

Con questo comando il programma elabora il socio `7`, per il data sharing `CC002`, sul periodo `2026`.

Il periodo puo essere scritto in due modi:

- `YYYYMM` per un singolo mese, ad esempio `202603`
- `YYYY` per un intero anno, ad esempio `2026`

Esempio su un solo mese:

```powershell
datasharing.exe --period 202603 --datasharing CC001 --socio 7
```

Per vedere l'elenco dei data sharing disponibili:

```powershell
datasharing.exe --list-datasharing
```

Il comando mostra codice, nome e tipo file di ogni data sharing.

## Come creare l'exe

Per generare l'eseguibile dal progetto Python usare questo comando dalla cartella del progetto:

```powershell
.\build_exe.ps1
```

Al termine viene creata la cartella `dist` con:

- `datasharing.exe`
- `config.template.json`
- `config.json`, se presente in fase di build

## Dove vengono salvati i file

La cartella condivisa degli artefatti e:

```text
\\cdabackup\DataSharing
```

Questa cartella corrisponde alla root `DataSharingShare` usata dal programma.

All'interno si trovano queste sottocartelle principali:

- `\\cdabackup\DataSharing\LOG`
- `\\cdabackup\DataSharing\OutPut`
- `\\cdabackup\DataSharing\querysql`
- `\\cdabackup\DataSharing\templatexml`

Significato delle cartelle:

- `LOG`: contiene il file di log dell'applicazione
- `OutPut`: contiene i file generati per soci e data sharing
- `querysql`: contiene le istruzioni che dicono al programma quali dati leggere dal database
- `templatexml`: contiene il modello usato per costruire il file XML finale

Il mapping, in pratica, dice quali dati finiscono nei vari campi del file finale.

Esempio semplice: un valore letto dal database viene riportato nel campo corrispondente del file XML.

## Dove trovare il file generato

I file prodotti vengono salvati in:

```text
\\cdabackup\DataSharing\OutPut\<codice socio>\<codice data sharing>
```

Esempio reale:

```text
\\cdabackup\DataSharing\OutPut\7\CC002
```

Quindi, dopo il lancio, per il socio `7` e il data sharing `CC002`, il file sara dentro quella cartella.

## Come leggere il nome del file

Il nome del file dipende dal data sharing configurato.

Per esempio, nei flussi Coca Cola il nome contiene di solito:

- codice wholesaler
- mese del periodo
- anno del periodo
- numero del flusso

In alcuni casi, oltre al file principale, nella cartella puo comparire anche un secondo file con estensione `.ok`.


## Cosa succede dopo il lancio

Quando il comando parte, il programma verifica nella tabella `TC_Soci` se il socio e abilitato al data sharing richiesto. Se il socio non risulta abilitato, l'elaborazione non prosegue. Se invece e abilitato, il programma genera il file, lo salva nella cartella condivisa, lo invia e manda una mail finale di recap.

Alcuni esempi di campi usati per questa verifica sono:

- `TC_Soci_CocaCola_Attivo`
- `TC_Soci_CocaCola_In_Chiaro`
- `TC_Soci_DIAGEO_Attivo`

In pratica, se il campo collegato al data sharing vale `1`, il socio e abilitato. Se vale `0`, non e abilitato.

## La mail di recap

Alla fine di ogni elaborazione viene inviata una mail di riepilogo interno.

La mail di recap arriva alla casella:

- `dwh@cdaweb.it`

## Cosa contiene la mail di recap

La mail riporta:

- esito finale: `OK` oppure `KO`
- codice e nome del data sharing
- codice e nome del socio
- periodo elaborato
- modalita di invio
- destinatario o destinazione dell'invio
- elenco dei file inviati
- percorso locale del file salvato
- messaggio finale del processo

L'oggetto della mail contiene:

- nome del data sharing
- codice socio
- nome socio

## Come capire se e andato tutto bene

Di norma l'elaborazione e corretta quando:

1. il comando termina senza errori
2. il file compare nella cartella `\\cdabackup\DataSharing\OutPut\...`
3. arriva la mail di recap
4. nella mail il risultato e `OK`

## Cosa controllare se qualcosa non va

Se l'elaborazione non produce il risultato atteso, controllare in questo ordine:

1. che il codice socio sia giusto
2. che il periodo sia corretto
3. che il codice data sharing sia corretto
4. che il file sia presente nella cartella condivisa
5. che sia arrivata la mail di recap
6. che la mail riporti `OK`

Se la mail riporta `KO`, controllare anche il log applicativo in:

```text
\\cdabackup\DataSharing\LOG\data_sharing.log
```

Se la mail riporta `KO`, oppure il file non compare, usare il recap e le informazioni del log per approfondire il problema.

## Casi frequenti

### Il file c'e ma non sembra inviato

In questo caso il file puo essere stato creato correttamente ma non pubblicato. La mail di recap indica a chi e stato inviato oppure segnala che la pubblicazione non e stata eseguita.

### Sono presenti due file nella cartella

Se nella cartella trovi anche un file `.ok`, e normale e non devi fare nulla.

### Non trovo il file

Controllare prima la cartella del socio e poi quella del data sharing dentro:

```text
\\cdabackup\DataSharing\OutPut
```

Se il file non c'e, l'elaborazione potrebbe non essere arrivata alla fine.

## Quando approfondire il problema

Serve fare ulteriori verifiche quando:

- il recap segnala errore
- il file non viene creato
- il file non compare nella cartella condivisa
- manca la mail finale di recap
- il socio o il data sharing elaborati non sono quelli attesi