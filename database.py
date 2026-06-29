from urllib.parse import urlparse
import logging

from neo4j import GraphDatabase
import streamlit as st

"""
Gerencia a conexão e a execução de queries no Neo4j.
Possui um sistema automático de fallback para lidar com falhas de
roteamento e protocolos diferentes entre conexões locais e na nuvem (Aura DB).
"""

#desabilita logs verbosos do Neo4j driver
logging.getLogger('neo4j').setLevel(logging.WARNING)


def normalize_uri(uri: str) -> str:
    parsed = urlparse(uri)
    if not parsed.scheme:
        return f"bolt://{uri}"
    #se for Aura (neo4j+s), usar neo4j+ssc direto
    if uri.startswith("neo4j+s://"):
        return uri.replace("neo4j+s://", "neo4j+ssc://", 1)
    return uri


def get_fallback_uri(uri: str) -> str | None:
    if uri.startswith("bolt://"):
        return uri.replace("bolt://", "neo4j+s://", 1)
    if uri.startswith("bolt+s://"):
        return uri.replace("bolt+s://", "bolt+ssc://", 1)
    if uri.startswith("neo4j://"):
        return uri.replace("neo4j://", "neo4j+s://", 1)
    if uri.startswith("neo4j+s://"):
        return uri.replace("neo4j+s://", "neo4j+ssc://", 1)
    return None


@st.cache_resource
def get_neo4j_driver(_uri, _user, _password):
    """
    Cria um driver Neo4j com timeouts curtos para evitar retry infinito.
    Parâmetros começam com _ para serem ignorados pelo hash do cache.
    """
    uri = normalize_uri(_uri)
    return GraphDatabase.driver(
        uri, 
        auth=(_user, _password),
        connection_timeout=10,
        connection_acquisition_timeout=10,
    )


def test_connection(uri, auth_user, auth_pass, silent=False):
    """
    Testa conexão ao Neo4j com fallback automático.
    """
    uri = normalize_uri(uri)
    
    # Primeiro tenta o URI original
    try:
        driver = get_neo4j_driver(uri, auth_user, auth_pass)
        driver.verify_connectivity()
        return True
    except Exception as e:
        error_msg = str(e)
        if "Unable to retrieve routing information" in error_msg or "ServiceUnavailable" in error_msg:
            fallback_uri = get_fallback_uri(uri)
            if fallback_uri:
                try:
                    #driver com fallback diretamente sem cache
                    driver = GraphDatabase.driver(
                        fallback_uri, 
                        auth=(auth_user, auth_pass),
                        connection_timeout=10,
                        connection_acquisition_timeout=10,
                    )
                    driver.verify_connectivity()
                    driver.close()
                    return True
                except Exception as fallback_error:
                    if not silent:
                        st.sidebar.error(f"Erro de conexão interno: {fallback_error}")
                    return False
        if not silent:
            st.sidebar.error(f"Erro de conexão interno: {e}")
        return False


def run_cypher(uri, user, password, query, parameters=None):
    uri = normalize_uri(uri)
    try:
        driver = get_neo4j_driver(uri, user, password)
        with driver.session() as session:
            result = session.run(query, parameters)
            return list(result)
    except Exception as e:
        error_msg = str(e)
        if "Unable to retrieve routing information" in error_msg or "ServiceUnavailable" in error_msg:
            fallback_uri = get_fallback_uri(uri)
            if fallback_uri:
                try:
                    #driver com fallback diretamente sem cache
                    driver = GraphDatabase.driver(
                        fallback_uri, 
                        auth=(user, password),
                        connection_timeout=10,
                        connection_acquisition_timeout=10,
                    )
                    with driver.session() as session:
                        result = session.run(query, parameters)
                        driver.close()
                        return list(result)
                except Exception as fallback_error:
                    st.error(f"Erro na execução da Query: {fallback_error}")
                    return None
        st.error(f"Erro na execução da Query: {e}")
        return None
    
def check_db_health(uri, user, password):
    """
    Executa um Health Check detalhado no banco de dados.
    Retorna um dicionário com o status ('online', 'paused', 'offline') e uma mensagem.
    """
    uri_normalizada = normalize_uri(uri)
    is_aura = "neo4j.io" in uri_normalizada.lower()
    
    try:
        #tenta criar o driver e verificar conectividade
        driver = get_neo4j_driver(uri_normalizada, user, password)
        driver.verify_connectivity()
        return {"status": "online", "message": "Banco de dados ativo e operando normalmente!"}
    except Exception as e:
        error_msg = str(e)
        
        #se falhar, tenta o protocolo de fallback antes de dar o diagnóstico final
        fallback_uri = get_fallback_uri(uri_normalizada)
        if fallback_uri:
            try:
                driver_fb = GraphDatabase.driver(
                    fallback_uri, 
                    auth=(user, password),
                    connection_timeout=5,
                    connection_acquisition_timeout=5,
                )
                driver_fb.verify_connectivity()
                driver_fb.close()
                return {"status": "online", "message": "Conectado com sucesso via protocolo de Fallback."}
            except Exception as fb_e:
                error_msg += f" | Fallback Error: {str(fb_e)}"

        #Análise do Erro para detecção de Instância Pausada no Neo4j Aura
        error_msg_lower = error_msg.lower()
        if is_aura and (
            "unable to retrieve routing information" in error_msg_lower or 
            "serviceunavailable" in error_msg_lower or 
            "paused" in error_msg_lower or
            "connection timed out" in error_msg_lower
        ):
            return {
                "status": "paused",
                "message": (
                    " **Banco de Dados Pausado!** Neo4j Aura pausado devido a 3 dias de inatividade "
                )
            }
            
        return {
            "status": "offline",
            "message": f" **Falha de Conexão:** {error_msg}"
        }