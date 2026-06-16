import streamlit as st
import database
import components

st.set_page_config(page_title="X4Good Administrator Suite", layout="wide", page_icon="🌐")

st.title("🌐 X4Good Social Media")

if "connected" not in st.session_state:
    st.session_state.connected = False

try:
    #conexão local/nuvem via secrets
    uri = st.secrets["NEO4J_URI"]
    user = st.secrets["NEO4J_USERNAME"]
    password = st.secrets["NEO4J_PASSWORD"]
    database_name = st.secrets["NEO4J_DATABASE"]
    usando_secrets = True

except Exception as e:
    st.write(e)
    usando_secrets = False

st.sidebar.header("Autenticação Neo4j")

if usando_secrets:
    st.sidebar.success("Banco de dados conectado!")
    st.sidebar.info("Credenciais Neo4j Aura ativas.")
    
    #executa o teste de conexão automático
    if not st.session_state.connected:
        with st.spinner("Sincronizando com o Neo4j Aura..."):
            if database.test_connection(uri, user, password, silent=True):
                st.session_state.connected = True
                st.rerun()
            else:
                st.sidebar.error("Falha ao autenticar com as credenciais dos Secrets.")
else:
    st.sidebar.warning("Modo Local: Secrets não detectados.")
    uri = st.sidebar.text_input("URI de Conexão", value="bolt://localhost:7687")
    user = st.sidebar.text_input("Usuário", value="neo4j")
    password = st.sidebar.text_input("Senha", type="password", value="")

    if st.sidebar.button("Conectar ao Banco de Dados"):
        if database.test_connection(uri, user, password, silent=False):
            st.session_state.connected = True
            st.sidebar.success("Conexão estabelecida localmente!")
            st.rerun()
        else:
            st.session_state.connected = False

st.markdown("---")

if not st.session_state.connected:
    st.info("Autentique as credenciais corretamente.")
else:
    
    # 1. Visualização do Grafo
    components.render_graph_viz(uri, user, password)
    
    # 2. Formulários de Criação e Edição
    col_left, col_right = st.columns([1.0, 1.0])
    
    with col_left:
        #Criação de Nós
        components.render_node_form(uri, user, password)
        st.markdown("<br>", unsafe_allow_html=True) 
        
        #Criação de Relacionamentos
        components.render_relationship_form(uri, user, password)
        st.markdown("<br>", unsafe_allow_html=True) 
        
        #Edição de Nós Existentes
        components.render_edit_node_form(uri, user, password)
        
    with col_right:
        #Remoção de Elementos
        components.render_delete_form(uri, user, password)
        st.markdown("<br>", unsafe_allow_html=True) 

        #Prompt Cypher
        st.subheader("Console de Comando Prompt Cypher")
        cypher_prompt = st.text_area(
            "Digite o Código Cypher para Execução:", 
            height=180,
            value="// Buscar total de conexões criadas\nMATCH (n)-[r]->(m) RETURN n.id, type(r), m.id LIMIT 5"
        )
        if st.button("Executar Prompt", use_container_width=True):
            if cypher_prompt.strip():
                with st.spinner("Processando instrução..."):
                    resultado = database.run_cypher(uri, user, password, cypher_prompt)
                    if resultado is not None:
                        st.write(" Registros Retornados:")
                        st.json([record.data() for record in resultado])