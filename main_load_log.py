import os
import re
import sys
import datetime
import socket
import getpass
from database.db_manager import DBManager
from database.repositories.tabella_logging_repository import TabellaLoggingRepository

LOG_PATH = r"\\cdabackup\DataSharing\LOG\data_sharing.log"

# Regex patterns
RE_AVVIO = re.compile(r"Avvio elaborazione per socio (\d+), periodo (\d+), data sharing ([A-Z0-9]+)")
RE_XML = re.compile(r"Generazione artefatto xml in (.+?\.xml)")
RE_STATO = re.compile(r"Elaborazione completata\.")
RE_ERRORE = re.compile(r"ERRORE|ERROR|Exception|Traceback", re.IGNORECASE)
RE_FILE = re.compile(r"file ([^\s]+\.xml)")
RE_FTP = re.compile(r"Upload FTP completato per il file ([^\s]+\.xml)")


def parse_log(log_path):
    """
    Estrae i dati chiave dal log e li raggruppa per ciclo di elaborazione.
    """
    results = []
    current = None
    with open(log_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            # Estrarre timestamp
            try:
                ts_str = line.split(" - ")[0]
                tms_invio = datetime.datetime.strptime(ts_str, "%Y-%m-%d %H:%M:%S,%f")
            except Exception:
                tms_invio = None
            # Avvio
            m = RE_AVVIO.search(line)
            if m:
                if current:
                    results.append(current)
                current = {
                    "cod_socio": m.group(1),
                    "num_periodo": m.group(2),
                    "cod_datasharing": m.group(3),
                    "tms_invio": tms_invio,
                    "nom_file": None,
                    "cod_stato": "OK",
                    "des_errore": None,
                }
                continue
            # File XML
            m = RE_XML.search(line)
            if m and current:
                xml_path = m.group(1)
                current["nom_file"] = os.path.basename(xml_path)
                continue
            # FTP completato
            m = RE_FTP.search(line)
            if m and current:
                current["cod_stato"] = "FTP"
                continue
            # Errore
            if RE_ERRORE.search(line) and current:
                current["cod_stato"] = "ERR"
                current["des_errore"] = line
                continue
            # Elaborazione completata
            if RE_STATO.search(line) and current:
                results.append(current)
                current = None
    if current:
        results.append(current)
    return results

def main():
    db_manager = DBManager()
    repo = TabellaLoggingRepository(db_manager)
    log_entries = parse_log(LOG_PATH)
    utente = getpass.getuser()
    host = socket.gethostname()
    for entry in log_entries:
        entry["nom_utente_operazione"] = utente
        entry["nom_host_operazione"] = host
        entry["tms_update"] = datetime.datetime.now()
        # Default stato
        if not entry.get("cod_stato"):
            entry["cod_stato"] = "OK"
        # Gestione nom_file obbligatorio
        nom_file = entry.get("nom_file")
        if not nom_file:
            entry["nom_file"] = ""
            entry["cod_stato"] = "ERR"
            entry["des_errore"] = "File XML non trovato nel log"
        else:
            # Verifica esistenza file
            if not os.path.exists(nom_file):
                entry["cod_stato"] = "ERR"
                entry["des_errore"] = f"File non trovato: {nom_file}"

        # Chiave primaria
        key_filters = {
            repo.column_mapping["cod_socio"]: entry["cod_socio"],
            repo.column_mapping["cod_datasharing"]: entry["cod_datasharing"],
            repo.column_mapping["num_periodo"]: entry["num_periodo"],
            repo.column_mapping["tms_invio"]: repo._truncate_to_minute(entry["tms_invio"]),
        }
        existing = repo.get_first_by_filters(key_filters)
        if existing:
            # Confronta tutti i valori
            is_equal = True
            for k, v in entry.items():
                db_col = repo.column_mapping.get(k, k)
                if hasattr(existing, db_col):
                    if getattr(existing, db_col, None) != v:
                        is_equal = False
                        break
            if is_equal:
                print(f"Saltato (già presente e identico): {entry}")
                continue
            # Altrimenti aggiorna
            try:
                repo.update_by_filters(key_filters, {repo.column_mapping.get(k, k): v for k, v in entry.items()})
                print(f"Aggiornato: {entry}")
            except Exception as exc:
                print(f"Errore aggiornamento: {entry} -> {exc}", file=sys.stderr)
        else:
            try:
                repo.add_entry(entry)
                print(f"Inserito: {entry}")
            except Exception as exc:
                print(f"Errore inserimento: {entry} -> {exc}", file=sys.stderr)

if __name__ == "__main__":
    main()
