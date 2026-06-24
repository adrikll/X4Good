import streamlit as st
import streamlit.components.v1 as components
import database
from datetime import datetime
import unicodedata
import re

from neo4j_viz import Node as VizNode, Relationship as VizRel, VisualizationGraph

#mapeamento das cores dos nós
NODE_COLORS = {
    "User": "#3498db", "Post": "#e67e22", "Comment": "#2ecc71",
    "Community": "#9b59b6", "Topic": "#1abc9c", "Hashtag": "#f1c40f",
    "Event": "#e74c3c", "Device": "#95a5a6", "Location": "#34495e",
    "Media": "#d35400", "Advertisement": "#7f8c8d"
}

#mapeamento das cores dos relacionamentos
EDGE_COLORS = {
    "FOLLOWS": "#2980b9", "FRIEND_OF": "#27ae60", "LIKES": "#e74c3c",
    "SHARES": "#e67e22", "COMMENTS_ON": "#16a085", "POSTED": "#8e44ad",
    "MEMBER_OF": "#f39c12", "TAGGED_IN": "#d35400", "BLOCKED": "#c0392b",
    "MUTED": "#7f8c8d", "VIEWED": "#bdc3c7", "RECOMMENDED": "#1abc9c", "SIMILAR_TO": "#34495e"
}

#mapeamento de qual propriedade interna representa o rótulo visual do nó
CAPTION_FIELDS = {
    "User": "name",
    "Post": "id",
    "Media": "tipo",
    "Comment": "conteudo",
    "Community": "name",
    "Hashtag": "name",
    "Event": "name",
    "Device": "tipo",
    "Location": "name",
    "Advertisement": "empresa",
    "Topic": "name"
}

def auto_create_location(uri, user, password, country, state, city, bairro="", coords=""):
    
    """
    Cria ou atualiza um nó de Localização (Location) no Neo4j de forma automática.
    Gera um ID único baseado na concatenação dos dados geográficos sem acentos.
    Retorna o ID gerado para ser vinculado a outras entidades.
    """
    
    loc_parts_name = []
    
    if bairro and bairro.strip(): loc_parts_name.append(bairro.strip())
    if city and city.strip(): loc_parts_name.append(city.strip())
    if state and state.strip(): loc_parts_name.append(state.strip())
    if country and country.strip(): loc_parts_name.append(country.strip())
        
    if not loc_parts_name:
        return None
    
    loc_name = ", ".join(loc_parts_name)
    
    string_bruta = "".join(loc_parts_name)
    
    sem_acento = unicodedata.normalize('NFKD', string_bruta).encode('ascii', 'ignore').decode('utf-8')
    
    id_limpo = re.sub(r'[^a-zA-Z0-9]', '', sem_acento).lower()
    
    loc_id = f"loc_{id_limpo}"
    
    query = """
    MERGE (l:Location {id: $loc_id})
    ON CREATE SET l.name = $loc_name,
                  l.bairro = $bairro,
                  l.city = $city,
                  l.state = $state,
                  l.country = $country,
                  l.coords = $coords
    ON MATCH SET l.coords = COALESCE(l.coords, $coords)
    RETURN l.id
    """
    database.run_cypher(uri, user, password, query, {
        "loc_id": loc_id,
        "loc_name": loc_name,
        "bairro": bairro.strip() or None,
        "city": city.strip() or None,
        "state": state.strip() or None,
        "country": country.strip() or None,
        "coords": coords.strip() or None
    })
    return loc_id

def render_graph_viz(uri, user, password):
    
    """
    Renderiza a visualização interativa do grafo na interface Streamlit.
    Busca os nós e relacionamentos no banco, mapeia cores/textos e injeta 
    HTML/JS/CSS customizado para esconder legendas nativas e painéis padrão.
    """
    
    tit_col, theme_col = st.columns([0.75, 0.25])
    with tit_col:
        st.subheader("Visualização Espacial do Grafo (Engine Nativa Neo4j)")
    with theme_col:
        grafo_escuro = st.toggle("Modo Escuro no Grafo", value=False)
    
    #dados reais do banco
    query = "MATCH (n) OPTIONAL MATCH (n)-[r]->(m) RETURN n, r, m LIMIT 1000"
    data = database.run_cypher(uri, user, password, query)
    
    if not data:
        st.info("Banco de dados vazio ou desconectado.")
        return
    
    viz_nodes = []
    viz_relationships = []
    added_node_ids = set()
    nodes_properties = {}

    for record in data:
        for key in ["n", "m"]:
            node = record.get(key)
            if node is not None:
                n_id = node.get("id") if node.get("id") else (str(node.element_id) if hasattr(node, 'element_id') else str(node.id))
                
                if n_id not in added_node_ids:
                    label_type = list(node.labels)[0] if node.labels else "Unknown"
                    
                    props_dict = dict(node)
                    props_dict["Entity_Type"] = label_type 
                    
                    nodes_properties[str(n_id)] = props_dict
                    
                    target_property = CAPTION_FIELDS.get(label_type, "id")
                    display_caption = props_dict.get(target_property, n_id)
                    
                    props_dict["name"] = str(display_caption)
                    
                    viz_nodes.append(
                        VizNode(
                            id=n_id,
                            properties=props_dict,
                            caption=str(display_caption),
                            color=NODE_COLORS.get(label_type, "#9b59b6"),
                            size=15 if label_type == "Post" else 12 
                        )
                    )
                    added_node_ids.add(n_id)
                        
        r = record.get("r")
        if r is not None and record.get("n") is not None and record.get("m") is not None:
            o_id = record["n"].get("id") if record["n"].get("id") else str(record["n"].element_id)
            d_id = record["m"].get("id") if record["m"].get("id") else str(record["m"].element_id)
            r_id = str(r.element_id) if hasattr(r, 'element_id') else str(r.id)
            
            viz_relationships.append(
                VizRel(
                    id=r_id,
                    source=o_id,
                    target=d_id,
                    caption=r.type,
                    properties=dict(r)
                )
            )

    try:
        vg = VisualizationGraph(nodes=viz_nodes, relationships=viz_relationships)
        html_object = vg.render(width="100%", height="500px")
        
        st.session_state.nodes_properties = nodes_properties
        
        css_customizado = """
        <style>
        html, body {
            margin: 0 !important;
            padding: 0 !important;
            overflow: hidden !important;
            background-color: transparent !important;
        }
        </style>
        """
        
        if grafo_escuro:
            css_customizado = """
            <style>
            html, body {
                margin: 0 !important;
                padding: 0 !important;
                overflow: hidden !important;
                filter: invert(1) hue-rotate(180deg) !important;
                background-color: #0e1117 !important; /* Cor exata do Dark Mode do Streamlit */
            }
            </style>
            """
            
        html_customizado = html_object.data + css_customizado + """
        <script>
        setTimeout(function() {
            
            var elementosTexto = document.querySelectorAll('p, span, div');
            elementosTexto.forEach(function(el) {
                var txt = el.innerText || el.textContent || '';
                if (txt.includes('graph visualization with') && txt.includes('displayed using')) {
                    // Garante que não estamos ocultando a árvore/canvas principal por engano
                    if (!el.querySelector('canvas') && !el.querySelector('svg')) {
                        el.style.setProperty('display', 'none', 'important');
                    }
                }
            });

            var elementos = document.querySelectorAll('button, div, span, i, a');
            elementos.forEach(function(el) {
                var texto = (el.innerText || el.textContent || '').toLowerCase();
                var classe = (el.className || '').toString().toLowerCase();
                var id = (el.id || '').toLowerCase();
                
                var termosChave = ['config', 'setting', 'detail', 'prop', 'node', 'relationship', 'detalhe', 'opç', 'aba', 'menu'];
                
                var contemTermo = termosChave.some(function(termo) {
                    return texto.includes(termo) || classe.includes(termo) || id.includes(termo);
                });
                
                if (contemTermo) {
                    if (el.tagName === 'BUTTON' || window.getComputedStyle(el).cursor === 'pointer' || classe.includes('btn') || classe.includes('toggle')) {
                        el.click(); 
                    }
                    if (el.tagName === 'DIV' && (el.style.display === 'none' || classe.includes('hide') || classe.includes('close'))) {
                        el.style.display = 'block';
                        el.style.visibility = 'visible';
                    }
                }
            });

            var visConfig = document.querySelector('.vis-configuration-wrapper');
            if (visConfig) {
                visConfig.style.display = 'block';
            }
            
            var paineisDireita = document.querySelectorAll('div');
            paineisDireita.forEach(function(p) {
                var style = window.getComputedStyle(p);
                if (style.position === 'absolute' || style.position === 'fixed') {
                    if (parseInt(style.right) === 0 || p.className.includes('sidebar') || p.className.includes('panel')) {
                        p.style.display = 'block';
                        p.style.transform = 'none';
                    }
                }
            });

        }, 400); 
        </script>
        """
        
        components.html(html_customizado, height=500)
        st.divider()
                            
    except Exception as e:
        st.error(f"Erro ao instanciar a engine neo4j-viz: {e}")
        
def render_node_form(uri, user, password):
    
    """
    Renderiza os formulários de criação de novos nós (User, Post, Media, etc.).
    Recebe os dados do usuário e executa as queries Cypher para 
    salvar no banco, criando amarrações automáticas (localização, tópicos).
    """
    
    st.subheader("Criar Nós")
    tipo_no = st.selectbox("Selecione o Tipo de Entidade:", ["User", "Post", "Media", "Comment", "Community", "Hashtag", "Event", "Device", "Location", "Advertisement", "Topic"])
    
    now = datetime.now()
    current_date = now.strftime("%Y-%m-%d")
    current_time = now.strftime("%H:%M:%S")

    with st.container(border=True):
        
        #formulário user
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
                    
                    #vinculação geográfica automática
                    loc_id = auto_create_location(uri, user, password, u_country, u_state, u_city)
                    if loc_id:
                        loc_query = "MATCH (u:User {id: $id}), (l:Location {id: $loc_id}) MERGE (u)-[:LOCATED_IN {timestamp: datetime()}]->(l)"
                        database.run_cypher(uri, user, password, loc_query, {"id": u_id.strip(), "loc_id": loc_id})
                    
                    st.success(f"User {u_id} processado com amarração geográfica automática!"); st.rerun()
                else: st.error("user_id é obrigatório!")

        #formulário post
        elif tipo_no == "Post":
            p_id = st.text_input("ID do Post (post_id) * Obrigatório:")
            p_user = st.text_input("ID do Usuário Criador (user_id) * Obrigatório:")
            p_date = st.text_input("Data * Obrigatório:", value=current_date)
            p_time = st.text_input("Hora * Obrigatório:", value=current_time)
            p_desc = st.text_area("Descrição (Opcional):")
            
            #caixas geográficas
            pc1, pc2, pc3 = st.columns(3)
            with pc1: p_country = st.text_input("País da Publicação (Opcional):")
            with pc2: p_state = st.text_input("Estado da Publicação (Opcional):")
            with pc3: p_city = st.text_input("Cidade da Publicação (Opcional):")
            
            p_topic_id = st.text_input("ID do Tópico do Post (Opcional):", placeholder="ex: top_01")
            p_tag_id = st.text_input("ID da Hashtag do Post (Opcional):", placeholder="ex: tag_IA")
            
            if st.button(" Publicar Post", use_container_width=True):
                if p_id.strip() and p_user.strip():
                    query = """
                    MATCH (u:User {id: $user_id}) 
                    MERGE (p:Post {id: $id}) 
                    SET p.data=$date, p.hora=$time, p.descricao=$desc, p.user_id=$user_id 
                    MERGE (u)-[:POSTED {timestamp: datetime()}]->(p) 
                    RETURN p
                    """
                    res = database.run_cypher(uri, user, password, query, {"id": p_id.strip(), "user_id": p_user.strip(), "date": p_date.strip(), "time": p_time.strip(), "desc": p_desc.strip() or None})
                    
                    if res:
                        loc_id = auto_create_location(uri, user, password, p_country, p_state, p_city)
                        if loc_id:
                            database.run_cypher(uri, user, password, "MATCH (p:Post {id: $id}), (l:Location {id: $loc_id}) MERGE (p)-[:LOCATED_IN {timestamp: datetime()}]->(l)", {"id": p_id.strip(), "loc_id": loc_id})
                        
                        if p_topic_id.strip():
                            database.run_cypher(uri, user, password, "MATCH (p:Post {id: $id}), (t:Topic {id: $t_id}) MERGE (p)-[:HAS_TOPIC]->(t)", {"id": p_id.strip(), "t_id": p_topic_id.strip()})
                        if p_tag_id.strip():
                            database.run_cypher(uri, user, password, "MATCH (p:Post {id: $id}), (h:Hashtag {id: $h_id}) MERGE (p)-[:TAGGED_WITH]->(h)", {"id": p_id.strip(), "h_id": p_tag_id.strip()})
                        
                        st.success("Post publicado e integrado à malha de localização!"); st.rerun()
                    else: st.error("Erro! O user_id do autor precisa existir no banco.")
                else: st.error("Campos obrigatórios ausentes!")
                
        #formulário media
        elif tipo_no == "Media":
            m_id = st.text_input("ID da Mídia (id_media) * Obrigatório:")
            m_tipo = st.selectbox("Tipo de Mídia * Obrigatório:", ["Imagem", "Vídeo", "Áudio", "3D Asset"])
            m_mime = st.text_input("MIME Type * Obrigatório:", value="image/png")
            m_bytes = st.number_input("Tamanho em Bytes * Obrigatório:", min_value=1, value=1024)
            m_post_id = st.text_input("ID do Post/Conteúdo dono desta mídia * Obrigatório:", placeholder="ex: post_01")
            
            #caixas geográficas da mídia
            mc1, mc2, mc3 = st.columns(3)
            with mc1: m_country = st.text_input("País de Origem da Mídia (Opcional):")
            with mc2: m_state = st.text_input("Estado de Origem da Mídia (Opcional):")
            with mc3: m_city = st.text_input("Cidade de Origem da Mídia (Opcional):")
            
            if st.button("Gravar Mídia", use_container_width=True):
                if m_id.strip() and m_post_id.strip():
                    query = "MERGE (m:Media {id: $id}) SET m.tipo=$tipo, m.mime_type=$mime, m.tam_bytes=$bytes RETURN m"
                    database.run_cypher(uri, user, password, query, {"id": m_id.strip(), "tipo": m_tipo, "mime": m_mime.strip(), "bytes": int(m_bytes)})
                    
                    rel_query = "MATCH (p:Post {id: $post_id}), (m:Media {id: $media_id}) MERGE (p)-[:HAS_MEDIA]->(m)"
                    res_rel = database.run_cypher(uri, user, password, rel_query, {"post_id": m_post_id.strip(), "media_id": m_id.strip()})
                    
                    if res_rel is not None:
                        loc_id = auto_create_location(uri, user, password, m_country, m_state, m_city)
                        if loc_id:
                            database.run_cypher(uri, user, password, "MATCH (m:Media {id: $id}), (l:Location {id: $loc_id}) MERGE (m)-[:LOCATED_IN {timestamp: datetime()}]->(l)", {"id": m_id.strip(), "loc_id": loc_id})
                        
                        st.success("Mídia criada, anexada ao post e localizada com sucesso!"); st.rerun()
                    else: st.error("Erro! O ID do Post informado não foi encontrado.")
                else: st.error("Preencha os IDs obrigatórios!")

        #formulário device
        elif tipo_no == "Device":
            d_id = st.text_input("ID Único do Dispositivo (device_id) * Obrigatório:")
            d_model = st.text_input("Modelo do Dispositivo * Obrigatório:", placeholder="ex: iPhone 15 Pro")
            d_type = st.selectbox("Tipo de Dispositivo * Obrigatório:", ["Mobile", "Desktop", "Tablet", "Smart TV"])
            d_user_id = st.text_input("ID do Usuário proprietário do dispositivo * Obrigatório:", placeholder="ex: adrik_ll")
            
            dc1, dc2, dc3 = st.columns(3)
            with dc1: d_country = st.text_input("País de Conexão do Dispositivo (Opcional):")
            with dc2: d_state = st.text_input("Estado de Conexão do Dispositivo (Opcional):")
            with dc3: d_city = st.text_input("Cidade de Conexão do Dispositivo (Opcional):")
            
            if st.button("Gravar e Vincular Dispositivo", use_container_width=True):
                if d_id.strip() and d_user_id.strip():
                    database.run_cypher(uri, user, password, "MERGE (d:Device {id: $id}) SET d.name=$model, d.tipo=$type", {"id": d_id.strip(), "model": d_model.strip(), "type": d_type})
                    res_u = database.run_cypher(uri, user, password, "MATCH (u:User {id: $u_id}), (d:Device {id: $d_id}) MERGE (u)-[:USES_DEVICE {since: datetime()}]->(d)", {"u_id": d_user_id.strip(), "d_id": d_id.strip()})
                    
                    if res_u:
                        loc_id = auto_create_location(uri, user, password, d_country, d_state, d_city)
                        if loc_id:
                            database.run_cypher(uri, user, password, "MATCH (d:Device {id: $d_id}), (l:Location {id: $loc_id}) MERGE (d)-[:LOCATED_IN {timestamp: datetime()}]->(l)", {"d_id": d_id.strip(), "loc_id": loc_id})
                        
                        st.success("Dispositivo registrado e localizado na rede!"); st.rerun()
                    else: st.error("Erro! Verifique se o ID do Usuário informado existe no sistema.")
                else: st.error("Campos obrigatórios ausentes!")

        #formulário event
        elif tipo_no == "Event":
            e_id = st.text_input("ID do Evento (event_id) * Obrigatório:")
            e_title = st.text_input("Título do Evento * Obrigatório:")
            e_user = st.text_input("ID do Usuário Organizador (user_id) * Obrigatório:")
            e_date = st.text_input("Data do Evento * Obrigatório:", value=current_date)
            e_time = st.text_input("Hora do Evento * Obrigatório:", value=current_time)
            
            ec1, ec2, ec3 = st.columns(3)
            with ec1: e_country = st.text_input("País do Evento (Opcional):")
            with ec2: e_state = st.text_input("Estado do Evento (Opcional):")
            with ec3: e_city = st.text_input("Cidade do Evento (Opcional):")
            
            e_topic_id = st.text_input("ID do Tópico Temático do Evento (Opcional):", placeholder="ex: top_01")
            
            if st.button("Gravar Evento", use_container_width=True):
                if e_id.strip() and e_title.strip() and e_user.strip():
                    query = "MATCH (u:User {id: $user_id}) MERGE (ev:Event {id: $id}) SET ev.name=$title, ev.data=$date, ev.hora=$time MERGE (u)-[:ORGANIZED {timestamp: datetime()}]->(ev) RETURN ev"
                    res = database.run_cypher(uri, user, password, query, {"id": e_id.strip(), "title": e_title.strip(), "user_id": e_user.strip(), "date": e_date.strip(), "time": e_time.strip()})
                    
                    if res:
                        loc_id = auto_create_location(uri, user, password, e_country, e_state, e_city)
                        if loc_id:
                            database.run_cypher(uri, user, password, "MATCH (ev:Event {id: $id}), (l:Location {id: $loc_id}) MERGE (ev)-[:LOCATED_IN]->(l)", {"id": e_id.strip(), "loc_id": loc_id})
                        
                        if e_topic_id.strip():
                            database.run_cypher(uri, user, password, "MATCH (ev:Event {id: $id}), (t:Topic {id: $t_id}) MERGE (ev)-[:HAS_TOPIC]->(t)", {"id": e_id.strip(), "t_id": e_topic_id.strip()})
                        st.success("Evento criado e integrado à malha geográfica!"); st.rerun()
                    else: st.error("Erro! O user_id do organizador precisa existir no banco.")
                else: st.error("Preencha os campos obrigatórios!")

        #formulário location
        elif tipo_no == "Location":
            st.info("O ID desta localização será gerado automaticamente de forma padronizada a partir dos campos geográficos preenchidos.")
            
            l_bairro = st.text_input("Bairro (Opcional):")
            lc1, lc2, lc3 = st.columns(3)
            with lc1: l_city = st.text_input("Cidade (Opcional):")
            with lc2: l_state = st.text_input("Estado (Opcional):")
            with lc3: l_country = st.text_input("País (Opcional):")
            
            l_coords = st.text_input("Coordenadas Geográficas (Opcional):", placeholder="ex: -3.7319, -38.5267")
            
            if st.button("Gravar Localização", use_container_width=True):
                # validação obrigatória solicitada: pelo menos 1 campo deve estar preenchido
                if not (l_country.strip() or l_state.strip() or l_city.strip() or l_bairro.strip()):
                    st.error("Erro! É obrigatório preencher pelo menos 1 dos campos geográficos: País, Estado, Cidade ou Bairro.")
                else:
                    loc_id = auto_create_location(uri, user, password, l_country, l_state, l_city, l_bairro, l_coords)
                    if loc_id:
                        st.success(f"Nó de Localização criado/garantido com sucesso! ID gerado automaticamente: {loc_id}")
                        st.rerun()

        #nós genéricos (Topic, Hashtag, Community, Comment, Advertisement)
        else:
            if tipo_no == "Comment":
                c_id = st.text_input("ID do Comentário (id_comment) * Obrigatório:")
                c_post = st.text_input("ID do Post Alvo (post_id) * Obrigatório:")
                c_user = st.text_input("ID do Autor do Comentário (user_id) * Obrigatório:")
                c_content = st.text_area("Conteúdo/Texto * Obrigatório:")
                if st.button("Gravar Comentário", use_container_width=True):
                    if c_id.strip() and c_post.strip() and c_user.strip() and c_content.strip():
                        query = "MATCH (u:User {id: $user_id}), (p:Post {id: $post_id}) MERGE (c:Comment {id: $id}) SET c.conteudo=$content, c.data=$date, c.hora=$time MERGE (u)-[:COMMENTS_ON {timestamp: datetime()}]->(c) MERGE (c)-[:BELONGS_TO]->(p) RETURN c"
                        res = database.run_cypher(uri, user, password, query, {"id": c_id.strip(), "post_id": c_post.strip(), "user_id": c_user.strip(), "content": c_content.strip(), "date": current_date, "time": current_time})
                        if res: st.success("Comentário criado!"); st.rerun()
                        else: st.error("Verifique os IDs informados.")
            
            elif tipo_no == "Community":
                cm_id = st.text_input("ID da Comunidade (community_id) * Obrigatório:")
                cm_name = st.text_input("Nome da Comunidade * Obrigatório:")
                cm_user = st.text_input("ID do Usuário Criador (user_id) * Obrigatório:")
                if st.button("Gravar Comunidade", use_container_width=True):
                    if cm_id.strip() and cm_name.strip() and cm_user.strip():
                        query = "MATCH (u:User {id: $user_id}) MERGE (c:Community {id: $id}) SET c.name=$name MERGE (u)-[:MEMBER_OF {role: 'admin', timestamp: datetime()}]->(c) RETURN c"
                        res = database.run_cypher(uri, user, password, query, {"id": cm_id.strip(), "name": cm_name.strip(), "user_id": cm_user.strip()})
                        if res: st.success("Comunidade criada!"); st.rerun()
            
            elif tipo_no == "Hashtag":
                h_id = st.text_input("ID da Hashtag * Obrigatório:")
                h_name = st.text_input("Nome (Sem #) * Obrigatório:")
                if st.button("Gravar Hashtag", use_container_width=True):
                    if h_id.strip() and h_name.strip():
                        database.run_cypher(uri, user, password, "MERGE (h:Hashtag {id: $id}) SET h.name = $name", {"id": h_id.strip(), "name": h_name.strip()})
                        st.success("Hashtag indexada!"); st.rerun()

            elif tipo_no == "Advertisement":
                ad_id = st.text_input("ID do Anúncio * Obrigatório:")
                ad_title = st.text_input("Título * Obrigatório:")
                ad_company = st.text_input("Empresa * Obrigatório:")
                ad_link = st.text_input("Link * Obrigatório:")
                if st.button("Gravar Anúncio", use_container_width=True):
                    if ad_id.strip() and ad_title.strip():
                        database.run_cypher(uri, user, password, "MERGE (a:Advertisement {id: $id}) SET a.name=$title, a.empresa=$company, a.link_destino=$link", {"id": ad_id.strip(), "title": ad_title.strip(), "company": ad_company.strip(), "link": ad_link.strip()})
                        st.success("Campanha gravada!"); st.rerun()

            else: #topic
                n_id = st.text_input(f"ID do(a) {tipo_no}:")
                n_name = st.text_input("Nome / Atributo Principal:")
                if st.button(f"Gravar {tipo_no}", use_container_width=True):
                    if n_id and n_name:
                        database.run_cypher(uri, user, password, f"MERGE (n:{tipo_no} {{id: $id}}) SET n.name = $name", {"id": n_id, "name": n_name})
                        st.success(f"{tipo_no} gravado!"); st.rerun()

def render_relationship_form(uri, user, password):
    
    """
    Renderiza o formulário para criar um relacionamento entre dois nós.
    Conecta entidades através de vínculos sociais definidos.
    """
    
    st.subheader("Criar Relacionamentos")
    with st.container(border=True):
        c1, c2 = st.columns(2)
        with c1:
            o_tipo = st.selectbox("Tipo Origem:", ["User", "Post", "Comment", "Community", "Topic", "Hashtag", "Event", "Device", "Location", "Media", "Advertisement"], key="r_ot")
            o_id = st.text_input("ID Origem:", key="r_oid")
        with c2:
            d_tipo = st.selectbox("Tipo Destino:", ["User", "Post", "Comment", "Community", "Topic", "Hashtag", "Event", "Device", "Location", "Media", "Advertisement"], key="r_dt")
            d_id = st.text_input("ID Destino:", key="r_did")
            
        tipo_aresta = st.selectbox("Selecione o Vínculo Social:", ["FOLLOWS", "FRIEND_OF", "LIKES", "SHARES", "COMMENTS_ON", "POSTED", "MEMBER_OF", "TAGGED_IN", "BLOCKED", "MUTED", "VIEWED", "SIMILAR_TO"])
        reacao = st.text_input("Atributo Contextual:", value="love")
        
        if st.button(" Conectar Entidades", use_container_width=True):
            if o_id and d_id:
                query = f"MATCH (a:{o_tipo} {{id: $oid}}), (b:{d_tipo} {{id: $did}}) MERGE (a)-[r:{tipo_aresta}]->(b) SET r.timestamp = datetime(), r.reaction = $react RETURN r"
                res = database.run_cypher(uri, user, password, query, {"oid": o_id, "did": d_id, "react": reacao})
                if res: st.success("Relacionamento estabelecido!"); st.rerun()
                else: st.error("Erro. Os IDs informados existem no banco?")
                
def render_edit_node_form(uri, user, password):
    
    """
    Renderiza os formulários para editar propriedades de nós já existentes.
    Atualiza apenas os campos preenchidos e refaz relacionamentos adjacentes 
    se houver mudança de contexto.
    """
    
    st.subheader("Editar um nó existente")
    tipo_no = st.selectbox(
        "Selecione o Tipo para Editar:", 
        ["User", "Post", "Media", "Comment", "Community", "Hashtag", "Event", "Device", "Location", "Advertisement", "Topic"], 
        key="edit_tipo_no"
    )
    edit_id = st.text_input("ID do Nó Alvo que deseja alterar *:", key="edit_node_id")

    with st.container(border=True):
        st.info("Campos em branco manterão seus dados antigos.")
        props = {}
        
        #edição user
        if tipo_no == "User":
            u_name = st.text_input("Novo Nome:", key="edit_u_name")
            c1, c2, c3 = st.columns(3)
            with c1: u_country = st.text_input("Novo País:", key="edit_u_country")
            with c2: u_state = st.text_input("Novo Estado:", key="edit_u_state")
            with c3: u_city = st.text_input("Nova Cidade:", key="edit_u_city")
            u_phone = st.text_input("Novo Telefone:", key="edit_u_phone")
            u_email = st.text_input("Novo Email:", key="edit_u_email")
            
            if st.button("Atualizar Usuário", use_container_width=True, key="btn_edit_user"):
                if edit_id.strip():
                    if u_name.strip(): props["name"] = u_name.strip()
                    if u_country.strip(): props["country"] = u_country.strip()
                    if u_state.strip(): props["state"] = u_state.strip()
                    if u_city.strip(): props["city"] = u_city.strip()
                    if u_phone.strip(): props["phone"] = u_phone.strip()
                    if u_email.strip(): props["email"] = u_email.strip()
                    
                    if props:
                        query = "MATCH (u:User {id: $id}) SET u += $props RETURN u"
                        database.run_cypher(uri, user, password, query, {"id": edit_id.strip(), "props": props})
                    
                    #se alterou a localização, recria o nó e move o relacionamento
                    loc_id = auto_create_location(uri, user, password, u_country, u_state, u_city)
                    if loc_id:
                        database.run_cypher(uri, user, password, "MATCH (u:User {id: $id})-[r:LOCATED_IN]->() DELETE r", {"id": edit_id.strip()})
                        database.run_cypher(uri, user, password, "MATCH (u:User {id: $id}), (l:Location {id: $loc_id}) MERGE (u)-[:LOCATED_IN {timestamp: datetime()}]->(l)", {"id": edit_id.strip(), "loc_id": loc_id})
                    
                    st.success(f"User '{edit_id}' atualizado com sucesso!"); st.rerun()
                else: st.error("O ID do nó alvo é obrigatório!")

        #edição post
        elif tipo_no == "Post":
            p_user = st.text_input("Novo ID do Usuário Criador (user_id):", key="edit_p_user")
            p_date = st.text_input("Nova Data (AAAA-MM-DD):", key="edit_p_date")
            p_time = st.text_input("Nova Hora (HH:MM:SS):", key="edit_p_time")
            p_desc = st.text_area("Nova Descrição:", key="edit_p_desc")
            
            pc1, pc2, pc3 = st.columns(3)
            with pc1: p_country = st.text_input("Novo País da Publicação:", key="edit_p_country")
            with pc2: p_state = st.text_input("Novo Estado da Publicação:", key="edit_p_state")
            with pc3: p_city = st.text_input("Nova Cidade da Publicação:", key="edit_p_city")
            
            p_topic_id = st.text_input("Novo ID do Tópico do Post:", key="edit_p_topic")
            p_tag_id = st.text_input("Novo ID da Hashtag do Post:", key="edit_p_tag")
            
            if st.button("Atualizar Post", use_container_width=True, key="btn_edit_post"):
                if edit_id.strip():
                    if p_user.strip(): props["user_id"] = p_user.strip()
                    if p_date.strip(): props["data"] = p_date.strip()
                    if p_time.strip(): props["hora"] = p_time.strip()
                    if p_desc.strip(): props["descricao"] = p_desc.strip()
                    
                    if props:
                        query = "MATCH (p:Post {id: $id}) SET p += $props RETURN p"
                        database.run_cypher(uri, user, password, query, {"id": edit_id.strip(), "props": props})
                    
                    #atualiza autor real se modificado
                    if p_user.strip():
                        database.run_cypher(uri, user, password, "MATCH ()-[r:POSTED]->(p:Post {id: $id}) DELETE r", {"id": edit_id.strip()})
                        database.run_cypher(uri, user, password, "MATCH (u:User {id: $user_id}), (p:Post {id: $id}) MERGE (u)-[:POSTED {timestamp: datetime()}]->(p)", {"id": edit_id.strip(), "user_id": p_user.strip()})
                    
                    #atualiza topologia geográfica
                    loc_id = auto_create_location(uri, user, password, p_country, p_state, p_city)
                    if loc_id:
                        database.run_cypher(uri, user, password, "MATCH (p:Post {id: $id})-[r:LOCATED_IN]->() DELETE r", {"id": edit_id.strip()})
                        database.run_cypher(uri, user, password, "MATCH (p:Post {id: $id}), (l:Location {id: $loc_id}) MERGE (p)-[:LOCATED_IN {timestamp: datetime()}]->(l)", {"id": edit_id.strip(), "loc_id": loc_id})
                        
                    #atualizatopologia temática
                    if p_topic_id.strip():
                        database.run_cypher(uri, user, password, "MATCH (p:Post {id: $id})-[r:HAS_TOPIC]->() DELETE r", {"id": edit_id.strip()})
                        database.run_cypher(uri, user, password, "MATCH (p:Post {id: $id}), (t:Topic {id: $t_id}) MERGE (p)-[:HAS_TOPIC]->(t)", {"id": edit_id.strip(), "t_id": p_topic_id.strip()})
                    if p_tag_id.strip():
                        database.run_cypher(uri, user, password, "MATCH (p:Post {id: $id})-[r:TAGGED_WITH]->() DELETE r", {"id": edit_id.strip()})
                        database.run_cypher(uri, user, password, "MATCH (p:Post {id: $id}), (h:Hashtag {id: $h_id}) MERGE (p)-[:TAGGED_WITH]->(h)", {"id": edit_id.strip(), "h_id": p_tag_id.strip()})
                        
                    st.success("Post modificado e relacionamentos atualizados!"); st.rerun()
                else: st.error("O ID do nó alvo é obrigatório!")

        #edição media
        elif tipo_no == "Media":
            m_tipo = st.selectbox("Novo Tipo de Mídia:", ["-- Manter Atual --", "Imagem", "Vídeo", "Áudio", "3D Asset"], key="edit_m_tipo")
            m_mime = st.text_input("Novo MIME Type:", key="edit_m_mime")
            m_bytes_str = st.text_input("Novo Tamanho (Bytes):", key="edit_m_bytes")
            m_post_id = st.text_input("Novo ID do Post dono desta mídia:", key="edit_m_post_id")
            
            mc1, mc2, mc3 = st.columns(3)
            with mc1: m_country = st.text_input("Novo País de Origem da Mídia:", key="edit_m_country")
            with mc2: m_state = st.text_input("Novo Estado de Origem da Mídia:", key="edit_m_state")
            with mc3: m_city = st.text_input("Nova Cidade de Origem da Mídia:", key="edit_m_city")
            
            if st.button("Atualizar Mídia", use_container_width=True, key="btn_edit_media"):
                if edit_id.strip():
                    if m_tipo != "-- Manter Atual --": props["tipo"] = m_tipo
                    if m_mime.strip(): props["mime_type"] = m_mime.strip()
                    if m_bytes_str.strip():
                        try: props["tam_bytes"] = int(m_bytes_str.strip())
                        except ValueError: st.error("Tamanho em Bytes deve ser um número inteiro válido."); return
                    
                    if props:
                        query = "MATCH (m:Media {id: $id}) SET m += $props RETURN m"
                        database.run_cypher(uri, user, password, query, {"id": edit_id.strip(), "props": props})
                        
                    if m_post_id.strip():
                        database.run_cypher(uri, user, password, "MATCH ()-[r:HAS_MEDIA]->(m:Media {id: $id}) DELETE r", {"id": edit_id.strip()})
                        database.run_cypher(uri, user, password, "MATCH (p:Post {id: $post_id}), (m:Media {id: $media_id}) MERGE (p)-[:HAS_MEDIA]->(m)", {"post_id": m_post_id.strip(), "media_id": edit_id.strip()})
                        
                    loc_id = auto_create_location(uri, user, password, m_country, m_state, m_city)
                    if loc_id:
                        database.run_cypher(uri, user, password, "MATCH (m:Media {id: $id})-[r:LOCATED_IN]->() DELETE r", {"id": edit_id.strip()})
                        database.run_cypher(uri, user, password, "MATCH (m:Media {id: $id}), (l:Location {id: $loc_id}) MERGE (m)-[:LOCATED_IN {timestamp: datetime()}]->(l)", {"id": edit_id.strip(), "loc_id": loc_id})
                        
                    st.success("Mídia atualizada!"); st.rerun()
                else: st.error("O ID do nó alvo é obrigatório!")

        #edição device
        elif tipo_no == "Device":
            d_model = st.text_input("Novo Modelo:", key="edit_d_model")
            d_type = st.selectbox("Novo Tipo de Dispositivo:", ["-- Manter Atual --", "Mobile", "Desktop", "Tablet", "Smart TV"], key="edit_d_tipo")
            d_user_id = st.text_input("Novo ID do Usuário proprietário do dispositivo:", key="edit_d_user_id")
            
            dc1, dc2, dc3 = st.columns(3)
            with dc1: d_country = st.text_input("Novo País de Conexão:", key="edit_d_country")
            with dc2: d_state = st.text_input("Novo Estado de Conexão:", key="edit_d_state")
            with dc3: d_city = st.text_input("Nova Cidade de Conexão:", key="edit_d_city")
            
            if st.button("Atualizar Dispositivo", use_container_width=True, key="btn_edit_device"):
                if edit_id.strip():
                    if d_model.strip(): props["name"] = d_model.strip()
                    if d_type != "-- Manter Atual --": props["tipo"] = d_type
                    
                    if props:
                        query = "MATCH (d:Device {id: $id}) SET d += $props RETURN d"
                        database.run_cypher(uri, user, password, query, {"id": edit_id.strip(), "props": props})
                        
                    if d_user_id.strip():
                        database.run_cypher(uri, user, password, "MATCH ()-[r:USES_DEVICE]->(d:Device {id: $id}) DELETE r", {"id": edit_id.strip()})
                        database.run_cypher(uri, user, password, "MATCH (u:User {id: $u_id}), (d:Device {id: $d_id}) MERGE (u)-[:USES_DEVICE {since: datetime()}]->(d)", {"u_id": d_user_id.strip(), "d_id": edit_id.strip()})
                        
                    loc_id = auto_create_location(uri, user, password, d_country, d_state, d_city)
                    if loc_id:
                        database.run_cypher(uri, user, password, "MATCH (d:Device {id: $id})-[r:LOCATED_IN]->() DELETE r", {"id": edit_id.strip()})
                        database.run_cypher(uri, user, password, "MATCH (d:Device {id: $d_id}), (l:Location {id: $loc_id}) MERGE (d)-[:LOCATED_IN {timestamp: datetime()}]->(l)", {"d_id": edit_id.strip(), "loc_id": loc_id})
                        
                    st.success("Dispositivo atualizado!"); st.rerun()
                else: st.error("O ID do nó alvo é obrigatório!")

        #edição event
        elif tipo_no == "Event":
            e_title = st.text_input("Novo Título:", key="edit_e_title")
            e_user = st.text_input("Novo ID do Usuário Organizador:", key="edit_e_user")
            e_date = st.text_input("Nova Data (AAAA-MM-DD):", key="edit_e_date")
            e_time = st.text_input("Nova Hora (HH:MM:SS):", key="edit_e_time")
            
            ec1, ec2, ec3 = st.columns(3)
            with ec1: e_country = st.text_input("Novo País do Evento:", key="edit_e_country")
            with ec2: e_state = st.text_input("Novo Estado do Evento:", key="edit_e_state")
            with ec3: e_city = st.text_input("Nova Cidade do Evento:", key="edit_e_city")
            e_topic_id = st.text_input("Novo ID do Tópico Temático:", key="edit_e_topic")
            
            if st.button("Atualizar Evento", use_container_width=True, key="btn_edit_event"):
                if edit_id.strip():
                    if e_title.strip(): props["name"] = e_title.strip()
                    if e_date.strip(): props["data"] = e_date.strip()
                    if e_time.strip(): props["hora"] = e_time.strip()
                    
                    if props:
                        query = "MATCH (ev:Event {id: $id}) SET ev += $props RETURN ev"
                        database.run_cypher(uri, user, password, query, {"id": edit_id.strip(), "props": props})
                        
                    if e_user.strip():
                        database.run_cypher(uri, user, password, "MATCH ()-[r:ORGANIZED]->(ev:Event {id: $id}) DELETE r", {"id": edit_id.strip()})
                        database.run_cypher(uri, user, password, "MATCH (u:User {id: $user_id}), (ev:Event {id: $id}) MERGE (u)-[:ORGANIZED {timestamp: datetime()}]->(ev)", {"user_id": e_user.strip(), "id": edit_id.strip()})
                        
                    loc_id = auto_create_location(uri, user, password, e_country, e_state, e_city)
                    if loc_id:
                        database.run_cypher(uri, user, password, "MATCH (ev:Event {id: $id})-[r:LOCATED_IN]->() DELETE r", {"id": edit_id.strip()})
                        database.run_cypher(uri, user, password, "MATCH (ev:Event {id: $id}), (l:Location {id: $loc_id}) MERGE (ev)-[:LOCATED_IN]->(l)", {"id": edit_id.strip(), "loc_id": loc_id})
                        
                    if e_topic_id.strip():
                        database.run_cypher(uri, user, password, "MATCH (ev:Event {id: $id})-[r:HAS_TOPIC]->() DELETE r", {"id": edit_id.strip()})
                        database.run_cypher(uri, user, password, "MATCH (ev:Event {id: $id}), (t:Topic {id: $t_id}) MERGE (ev)-[:HAS_TOPIC]->(t)", {"id": edit_id.strip(), "t_id": e_topic_id.strip()})
                        
                    st.success("Evento atualizado!"); st.rerun()
                else: st.error("O ID do nó alvo é obrigatório!")

        #edição location
        elif tipo_no == "Location":
            l_bairro = st.text_input("Novo Bairro:", key="edit_l_bairro")
            lc1, lc2, lc3 = st.columns(3)
            with lc1: l_city = st.text_input("Nova Cidade:", key="edit_l_city")
            with lc2: l_state = st.text_input("Novo Estado:", key="edit_l_state")
            with lc3: l_country = st.text_input("Novo País:", key="edit_l_country")
            l_coords = st.text_input("Novas Coordenadas Geográficas:", key="edit_l_coords")
            
            if st.button("Atualizar Localização", use_container_width=True, key="btn_edit_location"):
                if edit_id.strip():
                    if l_bairro.strip(): props["bairro"] = l_bairro.strip()
                    if l_city.strip(): props["city"] = l_city.strip()
                    if l_state.strip(): props["state"] = l_state.strip()
                    if l_country.strip(): props["country"] = l_country.strip()
                    if l_coords.strip(): props["coords"] = l_coords.strip()
                    
                    if props:
                        #reconstrói a propriedade de exibição visual baseada nos novos dados informados
                        loc_parts_name = []
                        if l_bairro.strip(): loc_parts_name.append(l_bairro.strip())
                        if l_city.strip(): loc_parts_name.append(l_city.strip())
                        if l_state.strip(): loc_parts_name.append(l_state.strip())
                        if l_country.strip(): loc_parts_name.append(l_country.strip())
                        if loc_parts_name:
                            props["name"] = ", ".join(loc_parts_name)
                            
                        query = "MATCH (l:Location {id: $id}) SET l += $props RETURN l"
                        res = database.run_cypher(uri, user, password, query, {"id": edit_id.strip(), "props": props})
                        if res: st.success("Nó geométrico Location atualizado!"); st.rerun()
                        else: st.error("Localização não encontrada com esse ID.")
                    else: st.info("Nenhum campo preenchido.")
                else: st.error("O ID do nó alvo é obrigatório!")

        #outros nós genéricos (Comment, Community, Advertisement, Topic, Hashtag)
        else:
            if tipo_no == "Comment":
                c_post = st.text_input("Novo ID do Post Alvo (post_id):", key="edit_c_post")
                c_user = st.text_input("Novo ID do Autor do Comentário (user_id):", key="edit_c_user")
                c_content = st.text_area("Novo Conteúdo do Comentário:", key="edit_c_content")
                
                if st.button("Atualizar Comentário", use_container_width=True, key="btn_edit_comment"):
                    if edit_id.strip():
                        if c_content.strip(): props["conteudo"] = c_content.strip()
                        if props:
                            database.run_cypher(uri, user, password, "MATCH (c:Comment {id: $id}) SET c += $props", {"id": edit_id.strip(), "props": props})
                        
                        if c_user.strip():
                            database.run_cypher(uri, user, password, "MATCH ()-[r:COMMENTS_ON]->(c:Comment {id: $id}) DELETE r", {"id": edit_id.strip()})
                            database.run_cypher(uri, user, password, "MATCH (u:User {id: $user_id}), (c:Comment {id: $id}) MERGE (u)-[:COMMENTS_ON {timestamp: datetime()}]->(c)", {"id": edit_id.strip(), "user_id": c_user.strip()})
                        if c_post.strip():
                            database.run_cypher(uri, user, password, "MATCH (c:Comment {id: $id})-[r:BELONGS_TO]->() DELETE r", {"id": edit_id.strip()})
                            database.run_cypher(uri, user, password, "MATCH (c:Comment {id: $id}), (p:Post {id: $post_id}) MERGE (c)-[:BELONGS_TO]->(p)", {"id": edit_id.strip(), "post_id": c_post.strip()})
                        
                        st.success("Comentário atualizado!"); st.rerun()
                    else: st.error("ID obrigatório.")
            
            elif tipo_no == "Community":
                cm_name = st.text_input("Novo Nome da Comunidade:", key="edit_cm_name")
                cm_user = st.text_input("Novo ID do Usuário Criador (user_id):", key="edit_cm_user")
                
                if st.button("Atualizar Comunidade", use_container_width=True, key="btn_edit_community"):
                    if edit_id.strip():
                        if cm_name.strip(): props["name"] = cm_name.strip()
                        if props:
                            database.run_cypher(uri, user, password, "MATCH (c:Community {id: $id}) SET c += $props", {"id": edit_id.strip(), "props": props})
                        if cm_user.strip():
                            database.run_cypher(uri, user, password, "MATCH ()-[r:MEMBER_OF {role: 'admin'}]->(c:Community {id: $id}) DELETE r", {"id": edit_id.strip()})
                            database.run_cypher(uri, user, password, "MATCH (u:User {id: $user_id}), (c:Community {id: $id}) MERGE (u)-[:MEMBER_OF {role: 'admin', timestamp: datetime()}]->(c)", {"id": edit_id.strip(), "user_id": cm_user.strip()})
                        st.success("Comunidade atualizada!"); st.rerun()
                    else: st.error("ID obrigatório.")
            
            elif tipo_no == "Advertisement":
                ad_title = st.text_input("Novo Título do Anúncio:", key="edit_ad_title")
                ad_company = st.text_input("Nova Empresa:", key="edit_ad_company")
                ad_link = st.text_input("Novo Link:", key="edit_ad_link")
                
                if st.button("Atualizar Anúncio", use_container_width=True, key="btn_edit_advertisement"):
                    if edit_id.strip():
                        if ad_title.strip(): props["name"] = ad_title.strip()
                        if ad_company.strip(): props["empresa"] = ad_company.strip()
                        if ad_link.strip(): props["link_destino"] = ad_link.strip()
                        if props:
                            query = "MATCH (a:Advertisement {id: $id}) SET a += $props RETURN a"
                            database.run_cypher(uri, user, password, query, {"id": edit_id.strip(), "props": props})
                            st.success("Campanha modificada!"); st.rerun()
                    else: st.error("ID obrigatório.")

            else: #Topic ou Hashtag
                n_name = st.text_input(f"Novo Nome do(a) {tipo_no}:", key="edit_generic_name")
                if st.button(f"Atualizar {tipo_no}", use_container_width=True, key="btn_edit_generic"):
                    if edit_id.strip():
                        if n_name.strip(): props["name"] = n_name.strip()
                        if props:
                            query = f"MATCH (n:{tipo_no} {{id: $id}}) SET n += $props RETURN n"
                            database.run_cypher(uri, user, password, query, {"id": edit_id.strip(), "props": props})
                            st.success(f"{tipo_no} atualizado!"); st.rerun()
                    else: st.error("ID obrigatório.")

def render_delete_form(uri, user, password):
    
    """
    Renderiza o painel de exclusãodo sistema.
    Permite deletar um nó completo com todas as suas arestas (DETACH DELETE) 
    ou romper apenas um relacionamento específico entre dois nós.
    """
    
    st.subheader("Deletar")
    opcao_del = st.radio("O que você deseja apagar da rede?", ["Nó (Entidade)", "Relacionamento"], horizontal=True, key="del_opcao_global")
    
    with st.container(border=True):
        #remover nó
        if opcao_del == "Nó (Entidade)":
            del_tipo = st.selectbox("Selecione o Tipo do Nó:", ["User", "Post", "Comment", "Community", "Topic", "Hashtag", "Event", "Device", "Location", "Media", "Advertisement"], key="del_tipo_no")
            del_id = st.text_input("ID do Nó a ser excluído permanentemente:", key="del_no_id")
            
            if st.button("Confirmar Exclusão do Nó", use_container_width=True):
                if del_id.strip():
                    query = f"MATCH (n:{del_tipo} {{id: $id}}) DETACH DELETE n"
                    database.run_cypher(uri, user, password, query, {"id": del_id.strip()})
                    st.success(f"Nó {del_id} e todas as suas ramificações foram excluídos!"); st.rerun()
                else:
                    st.error("Informe o ID da entidade para exclusão.")

        #remover relacionamento
        else:
            c1, c2 = st.columns(2)
            with c1:
                del_o_tipo = st.selectbox("Tipo Origem:", ["User", "Post", "Comment", "Community", "Topic", "Hashtag", "Event", "Device", "Location", "Media", "Advertisement"], key="del_rel_ot")
                del_o_id = st.text_input("ID Origem:", key="del_rel_oid")
            with c2:
                del_d_tipo = st.selectbox("Tipo Destino:", ["User", "Post", "Comment", "Community", "Topic", "Hashtag", "Event", "Device", "Location", "Media", "Advertisement"], key="del_rel_dt")
                del_d_id = st.text_input("ID Destino:", key="del_rel_did")
                
            del_tipo_aresta = st.selectbox("Selecione o Tipo de Relacionamento:", ["FOLLOWS", "FRIEND_OF", "LIKES", "SHARES", "COMMENTS_ON", "POSTED", "MEMBER_OF", "TAGGED_IN", "BLOCKED", "MUTED", "VIEWED", "SIMILAR_TO"], key="del_rel_tipo")
            
            if st.button("Apagar Relacionamento", use_container_width=True):
                if del_o_id.strip() and del_d_id.strip():
                    #localiza a aresta exata entre os nós e remove apenas ela, preservando os nós
                    query = f"MATCH (a:{del_o_tipo} {{id: $oid}})-[r:{del_tipo_aresta}]->(b:{del_d_tipo} {{id: $did}}) DELETE r"
                    database.run_cypher(uri, user, password, query, {"oid": del_o_id.strip(), "did": del_d_id.strip()})
                    st.success("Relacionamento rompido e deletado com sucesso!"); st.rerun()
                else:
                    st.error("Preencha os IDs de origem e destino para localizar a aresta.")