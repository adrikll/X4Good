import streamlit as st
import database
import components


# Esse script controla a interface do Streamlit, gerencia a conexão com o banco
# de dados Neo4j (via st.secrets ou manual) e renderiza as ferramentas de administração.

# 1. Autenticação (Aura DB ou Local).
# 2. Renderização do Grafo (via components.py).
# 3. Formulários de CRUD de Nós e Arestas (via components.py).
# 4. Terminal de execução de queries Cypher diretas.


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
    
    #Visualização do Grafo
    components.render_graph_viz(uri, user, password)
    st.markdown("<br>", unsafe_allow_html=True)
    
    col_left, col_right = st.columns([1.0, 1.0])
    
    with col_left:
        #Criação de Nós
        components.render_node_form(uri, user, password)
        st.markdown("<br>", unsafe_allow_html=True) 
        
        #Remoção de Elementos 
        components.render_delete_form(uri, user, password)
        st.markdown("<br>", unsafe_allow_html=True)
        
    with col_right:
        #Criação de Relacionamentos
        components.render_relationship_form(uri, user, password)
        st.markdown("<br>", unsafe_allow_html=True) 
        
        #Edição de Nós Existentes
        components.render_edit_node_form(uri, user, password)
        st.markdown("<br>", unsafe_allow_html=True) 

    #console cypher
    st.markdown("---")
    st.subheader("Console de Comando Prompt Cypher")
        
    #Exemplos de consultas relevantes
    exemplos_cypher = """// CONSULTAS ESTRATÉGICAS

// 1. RECOMENDAÇÃO
// Quais usuarios foram recomendados a adrik_ll e por que?
// MATCH (u:User {id: "adrik_ll"})-[r:RECOMMENDED]->(recomendado:User)
// RETURN recomendado.id AS usuario_recomendado, r.motivo AS porque

// 2. SIMILARIDADE
// Quais são os usuários similares ao "vitoria_maria" e quais comunidades eles participam que ele não segue?
//MATCH (u:User {id: "vitoria_maria"})-[s:SIMILAR_TO]-(sim:User)
//RETURN sim.id AS usuario_semelhante,
//       s.score_total AS grau_de_similaridade,
//       coalesce(s.score_curtidas, 0) AS curtidas_em_comum,
//       coalesce(s.score_comunidades, 0) AS comunidades_em_comum,
//       coalesce(s.score_conexoes, 0) AS conexoes_em_comum,
//       coalesce(s.score_topicos, 0) AS topicos_em_comum
//ORDER BY grau_de_similaridade DESC

// 3. Gerenciamento de Perfil de Usuários
//MATCH (u:User {id: "vg_rocha"})
//OPTIONAL MATCH (u)-[:LOCATED_IN]->(l:Location)
//WITH u, l,
//     COUNT { (u)-[:FOLLOWS]->(:User) } AS seguindo,
//     COUNT { (:User)-[:FOLLOWS]->(u) } AS seguidores,
//     COUNT { (u)-[:FOLLOWS]->(m:User) WHERE (m)-[:FOLLOWS]->(u) } AS seguidores_mutuos

//RETURN u.id AS usuario,
//       u.name AS nome,
//       coalesce(l.name, "Não informada") AS localizacao,
//       seguidores,
//       seguindo,
//       seguidores_mutuos
"""

    cypher_prompt = st.text_area(
        "Digite o Código Cypher para Execução:", 
        height=350,
        value=exemplos_cypher
    )
        
    if st.button("Executar Prompt", use_container_width=True):
        #remove linhas de comentários antes de enviar pra não bugar a visualização
        linhas_validas = [linha for linha in cypher_prompt.split('\n') if not linha.strip().startswith('//')]
        query_limpa = '\n'.join(linhas_validas)
            
        if query_limpa.strip():
            with st.spinner("Processando instrução..."):
                resultado = database.run_cypher(uri, user, password, query_limpa)
                if resultado is not None:
                    st.write(" Registros Retornados:")
                    st.json([record.data() for record in resultado])