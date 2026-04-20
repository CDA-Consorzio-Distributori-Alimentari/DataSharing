# Wrapper per job MicroStrategy tramite mstrio
from enum import Enum

# Enum per tipo job
class JobType(Enum):
    SUBSCRIPTION = "SUBSCRIPTION"
    # Aggiungi altri tipi se necessario

class SubscriptionType(Enum):
    EMAIL = "EMAIL"
    FTP = "FTP"

class SubscriptionStage(Enum):
    EXECUTING = "EXECUTING"
    # Aggiungi altri stage se necessario

class SubscriptionState(Enum):
    SUCCESS = "SUCCESS"
    # Aggiungi altri stati se necessario

def list_jobs(connection, type=JobType.SUBSCRIPTION, subscription_type=None, object_id=None):
    """
    Wrapper per list_jobs di mstrio. Filtra per tipo, subscription_type e object_id.
    """
    # #jobs = mstrio_list_jobs(connection=connection)
    # filtered = []
    # for job in jobs:
    #     if type and hasattr(job, 'type') and job.type != type.value:
    #         continue
    #     if subscription_type and hasattr(job, 'subscription_type') and job.subscription_type != subscription_type.value:
    #         continue
    #     if object_id and hasattr(job, 'object_id') and job.object_id != object_id:
    #         continue
    #     filtered.append(job)
    # return filtered
