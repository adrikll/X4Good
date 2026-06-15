import streamlit as st
import database
import components

st.set_page_config(page_title="X4Good Administrator Suite", layout="wide", page_icon="🌐")

st.title("🌐 X4Good Social Media")

if "connected" not in st.session_state:
    st.session_state.connected = False

try:
    #conexão local
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
    st.sidebar.success("Conectado via Streamlit Secrets!")
    st.sidebar.info("As credenciais seguras da nuvem do Neo4j Aura estão ativas.")
    
    # Executa o teste de conexão automático apenas uma vez para não travar o app
    if not st.session_state.connected:
        with st.spinner("Sincronizando com o Neo4j Aura..."):
            if database.test_connection(uri, user, password, silent=True):
                st.session_state.connected = True
                st.rerun()
            else:
                st.sidebar.error("Falha ao autenticar com as credenciais dos Secrets.")
else:

    st.sidebar.warning("⚠️ Modo Local: Secrets não detectados.")
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
    st.info("Autentique-se utilizando o painel lateral esquerdo para ativar as caixas do ecossistema.")
else:
    
    col_top_left, col_top_right = st.columns([1.0, 1.0])
    
    with col_top_left:
        # Superior Esquerdo: Criação de Nós
        components.render_node_form(uri, user, password)
        
    with col_top_right:
        # Superior Direito: Prompt Cypher
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

    st.markdown("---")
    
    col_bottom_left, col_bottom_right = st.columns([1.0, 1.0])
    
    with col_bottom_left:
        # Inferior Esquerdo: Criação de Relacionamentos
        components.render_relationship_form(uri, user, password)
        
    with col_bottom_right:
        # Inferior Direito: Visualização do Grafo
        components.render_graph_viz(uri, user, password)