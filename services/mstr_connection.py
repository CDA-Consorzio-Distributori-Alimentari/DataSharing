import json
from mstrio.connection import Connection
import os

def get_mstr_connection(env: str = None):
    """
    Recupera la connessione MicroStrategy in base all'ambiente (Sviluppo/Produzione) dal config.json.
    Se env non è specificato, usa il valore di default (Produzione).
    """
    config_path = os.path.join(os.path.dirname(__file__), '..', 'config.json')
    with open(config_path, 'r', encoding='utf-8') as f:
        config = json.load(f)
    strategy_cfg = config.get('StrategyConectionString', {})
    if not strategy_cfg:
        raise ValueError('StrategyConectionString non trovato in config.json')
    # Scegli ambiente
    env = env or config.get('STRATEGY_ENV', 'Produzione')
    env_cfg = strategy_cfg.get(env)
    if not env_cfg:
        raise ValueError(f'Ambiente {env} non trovato in StrategyConectionString')
    # Decodifica password se serve
    password = env_cfg.get('password_enc')
    # Qui puoi aggiungere una vera decodifica se serve
    return Connection(
        base_url=env_cfg['base_url'],
        username=env_cfg['username'],
        password=password,
        project_name=env_cfg['project_name'],
        project_id=env_cfg['project_id']
    )
