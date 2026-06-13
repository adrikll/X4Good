from neo4j import GraphDatabase
import streamlit as st

@st.cache_resource
def get_neo4j_driver(uri, user, password):
    return GraphDatabase.driver(uri, auth=(user, password))

def test_connection(uri, auth_user, auth_pass):
    try:
        driver = get_neo4j_driver(uri, auth_user, auth_pass)
        driver.verify_connectivity()
        return True
    except Exception as e:
        st.sidebar.error(f"Erro de conexão interno: {e}")
        return False

def run_cypher(uri, user, password, query, parameters=None):
    try:
        driver = get_neo4j_driver(uri, user, password)
        # Deixamos o session() vazio para o Aura usar o banco padrão automaticamente
        with driver.session() as session:
            result = session.run(query, parameters)
            return list(result)
    except Exception as e:
        st.error(f"Erro na execução da Query: {e}")
        return None