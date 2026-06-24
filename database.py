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