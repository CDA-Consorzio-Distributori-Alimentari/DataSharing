import time
from datetime import datetime
from typing import Optional

# Import delle classi e funzioni esterne
from services.mstr_connection import get_mstr_connection
from services.mstr_jobs import list_jobs, JobType, SubscriptionType, SubscriptionStage, SubscriptionState

from mstrio.connection import Connection
from mstrio.distribution_services.subscription.content import Content
from mstrio.project_objects.report import Report
from mstrio.project_objects.document import Document
from mstrio.distribution_services.subscription.ftp_subscription import FTPSubscription
from mstrio.distribution_services.subscription.email_subscription import EmailSubscription
from mstrio.project_objects.content_cache import ContentCache
from mstrio.project_objects.prompt import Prompt
from mstrio.project_objects.dashboard import (
    Dashboard,
    list_dashboards,
    list_dashboards_across_projects
)
from mstrio.project_objects.report import Report

from mstrio.api.documents import *
from mstrio.api.reports import *
from mstrio.distribution_services.subscription.subscription_status import *
from mstrio.distribution_services import *
from mstrio.server import (
    Job, JobStatus, JobType, kill_all_jobs, kill_jobs, list_jobs, ObjectType, PUName, SubscriptionType
)

from mstrio.modeling import ExpressionFormat, Filter, list_filters, SchemaManagement, SchemaUpdateType
# Import corretto per Token.Type
from mstrio.modeling.expression.expression import Token
from mstrio.modeling.expression.expression import ExpressionNode
from mstrio.connection import Connection
from mstrio.modeling.filter import Filter
from database.repositories.td_rpt_socio_periodo_repository import TdRptSocioPeriodoRepository

class DataSharingStrategyManager:
    def get_enabled_entities(self, option):
        """
        Returns a list of enabled entities (entità) for the given data sharing option.
        """
        
        repo = TdRptSocioPeriodoRepository(self.db_utils)
        df = repo.get_relations_dataframe(datasharing_code=option.code, only_enabled=True, only_current_tool=True)
        # Return as list of dicts with code and name for UI
        return [
            {"code": row["TC_Soci_Codice"], "name": row["TC_Soci_Ragione_Sociale"]}
            for _, row in df.iterrows()
        ]
    def __init__(self, db_utils, myLogger, strategy_env=None):
        self.db_utils = db_utils
        self.myLogger = myLogger
        self.strategy_env = strategy_env or "Produzione"

    #OK 2
    def manage_sottoscrizione_mstrio(self, cod_sottoscrizione: str, cod_tipo: str = "MAIL") -> Optional[str]:
        """
        Aggiorna la sottoscrizione MSTR e ritorna il codice report aggiornato.
        """
        conn = get_mstr_connection(self.strategy_env)
        try:
            if cod_tipo.strip().upper() == "FTP":
                sub = FTPSubscription(connection=conn, id=cod_sottoscrizione)
            else:
                sub = EmailSubscription(connection=conn, id=cod_sottoscrizione)

            if sub is None or sub.contents is None:
                raise ValueError(f"Subscription {cod_sottoscrizione} non trovata o senza contenuti.")

            report_contents = sub.contents
            if not report_contents:
                raise ValueError("Nessun report trovato nella subscription.")
            if len(report_contents) > 1:
                raise ValueError(f"Più report trovati nella sottoscrizione {cod_sottoscrizione}: {', '.join([c.name for c in report_contents])}")
            content_to_update = report_contents[0]
            cod_rpt = getattr(content_to_update, 'id', None)
            self.aggiorna_TA_SOTTOSCRIZIONI_RPT(content_to_update, cod_sottoscrizione)
            self.myLogger.log(f"Report aggiornato per sottoscrizione {cod_sottoscrizione}")
            return cod_rpt
        finally:
            conn.close()
    #OK 3
    def lancia_sottoscrizioni_socio(self) -> None:
        """
        Lancia la schedulazione delle sottoscrizioni socio (EMAIL).
        """
        try:
            self.myLogger.log("Inizio elaborazione dalla coda.")
            df_TA_SOTTOSCRIZIONI_RPT = self.leggo_TA_SOTTOSCRIZIONI_RPT()
            if df_TA_SOTTOSCRIZIONI_RPT is None or df_TA_SOTTOSCRIZIONI_RPT.empty:
                self.myLogger.log("ESCO: Nessuna sottoscrizione Abilitata.")
                return
            cisonoreportincoda = True
            while cisonoreportincoda:
                cisonoreportincoda = self.manage_running_subscriptions()
                time.sleep(5)
        except Exception as e:
            self.myLogger.log_exception(e)
        finally:
            self.myLogger.log("fine elaborazione dalla coda.")
    
    def lancia_sottoscrizioni(self) -> None:
        """
        Lancia la schedulazione delle sottoscrizioni generali (FTP).
        """
        try:
            self.myLogger.log("Inizio elaborazione dalla coda.")
            ftp_cod_tipo = ""
            df_TA_SOTTOSCRIZIONI_RPT = self.leggo_TA_SOTTOSCRIZIONI_RPT(cod_tipo=ftp_cod_tipo, isgenelar=1)
            if df_TA_SOTTOSCRIZIONI_RPT is None or df_TA_SOTTOSCRIZIONI_RPT.empty:
                self.myLogger.log("ESCO: Nessuna sottoscrizione Abilitata.")
                return
            cisonoreportincoda = True
            while cisonoreportincoda:
                cisonoreportincoda = self.manage_running_subscriptions(mysubscription_type=SubscriptionType.FTP)
                time.sleep(5)
        except Exception as e:
            self.myLogger.log_exception(e)
        finally:
            self.myLogger.log("fine elaborazione dalla coda.")



    def manage_running_subscriptions(self, cod_rpt=None, mysubscription_type : SubscriptionType = SubscriptionType.EMAIL) ->bool:
        cisonoreportincoda = True
        conn = None
        try:
            df_TD_RPT_SOCIO_PERIODO = self.leggo_TD_RPT_SOCIO_PERIODO()
            if df_TD_RPT_SOCIO_PERIODO is None:
                self.myLogger.log("ESCO: Nessuna sottoscrizione in attesa o in elaborazione.")
                return False                                       
            
            db_job_run = df_TD_RPT_SOCIO_PERIODO[df_TD_RPT_SOCIO_PERIODO['COD_STATO'] == 'RUN']

            # Restore catalogo_rpt_ids definition
            df_TA_SOTTOSCRIZIONI_RPT = self.leggo_TA_SOTTOSCRIZIONI_RPT()
            if df_TA_SOTTOSCRIZIONI_RPT is not None and not df_TA_SOTTOSCRIZIONI_RPT.empty:
                catalogo_rpt_ids = set(df_TA_SOTTOSCRIZIONI_RPT['COD_RPT'].values)
            else:
                catalogo_rpt_ids = set()

            conn=get_mstr_connection(self.strategy_env)   
            stra_jobs_run = list_jobs(connection=conn, type = JobType.SUBSCRIPTION, subscription_type= mysubscription_type)

            # --- Improved job state and quadratura logic ---
            if stra_jobs_run is None or len(stra_jobs_run) == 0:
                cisonoreportincoda = self.handle_empty_job_queue(db_job_run, conn, mysubscription_type)
            else:
                # Controllo di quadratura: stra_jobs_run comanda
                job_obj_ids = set(db_job_run['COD_OBJ'].values) if db_job_run is not None else set()
                stra_obj_ids = set([job.object_id for job in stra_jobs_run if hasattr(job, 'object_id')])
                stra_obj_ids = stra_obj_ids & catalogo_rpt_ids
                common_obj_ids = job_obj_ids & stra_obj_ids
                only_db = job_obj_ids - stra_obj_ids
                only_stra = stra_obj_ids - job_obj_ids

                
                for _, row in db_job_run.iterrows():
                    # Verifica se l'id esecuzione è tra gli id dei job attivi in stra_jobs_run
                    trovata = any(job.id == row['COD_ESECUZIONE'] for job in stra_jobs_run if hasattr(job, 'id'))
                    self.myLogger.log(f"📝 ID_SOCIO={row['ID_SOCIO']}, NUM_PERIODO={row['NUM_PERIODO']} trovata_in_stra_jobs_run={trovata}, COD_STATO=RUN")


                self.myLogger.log(f"🔗 Job comuni (presenti in entrambi): {list(common_obj_ids)}")
                self.myLogger.log(f"📦 Solo nel db_job_run: {list(only_db)}")
                self.myLogger.log(f"📦 Solo in stra_jobs_run: {list(only_stra)}")
                self.myLogger.log(f"🔢 Numero job in db_job_run: {len(job_obj_ids)}")
                self.myLogger.log(f"🔢 Numero job in stra_jobs_run: {len(stra_obj_ids)}")
                self.myLogger.log(f"🔢 Numero job comuni: {len(common_obj_ids)}")

                # Aggiorna COD_ESECUZIONE se c'è un solo job comune e COD_ESECUZIONE == 'RUNNNING'
                self.update_common_job_execution(db_job_run, conn, stra_jobs_run, common_obj_ids,mysubscription_type)

                # Aggiorna lo stato dei job che sono solo nel db (non più attivi in strategy)
                for obj_id in only_db:
                    rows = db_job_run[db_job_run['COD_OBJ'] == obj_id]
                    if (mysubscription_type == SubscriptionType.EMAIL):
                        sub: EmailSubscription = self.initialize_email_subscription(conn, row['COD_SOTTOSCRIZIONE'])
                    elif (mysubscription_type == SubscriptionType.FTP):
                        sub: FTPSubscription = self.initialize_ftp_subscription(conn, row['COD_SOTTOSCRIZIONE'])
                    for _, row in rows.iterrows():
                        cod_stato = "ERR" if sub.status.state != SubscriptionState.SUCCESS else "OKS"
                        try:
                            self.myLogger.log(f"📝 Aggiorno a ERR: job solo nel db, obj_id={obj_id}, ID_SOCIO={row['ID_SOCIO']}, NUM_PERIODO={row['NUM_PERIODO']}")
                            self.aggiorna_TD_RPT_SOCIO_PERIODO(
                                id_socio=row['ID_SOCIO'],
                                num_periodo=row['NUM_PERIODO'],
                                cod_sottoscrizione=row['COD_SOTTOSCRIZIONE'],
                                cod_esecuzione='NULL',
                                cod_stato=cod_stato
                            )
                            self.myLogger.log(f"✅ Aggiornato a ERR: job solo nel db, obj_id={obj_id}")
                        except Exception as e:
                            self.myLogger.log_exception(e)
                            self.myLogger.log(f"❌ Errore aggiornamento job solo nel db obj_id={obj_id}: {e}")

                # Logga i job che sono solo in strategy (non presenti nel db)
                for obj_id in only_stra:
                    self.myLogger.log(f"🔎 Job solo in stra_jobs_run, obj_id={obj_id}")

                # Logga i job comuni
                for obj_id in common_obj_ids:                    
                    self.myLogger.log(f"🔎 Job comune attivo, obj_id={obj_id}")

            if df_TD_RPT_SOCIO_PERIODO is None or df_TD_RPT_SOCIO_PERIODO.empty:
                self.myLogger.log("ESCO: Nessuna sottoscrizione in attesa o in elaborazione.")
                cisonoreportincoda = False

            if cisonoreportincoda == False:
                self.myLogger.log("GO: nessuno sta elaborando la coda!!!!!")
                df_ins = df_TD_RPT_SOCIO_PERIODO[(df_TD_RPT_SOCIO_PERIODO['COD_STATO'] == 'INS') & (df_TD_RPT_SOCIO_PERIODO['ID_SOCIO'] != '999')]                
                #NO Elabora solo la prima riga INS
                if df_ins is not None and  not df_ins.empty:
                    row_ins = df_ins.iloc[0]                
                    id_socio = int(row_ins['ID_SOCIO'])
                    num_periodo = int(row_ins['NUM_PERIODO'])
                    cod_sottoscrizione = row_ins['COD_SOTTOSCRIZIONE']
                    cod_rpt = row_ins['COD_OBJ']
                    #dfsch = df_TA_SOTTOSCRIZIONI_RPT[df_TA_SOTTOSCRIZIONI_RPT['COD_SOTTOSCRIZIONE'] == cod_sottoscrizione]
                    #myLogger.log(f"elabora_sottoscrizione_periodo per socio :{id_socio}  periodo: {num_periodo} sottoscrizione: {cod_sottoscrizione}")
                    self.execute_sottoscrizione(cod_sottoscrizione=cod_sottoscrizione, cod_rpt=cod_rpt, cod_socio=id_socio, periodo=num_periodo, mysubscription_type = mysubscription_type) 
                    self.myLogger.log(f"elabora_sottoscrizione_periodo per socio :{id_socio}  periodo: {num_periodo} sottoscrizione: {cod_sottoscrizione}")
                    cisonoreportincoda = True
                else:
                    self.myLogger.log("ESCO: Nessuna sottoscrizione in attesa di elaborazione.")
                    cisonoreportincoda = False
        finally:        
            if conn is not None:
                conn.close()
        return cisonoreportincoda
        return cisonoreportincoda

    def update_common_job_execution(self, db_job_run, conn, stra_jobs_run, common_obj_ids, mysubscription_type : SubscriptionType):
        if len(common_obj_ids) == 1:
            obj_id = next(iter(common_obj_ids))
            job_found = next((job for job in stra_jobs_run if hasattr(job, 'object_id') and job.object_id == obj_id), None)
            if job_found:
                rows = db_job_run[(db_job_run['COD_OBJ'] == obj_id) & (db_job_run['COD_ESECUZIONE'] == 'RUNNING')]
                for _, row in rows.iterrows():
                    try:
                        self.myLogger.log(f"🔄 Inizializzo EmailSubscription per COD_SOTTOSCRIZIONE={row['COD_SOTTOSCRIZIONE']} (job comune)")
                        if (mysubscription_type == SubscriptionType.EMAIL):
                            sub: EmailSubscription = self.initialize_email_subscription(conn, row['COD_SOTTOSCRIZIONE'])
                        elif (mysubscription_type == SubscriptionType.FTP):
                            sub: FTPSubscription = self.initialize_ftp_subscription(conn, row['COD_SOTTOSCRIZIONE'])
                        self.myLogger.log(f"📝 Aggiorno TD_RPT_SOCIO_PERIODO: ID_SOCIO={row['ID_SOCIO']}, NUM_PERIODO={row['NUM_PERIODO']}, COD_SOTTOSCRIZIONE={row['COD_SOTTOSCRIZIONE']}, COD_ESECUZIONE={job_found.id}, COD_STATO=RUN")
                        self.aggiorna_TD_RPT_SOCIO_PERIODO(
                                    id_socio=row['ID_SOCIO'],
                                    num_periodo=row['NUM_PERIODO'],
                                    cod_sottoscrizione=row['COD_SOTTOSCRIZIONE'],
                                    cod_esecuzione=job_found.id,
                                    cod_stato='RUN'
                                )
                        self.myLogger.log(f"✅ Aggiornato COD_ESECUZIONE a {job_found.id} per job comune obj_id={obj_id}")
                    except Exception as e:
                        self.myLogger.log_exception(e)
                        self.myLogger.log(f"❌ Errore aggiornamento job comune obj_id={obj_id}: {e}")

    def handle_empty_job_queue(self, db_job_run, conn, mysubscription_type : SubscriptionType) -> bool: 
        if db_job_run is None or db_job_run.empty:
            self.myLogger.log("✅ Code vuote: nessun job in esecuzione su DB o Strategy. Procedo.")
            return False
        else:
            self.myLogger.log("⚠️ Quadratura: jobs in RUN su DB ma non in Strategy. Aggiorno a ERR.")
            for _, row in db_job_run.iterrows():
                try:
                    self.myLogger.log(f"🔄 Inizializzo EmailSubscription per COD_SOTTOSCRIZIONE={row['COD_SOTTOSCRIZIONE']}")
                    
                    if (mysubscription_type == SubscriptionType.EMAIL):
                            sub: EmailSubscription = self.initialize_email_subscription(conn, row['COD_SOTTOSCRIZIONE'])
                    elif (mysubscription_type == SubscriptionType.FTP):
                            sub: FTPSubscription = self.initialize_ftp_subscription(conn, row['COD_SOTTOSCRIZIONE'])
                    self.myLogger.log(f"Status: {getattr(sub.status, 'state', None)}, Stage: {getattr(sub.status, 'stage', None)}")
                    cod_stato = "ERR" if sub.status.state != SubscriptionState.SUCCESS else "OKS"
                    self.myLogger.log(f"📝 Aggiorno TD_RPT_SOCIO_PERIODO: ID_SOCIO={row['ID_SOCIO']}, NUM_PERIODO={row['NUM_PERIODO']}, COD_SOTTOSCRIZIONE={row['COD_SOTTOSCRIZIONE']}, COD_ESECUZIONE=NULL, COD_STATO={cod_stato}")
                    self.aggiorna_TD_RPT_SOCIO_PERIODO(
                                id_socio=row['ID_SOCIO'],
                                num_periodo=row['NUM_PERIODO'],
                                cod_sottoscrizione=row['COD_SOTTOSCRIZIONE'],
                                cod_esecuzione='NULL',
                                cod_stato=cod_stato
                            )
                except Exception as e:
                    self.myLogger.log_exception(e)
                    self.myLogger.log(f"❌ Errore aggiornamento job DB: {e}")
            return False
        
    #OK
    def execute_sottoscrizione(self, cod_sottoscrizione, cod_rpt,  cod_socio, periodo, mysubscription_type : SubscriptionType):
        found_job1 = None  # Ensure variable is always defined
        self.modificaFiltro(cod_socio, periodo)
        try:
            conn = get_mstr_connection(self.strategy_env)
            sub = self.initialize_email_subscription(conn, cod_sottoscrizione)

            if (mysubscription_type == SubscriptionType.EMAIL):
                sub: EmailSubscription = self.initialize_email_subscription(conn, cod_sottoscrizione)
                sub.alter(email_subject=f"Chiusura Socio {cod_socio} per il periodo {periodo}", filename=f"chiusura_{cod_socio}_{periodo}")
            elif (mysubscription_type == SubscriptionType.FTP):
                sub: FTPSubscription = self.initialize_ftp_subscription(conn, cod_sottoscrizione)
                sub.alter(filename = f"Estrazione CDA {periodo}")   
            
            sub.fetch()
            self.aggiorna_TD_RPT_SOCIO_PERIODO(
                id_socio=cod_socio,
                num_periodo=periodo,
                cod_sottoscrizione=cod_sottoscrizione,
                cod_esecuzione= self.COD_ESECUZIONE,
                cod_stato='RUN'
            )
            self.myLogger.log(f"[Chiusura Socio {cod_socio} per il periodo {periodo}] Stato iniziale RUN e esecuzione avviata.")
            sub.execute()
            giro = 0
            while (sub.status.stage != SubscriptionStage.EXECUTING or found_job1 is None) and giro < 10:
                sub.fetch()                
                giro += 1
                running_jobs1 = list_jobs(
                    connection=conn,
                    type=JobType.SUBSCRIPTION,
                    subscription_type= mysubscription_type,
                    object_id=cod_rpt
                )
                for job in running_jobs1:
                    if hasattr(job, 'object_id') and job.object_id == cod_rpt:
                        found_job1 = job
                        self.myLogger.log(f"[Chiusura Socio {cod_socio} per il periodo {periodo}] 🔎 Job trovato con object_id == cod_rpt: id={job.id}, object_id={job.object_id}, stato={getattr(job, 'status', None)}")
                        break
                if found_job1 is None:
                    time.sleep(5)

            # Nuova logica: solo se sub.status.stage == EXECUTING e found_job1 è stato trovato è tutto ok
            if sub.status.stage == SubscriptionStage.EXECUTING and found_job1 is not None:
                cod_stato = "RUN"
                cod_esecuzione = found_job1.id
                self.myLogger.log(f"[Chiusura Socio {cod_socio} per il periodo {periodo}] ✅ Sottoscrizione in esecuzione: stage EXECUTING e job trovato. id={found_job1.id}")
            else:
                cod_stato = "RUN"
                cod_esecuzione = found_job1.id if found_job1 is not None else self.COD_ESECUZIONE
                self.myLogger.log(f"[Chiusura Socio {cod_socio} per il periodo {periodo}] ❌ Errore: stage={sub.status.stage}, job trovato={found_job1 is not None}")

            self.repo.aggiorna_TD_RPT_SOCIO_PERIODO(
                id_socio=cod_socio,
                num_periodo=periodo,
                cod_sottoscrizione=cod_sottoscrizione,
                cod_esecuzione=cod_esecuzione,
                cod_stato=cod_stato
            )
            self.myLogger.log(f"[Chiusura Socio {cod_socio} per il periodo {periodo}] Stato aggiornato a {cod_stato} con COD_ESECUZIONE={cod_esecuzione}.")

        except Exception as e:
            self.myLogger.log_exception(e)
            self.repo.aggiorna_TD_RPT_SOCIO_PERIODO(
                id_socio=cod_socio,
                num_periodo=periodo,
                cod_sottoscrizione=cod_sottoscrizione,
                cod_esecuzione="",
                cod_stato='ERR',
                des_error=str(e) if isinstance(e, Exception) else None
            )
            self.myLogger.log(f"[Chiusura Socio {cod_socio} per il periodo {periodo}] ⚠️ Stato aggiornato a 'ERR' per periodo {periodo}")
            raise ValueError(f"Errore durante l'elaborazione del periodo {periodo}: {e}")
        finally:
            conn.close()

        self.myLogger.log(f"[Chiusura Socio {cod_socio} per il periodo {periodo}] ✅ Inserimento storico completato per sottoscrizione {cod_sottoscrizione} ({cod_rpt})  per il periodo {periodo}.")
   
    #OK
    def initialize_email_subscription(self, conn: Connection, cod_sottoscrizione: str) -> EmailSubscription:
                
        sub = EmailSubscription(connection=conn, id=cod_sottoscrizione)
         
        if sub is None or sub.contents is None:
            raise ValueError(f"Subscription {cod_sottoscrizione} non trovata o senza contenuti.")
        report_contents = sub.contents
            
        if not report_contents: 
            raise ValueError(f"Nessun report trovato nella subscription {cod_sottoscrizione}.")
        if len(report_contents) > 1:
                # Se ci sono più report con lo stesso ID, lancia un'eccezione   
            raise ValueError(f"Più report trovati nella sottoscrizione {cod_sottoscrizione} : {', '.join([c.name for c in report_contents])}")
        content_to_update = report_contents[0]
        if not content_to_update:
            raise ValueError(f"Nessun contenuto nella sottoscrizione {cod_sottoscrizione}.")
        
        return sub
    
    #OK
    def initialize_ftp_subscription(self, conn: Connection, cod_sottoscrizione: str) -> FTPSubscription:
                
        sub = FTPSubscription(connection=conn, id=cod_sottoscrizione)
         
        if sub is None or sub.contents is None:
            raise ValueError(f"Subscription {cod_sottoscrizione} non trovata o senza contenuti.")
        report_contents = sub.contents
            
        if not report_contents: 
            raise ValueError(f"Nessun report trovato nella subscription {cod_sottoscrizione}.")
        if len(report_contents) > 1:
                # Se ci sono più report con lo stesso ID, lancia un'eccezione   
            raise ValueError(f"Più report trovati nella sottoscrizione {cod_sottoscrizione} : {', '.join([c.name for c in report_contents])}")
        content_to_update = report_contents[0]
        if not content_to_update:
            raise ValueError(f"Nessun contenuto nella sottoscrizione {cod_sottoscrizione}.")
        
        return sub

    def modificaFiltro(self, codsocio: str, periodo: str):
        conn: Connection = get_mstr_connection()
        try:
            FILTER_ID_MESE = '6BAA7F28E84B77EEFFAA6DB09D070452'  # Insert ID of existing filter here
            FILTER_ID_SOCIO = 'D6520537C74D45DBFE72B8BA067F9B17'

            # Get specific filter by id with expressions represented as trees (default)
            self.SetFilter(conn, FILTER_ID_MESE, 'Mese (ID) = ', nuovovalore=periodo)
            self.SetFilter(conn, FILTER_ID_SOCIO, 'Socio (Socio) =', nuovovalore=codsocio)

            schema_manager = SchemaManagement(connection=conn, project_id=conn.project_id)
            task = schema_manager.reload(update_types=[SchemaUpdateType.LOGICAL_SIZE])
        except Exception as ex:
            print(ex)
        finally:
            conn.close()

    def SetFilter(self, conn: Connection, FILTER_ID: str, filtro: str, nuovovalore):
        """
        Modifica un filtro MSTR dato l'ID, la stringa filtro e il nuovo valore.
        """


        filter_obj: Filter = Filter(connection=conn, id=FILTER_ID, show_filter_tokens=False)
        print(filter_obj.qualification)
        newqualification = filter_obj.qualification
        newtree: ExpressionNode = newqualification.tree
        newqualification.text = f'{filtro}{nuovovalore}'
        newtree.predicate_text = f'{filtro}{nuovovalore}'
        if hasattr(newtree, 'parameters') and newtree.parameters:
            newtree.parameters[0].constant.value = nuovovalore

        filter_obj.qualification = newqualification
        filter_obj.alter(qualification=newqualification, comments="test di prova")
        filter_obj.fetch()  # aggiorna l'oggetto filter locale con i dati reali dal server
        print(filter_obj.qualification)

        # filter : Filter= Filter(connection=conn, id=FILTER_ID, show_filter_tokens=False)
        # print(filter.qualification)
        # newqualification = filter.qualification
        # newtree : ExpressionNode = newqualification.tree
        # newqualification.text = f'{filtro}{nuovovalore}'
        # newtree.predicate_text = f'{filtro}{nuovovalore}'
        # newtree.parameters[0].constant.value = nuovovalore
        
        # from mstrio.modeling.expression import Expression
        # filter.qualification = newqualification                
        # filter.alter(qualification=newqualification, comments="test di prova")
        # filter.fetch()  # aggiorna l'oggetto filter locale con i dati reali dal server
        # print(filter.qualification)