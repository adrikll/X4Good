from neo4j import GraphDatabase
import streamlit as st

def test_connection(uri, auth_user, auth_pass):
    try:
        with GraphDatabase.driver(uri, auth=(auth_user, auth_pass)) as driver:
            driver.verify_connectivity()
        return True
    except Exception as e:
        st.sidebar.error(f"Erro de conexão: {e}")
        return False

def run_cypher(uri, user, password, query, parameters=None):
    try:
        with GraphDatabase.driver(uri, auth=(user, password)) as driver:
            with driver.session() as session:
                result = session.run(query, parameters)
                # Retorna a lista de registros puros para preservar os nós e arestas nativos
                return list(result)
    except Exception as e:
        st.error(f"Erro na execução da Query: {e}")
        return None