import streamlit as st
import streamlit.components.v1 as components
import database
from datetime import datetime

from neo4j_viz import Node as VizNode, Relationship as VizRel, VisualizationGraph

# Mapeamento de cores únicas por Tipo de Entidade (Nós)
NODE_COLORS = {
    "User": "#3498db", "Post": "#e67e22", "Comment": "#2ecc71",
    "Community": "#9b59b6", "Topic": "#1abc9c", "Hashtag": "#f1c40f",
    "Event": "#e74c3c", "Device": "#95a5a6", "Location": "#34495e",
    "Media": "#d35400", "Advertisement": "#7f8c8d"
}

# Mapeamento de cores únicas por Tipo de Relacionamento
EDGE_COLORS = {
    "FOLLOWS": "#2980b9", "FRIEND_OF": "#27ae60", "LIKES": "#e74c3c",
    "SHARES": "#e67e22", "COMMENTS_ON": "#16a085", "POSTED": "#8e44ad",
    "MEMBER_OF": "#f39c12", "TAGGED_IN": "#d35400", "BLOCKED": "#c0392b",
    "MUTED": "#7f8c8d", "VIEWED": "#bdc3c7", "RECOMMENDED": "#1abc9c", "SIMILAR_TO": "#34495e"
}

def render_graph_viz(uri, user, password):
    st.subheader("Visualização Espacial do Grafo (Engine Nativa Neo4j)")
    
    # Buscamos os dados reais do banco
    query = "MATCH (n) OPTIONAL MATCH (n)-[r]->(m) RETURN n, r, m LIMIT 100"
    data = database.run_cypher(uri, user, password, query)
    
    if not data:
        st.info("Banco de dados vazio ou desconectado.")
        return
    
    # Listas que vão alimentar a engine NVL
    viz_nodes = []
    viz_relationships = []
    added_node_ids = set()
    nodes_properties = {}  # Dicionário para armazenar propriedades dos nós

    for record in data:
        # Processamento e extração de Nós (Origem 'n' e Destino 'm')
        for key in ["n", "m"]:
            node = record.get(key)
            if node:
                n_id = node.get("id") if node.get("id") else (str(node.element_id) if hasattr(node, 'element_id') else str(node.id))
                
                if n_id not in added_node_ids:
                    label_type = list(node.labels)[0] if node.labels else "Unknown"
                    
                    # Copia as propriedades do nó e injeta o Tipo para exibição no tooltip
                    props_dict = dict(node)
                    props_dict["Entity_Type"] = label_type 
                    
                    # Armazena as propriedades para exibição ao clicar
                    nodes_properties[str(n_id)] = props_dict
                    
                    # Criando o nó no formato oficial neo4j-viz (Sem o argumento incompatível 'labels')
                    viz_nodes.append(
                        VizNode(
                            id=n_id,
                            properties=props_dict,
                            caption=str(n_id), # Texto central que aparece no nó
                            color=NODE_COLORS.get(label_type, "#9b59b6"),
                            size=15 if label_type == "Post" else 12 # Controle de escala dinâmico
                        )
                    )
                    added_node_ids.add(n_id)
                    
        # Processamento e extração de Relacionamentos 'r'
        r = record.get("r")
        if r and record.get("n") and record.get("m"):
            o_id = record["n"].get("id") if record["n"].get("id") else str(record["n"].element_id)
            d_id = record["m"].get("id") if record["m"].get("id") else str(record["m"].element_id)
            r_id = str(r.element_id) if hasattr(r, 'element_id') else str(r.id)
            
            # Criando a aresta no formato oficial neo4j-viz
            viz_relationships.append(
                VizRel(
                    id=r_id,
                    source=o_id,
                    target=d_id,
                    caption=r.type, # Texto que fica em cima da linha
                    properties=dict(r) # Adiciona propriedades ao passar o mouse
                )
            )

    try:
        # Construindo o Grafo de Visualização oficial da Neo4j
        vg = VisualizationGraph(nodes=viz_nodes, relationships=viz_relationships)
        
        # Renderiza a estrutura gerando o componente HTML nativo
        html_object = vg.render(width="100%", height="480px")
        
        # Armazena as propriedades em session_state para acesso posterior
        st.session_state.nodes_properties = nodes_properties
        
        # JavaScript para detectar cliques nos nós e atualizar a seleção
        html_with_click_handler = html_object.data + """
        <script>
        // Tenta encontrar o objeto network da vis.js (usado por neo4j-viz)
        setTimeout(function() {
            if (window.network) {
                window.network.on("click", function(params) {
                    if (params.nodes.length > 0) {
                        const nodeId = params.nodes[0];
                        // Atualiza a URL com o nó selecionado
                        const url = new URL(window.location);
                        url.searchParams.set('selected_node', encodeURIComponent(nodeId));
                        window.history.replaceState({}, '', url);
                        // Força um rerun do Streamlit
                        window.location.href = url.toString();
                    }
                });
            }
        }, 1000);
        </script>
        """
        
        # Injeta o HTML retornado diretamente dentro do contêiner do Streamlit
        components.html(html_with_click_handler, height=500)
        
        # Seção para exibir propriedades do nó
        st.divider()
        
        # Verifica se há um nó selecionado via URL
        query_params = st.query_params
        selected_node = query_params.get("selected_node", None)
        
        if not selected_node and len(nodes_properties) > 0:
            node_list = list(nodes_properties.keys())
            selected_node = st.selectbox(
                "Clique em um nó no grafo ou selecione aqui para ver suas propriedades:",
                node_list,
                key="selected_node_graph"
            )
        
        if selected_node and selected_node in nodes_properties:
            st.subheader(f"Propriedades de: {selected_node}")
            props = nodes_properties[selected_node]
            
            # Exibe as propriedades em um formato organizado
            cols_props = st.columns(2)
            prop_items = sorted(props.items())
            
            for idx, (prop_name, prop_value) in enumerate(prop_items):
                if prop_value is not None:
                    col_idx = idx % 2
                    with cols_props[col_idx]:
                        st.write(f"**{prop_name}:** {prop_value}")
        elif len(nodes_properties) > 0:
            st.info("👆 Clique em um nó no grafo acima para ver suas propriedades")
        
    except Exception as e:
        st.error(f"Erro ao instanciar a engine neo4j-viz: {e}")

def render_node_form(uri, user, password):
    st.subheader("Criação de Nós")
    tipo_no = st.selectbox("Selecione o Tipo de Entidade:", ["User", "Post", "Media", "Comment", "Community", "Hashtag", "Event", "Device", "Location", "Advertisement", "Topic"])
    
    now = datetime.now()
    current_date = now.strftime("%Y-%m-%d")
    current_time = now.strftime("%H:%M:%S")

    with st.container(border=True):
        # --- FORMULÁRIO: USER ---
        if tipo_no == "User":
            u_id = st.text_input("ID do Usuário (user_id) * Obrigatório:")
            u_name = st.text_input("Nome (Opcional):")
            c1, c2, c3 = st.columns(3)
            with c1: u_country = st.text_input("País (Opcional):")
            with c2: u_state = st.text_input("Estado (Opcional):")
            with c3: u_city = st.text_input("Cidade (Opcional):")
            u_phone = st.text_input("Telefone (Opcional):")
            u_email = st.text_input("Email (Opcional):")
            
            if st.button("Gravar Usuário", use_container_width=True):
                if u_id.strip():
                    query = "MERGE (u:User {id: $id}) SET u.name=$name, u.country=$country, u.state=$state, u.city=$city, u.phone=$phone, u.email=$email RETURN u"
                    database.run_cypher(uri, user, password, query, {"id": u_id.strip(), "name": u_name.strip() or None, "country": u_country.strip() or None, "state": u_state.strip() or None, "city": u_city.strip() or None, "phone": u_phone.strip() or None, "email": u_email.strip() or None})
                    st.success(f"User {u_id} criado!"); st.rerun()
                else: st.error("user_id é obrigatório!")

        # --- FORMULÁRIO: POST ---
        elif tipo_no == "Post":
            p_id = st.text_input("ID do Post (post_id) * Obrigatório:")
            p_user = st.text_input("ID do Usuário Criador (user_id) * Obrigatório:")
            p_date = st.text_input("Data * Obrigatório:", value=current_date)
            p_time = st.text_input("Hora * Obrigatório:", value=current_time)
            p_loc = st.text_input("Localização (Opcional):")
            p_desc = st.text_area("Descrição (Opcional):")
            
            if st.button(" Gravar Post", use_container_width=True):
                if p_id.strip() and p_user.strip() and p_date.strip() and p_time.strip():
                    query = "MATCH (u:User {id: $user_id}) MERGE (p:Post {id: $id}) SET p.data=$date, p.hora=$time, p.localizacao=$loc, p.descricao=$desc MERGE (u)-[:POSTED {timestamp: datetime()}]->(p) RETURN p"
                    res = database.run_cypher(uri, user, password, query, {"id": p_id.strip(), "user_id": p_user.strip(), "date": p_date.strip(), "time": p_time.strip(), "loc": p_loc.strip() or None, "desc": p_desc.strip() or None})
                    if res: st.success("Post publicado e vinculado ao autor!"); st.rerun()
                    else: st.error("Erro! Certifique-se de que o user_id do autor existe no banco.")
                else: st.error("Campos obrigatórios ausentes!")

        # --- FORMULÁRIO: MEDIA ---
        elif tipo_no == "Media":
            m_id = st.text_input("ID da Mídia (id_media) * Obrigatório:")
            m_tipo = st.text_input("Tipo (Imagem, Vídeo...) * Obrigatório:")
            m_mime = st.text_input("MIME Type * Obrigatório:", placeholder="ex: image/png")
            m_bytes = st.number_input("Tamanho em Bytes * Obrigatório:", min_value=1, value=1024)
            m_res = st.text_input("Resolução (Opcional):", placeholder="ex: 1080x1350")
            m_dur = st.number_input("Duração em Segundos (Opcional):", min_value=0.0, value=0.0)
            m_desc = st.text_area("Descrição (Opcional):")
            
            if st.button("Gravar Mídia", use_container_width=True):
                if m_id.strip() and m_tipo.strip() and m_mime.strip() and m_bytes > 0:
                    query = "MERGE (m:Media {id: $id}) SET m.tipo=$tipo, m.mime_type=$mime, m.tam_bytes=$bytes, m.resolucao=$res, m.duracao_seg=$dur, m.descricao=$desc RETURN m"
                    database.run_cypher(uri, user, password, query, {"id": m_id.strip(), "tipo": m_tipo.strip(), "mime": m_mime.strip(), "bytes": int(m_bytes), "res": m_res.strip() or None, "dur": float(m_dur) if m_dur > 0 else None, "desc": m_desc.strip() or None})
                    st.success("Mídia adicionada com sucesso!"); st.rerun()
                else: st.error("Preencha todos os campos obrigatórios!")

        # --- FORMULÁRIO: COMMENT ---
        elif tipo_no == "Comment":
            c_id = st.text_input("ID do Comentário (id_comment) * Obrigatório:")
            c_post = st.text_input("ID do Post Alvo (post_id) * Obrigatório:")
            c_user = st.text_input("ID do Autor do Comentário (user_id) * Obrigatório:")
            c_content = st.text_area("Conteúdo/Texto * Obrigatório:")
            c_date = st.text_input("Data * Obrigatório:", value=current_date)
            c_time = st.text_input("Hora * Obrigatório:", value=current_time)
            c_likes = st.number_input("Número de Likes * Obrigatório:", min_value=0, value=0)
            c_resp = st.number_input("Número de Respostas * Obrigatório:", min_value=0, value=0)
            
            if st.button("Gravar Comentário", use_container_width=True):
                if c_id.strip() and c_post.strip() and c_user.strip() and c_content.strip():
                    query = """
                    MATCH (u:User {id: $user_id}), (p:Post {id: $post_id})
                    MERGE (c:Comment {id: $id})
                    SET c.conteudo=$content, c.data=$date, c.hora=$time, c.num_likes=$likes, c.num_respostas=$resp
                    MERGE (u)-[:COMMENTS_ON {timestamp: datetime()}]->(c)
                    MERGE (c)-[:BELONGS_TO]->(p)
                    RETURN c
                    """
                    res = database.run_cypher(uri, user, password, query, {"id": c_id.strip(), "post_id": c_post.strip(), "user_id": c_user.strip(), "content": c_content.strip(), "date": c_date.strip(), "time": c_time.strip(), "likes": int(c_likes), "resp": int(c_resp)})
                    if res: st.success("Comentário criado e acoplado no grafo!"); st.rerun()
                    else: st.error("Erro! Verifique se o user_id e o post_id já existem no banco.")
                else: st.error("Campos obrigatórios ausentes!")

        # --- FORMULÁRIO: COMMUNITY ---
        elif tipo_no == "Community":
            cm_id = st.text_input("ID da Comunidade (community_id) * Obrigatório:")
            cm_name = st.text_input("Nome da Comunidade * Obrigatório:")
            cm_user = st.text_input("ID do Usuário Criador (user_id) * Obrigatório:")
            cm_priv = st.selectbox("Privacidade * Obrigatório:", ["Público", "Privado"])
            cm_date = st.text_input("Data de Criação * Obrigatório:", value=current_date)
            cm_time = st.text_input("Hora de Criação * Obrigatório:", value=current_time)
            cm_desc = st.text_area("Descrição (Opcional):")
            cm_rules = st.text_area("Regras da Comunidade (Opcional):")
            
            if st.button("Gravar Comunidade", use_container_width=True):
                if cm_id.strip() and cm_name.strip() and cm_user.strip():
                    query = """
                    MATCH (u:User {id: $user_id})
                    MERGE (c:Community {id: $id})
                    SET c.name=$name, c.privacidade=$priv, c.data_criacao=$date, c.hora_criacao=$time, c.descricao=$desc, c.regras=$rules
                    MERGE (u)-[:MEMBER_OF {role: "admin", timestamp: datetime()}]->(c)
                    RETURN c
                    """
                    res = database.run_cypher(uri, user, password, query, {"id": cm_id.strip(), "name": cm_name.strip(), "user_id": cm_user.strip(), "priv": cm_priv, "date": cm_date.strip(), "time": cm_time.strip(), "desc": cm_desc.strip() or None, "rules": cm_rules.strip() or None})
                    if res: st.success(f"Comunidade '{cm_name}' criada e vinculada ao fundador!"); st.rerun()
                    else: st.error("Erro! O user_id do criador precisa existir no banco.")
                else: st.error("Campos obrigatórios em falta!")

        # --- FORMULÁRIO: HASHTAG ---
        elif tipo_no == "Hashtag":
            h_id = st.text_input("ID da Hashtag (hashtag_id) * Obrigatório:", placeholder="ex: tag_tech")
            h_name = st.text_input("Nome da Tag (Sem o #) * Obrigatório:", placeholder="ex: TechForGood")
            
            if st.button("Gravar Hashtag", use_container_width=True):
                if h_id.strip() and h_name.strip():
                    query = "MERGE (h:Hashtag {id: $id}) SET h.name = $name RETURN h"
                    database.run_cypher(uri, user, password, query, {"id": h_id.strip(), "name": h_name.strip()})
                    st.success(f"Hashtag #{h_name} gravada!"); st.rerun()
                else: st.error("Campos obrigatórios ausentes!")

        # --- FORMULÁRIO: EVENT ---
        elif tipo_no == "Event":
            e_id = st.text_input("ID do Evento (event_id) * Obrigatório:")
            e_title = st.text_input("Título do Evento * Obrigatório:")
            e_user = st.text_input("ID do Usuário Organizador (user_id) * Obrigatório:")
            e_date = st.text_input("Data do Evento * Obrigatório:", value=current_date)
            e_time = st.text_input("Hora do Evento * Obrigatório:", value=current_time)
            e_link = st.text_input("Link de Acesso Virtual (Opcional):")
            e_desc = st.text_area("Descrição (Opcional):")
            
            if st.button("Gravar Evento", use_container_width=True):
                if e_id.strip() and e_title.strip() and e_user.strip():
                    query = """
                    MATCH (u:User {id: $user_id})
                    MERGE (ev:Event {id: $id})
                    SET ev.name=$title, ev.data=$date, ev.hora=$time, ev.link_acesso=$link, ev.descricao=$desc
                    MERGE (u)-[:ORGANIZED {timestamp: datetime()}]->(ev)
                    RETURN ev
                    """
                    res = database.run_cypher(uri, user, password, query, {"id": e_id.strip(), "title": e_title.strip(), "user_id": e_user.strip(), "date": e_date.strip(), "time": e_time.strip(), "link": e_link.strip() or None, "desc": e_desc.strip() or None})
                    if res: st.success("Evento criado e vinculado ao organizador!"); st.rerun()
                    else: st.error("Erro! O user_id do organizador precisa existir no banco.")
                else: st.error("Preencha os campos obrigatórios!")

        # --- FORMULÁRIO: DEVICE ---
        elif tipo_no == "Device":
            d_id = st.text_input("ID do Dispositivo (device_id) * Obrigatório:")
            d_model = st.text_input("Modelo do Dispositivo * Obrigatório:", placeholder="ex: iPhone 15 Pro")
            d_type = st.selectbox("Tipo de Dispositivo * Obrigatório:", ["Mobile", "Desktop", "Tablet", "Smart TV"])
            d_os = st.text_input("Sistema Operacional (Opcional):", placeholder="ex: iOS 17.4")
            
            if st.button("⚡ Gravar Dispositivo", use_container_width=True):
                if d_id.strip() and d_model.strip():
                    query = "MERGE (d:Device {id: $id}) SET d.name=$model, d.tipo=$type, d.sistema_operacional=$os RETURN d"
                    database.run_cypher(uri, user, password, query, {"id": d_id.strip(), "model": d_model.strip(), "type": d_type, "os": d_os.strip() or None})
                    st.success("Dispositivo catalogado!"); st.rerun()
                else: st.error("Campos obrigatórios ausentes!")

        # --- FORMULÁRIO: LOCATION ---
        elif tipo_no == "Location":
            l_id = st.text_input("ID da Localização (location_id) * Obrigatório:")
            l_name = st.text_input("Nome Geográfico Completo * Obrigatório:", placeholder="ex: Fortaleza - Ceará")
            c1, c2 = st.columns(2)
            with c1: l_lat = st.text_input("Latitude (Opcional):")
            with c2: l_lon = st.text_input("Longitude (Opcional):")
            
            if st.button("Gravar Localização", use_container_width=True):
                if l_id.strip() and l_name.strip():
                    query = "MERGE (l:Location {id: $id}) SET l.name=$name, l.latitude=$lat, l.longitude=$lon RETURN l"
                    database.run_cypher(uri, user, password, query, {"id": l_id.strip(), "name": l_name.strip(), "lat": l_lat.strip() or None, "lon": l_lon.strip() or None})
                    st.success("Coordenada geográfica mapeada!"); st.rerun()
                else: st.error("Campos obrigatórios ausentes!")

        # --- FORMULÁRIO: ADVERTISEMENT ---
        elif tipo_no == "Advertisement":
            ad_id = st.text_input("ID do Anúncio (adv_id) * Obrigatório:")
            ad_title = st.text_input("Título da Campanha Patrocinada * Obrigatório:")
            ad_company = st.text_input("Empresa Anunciante * Obrigatório:")
            ad_link = st.text_input("Link de Destino/Clique * Obrigatório:")
            ad_desc = st.text_area("Descrição do Anúncio (Opcional):")
            
            if st.button("Gravar Anúncio", use_container_width=True):
                if ad_id.strip() and ad_title.strip() and ad_company.strip() and ad_link.strip():
                    query = "MERGE (a:Advertisement {id: $id}) SET a.name=$title, a.empresa=$company, a.link_destino=$link, a.descricao=$desc RETURN a"
                    database.run_cypher(uri, user, password, query, {"id": ad_id.strip(), "title": ad_title.strip(), "company": ad_company.strip(), "link": ad_link.strip(), "desc": ad_desc.strip() or None})
                    st.success("Anúncio patrocinado indexado!"); st.rerun()
                else: st.error("Preencha todos os campos de campanha obrigatórios!")

        # --- FALLBACK: TOPIC OU GENÉRICOS ---
        else:
            n_id = st.text_input(f"ID do(a) {tipo_no}:")
            n_name = st.text_input("Nome / Atributo Principal:")
            if st.button(f"Gravar {tipo_no}", use_container_width=True):
                if n_id and n_name:
                    database.run_cypher(uri, user, password, f"MERGE (n:{tipo_no} {{id: $id}}) SET n.name = $name", {"id": n_id, "name": n_name})
                    st.success(f"{tipo_no} gravado!"); st.rerun()

def render_relationship_form(uri, user, password):
    st.subheader("Conexão de Relacionamentos")
    with st.container(border=True):
        c1, c2 = st.columns(2)
        with c1:
            o_tipo = st.selectbox("Tipo Origem:", ["User", "Post", "Comment", "Community", "Topic", "Hashtag", "Event", "Device", "Location", "Media", "Advertisement"], key="r_ot")
            o_id = st.text_input("ID Origem:", key="r_oid")
        with c2:
            d_tipo = st.selectbox("Tipo Destino:", ["User", "Post", "Comment", "Community", "Topic", "Hashtag", "Event", "Device", "Location", "Media", "Advertisement"], key="r_dt")
            d_id = st.text_input("ID Destino:", key="r_did")
            
        tipo_aresta = st.selectbox("Selecione o Vínculo Social:", ["FOLLOWS", "FRIEND_OF", "LIKES", "SHARES", "COMMENTS_ON", "POSTED", "MEMBER_OF", "TAGGED_IN", "BLOCKED", "MUTED", "VIEWED", "RECOMMENDED", "SIMILAR_TO"])
        reacao = st.text_input("Atributo Contextual:", value="love")
        
        if st.button(" Conectar Entidades", use_container_width=True):
            if o_id and d_id:
                query = f"MATCH (a:{o_tipo} {{id: $oid}}), (b:{d_tipo} {{id: $did}}) MERGE (a)-[r:{tipo_aresta}]->(b) SET r.timestamp = datetime(), r.reaction = $react RETURN r"
                res = database.run_cypher(uri, user, password, query, {"oid": o_id, "did": d_id, "react": reacao})
                if res: st.success("Relacionamento estabelecido!"); st.rerun()
                else: st.error("Erro. Os IDs informados existem no banco?")