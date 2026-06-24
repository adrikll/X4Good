# X4Good Social Media - Administrator Suite

O **X4Good Suite** é uma infraestrutura de gerenciamento e painel administrativo em tempo real para redes sociais baseadas em grafos. Desenvolvido com **Streamlit** e alimentado pelo **Neo4j Aura**, o ecossistema fornece uma interface visual interativa para operações completas de CRUD (Criação, Leitura, Atualização e Deleção) sobre estruturas relacionais complexas, além de embutir motores nativos de Inteligência de Grafos para cálculo de similaridade e recomendação de conteúdo.

---

##  Demonstração em Produção

Link oficial do painel de controle:
 **[x4good.streamlit.app](https://x4good.streamlit.app/)**

---

##  Visualização do Sistema

### 1. Visão Espacial do Grafo

![Painel Superior - Visualização Espacial do Grafo de Ponta a Ponta](images/grafo.png)

### 2. Criação de Nós

![Painel Criação - Criação de nós e relacionamentos](images/criação.png)

### 3. Deletar e editar

![Painel de Deletar um nó/relacionamento ou editar um nó](images/delet_edit.png)

### 3. Prompt Cypher

![Promt para consultas cypher](images/prompt.png)

---


##  Modelo de Dados (Schema do Grafo)

O ecossistema modela uma plataforma de mídia social completa através de:

- **11 Tipos de Nós (Rótulos):** `User`, `Post`, `Media`, `Comment`, `Community`, `Hashtag`, `Event`, `Device`, `Location`, `Advertisement`, `Topic`.
- **Arestas Principais:** `FOLLOWS`, `FRIEND_OF`, `LIKES`, `SHARES`, `COMMENTS_ON`, `POSTED`, `MEMBER_OF`, `TAGGED_IN`, `BLOCKED`, `MUTED`, `VIEWED`, `SIMILAR_TO`, `HAS_MEDIA`, `LOCATED_IN`.

---

##  Implementações Inteligentes

O projeto possui scripts analíticos para geração de inteligência sobre o grafo:

###  Similaridade (`SIMILAR_TO`)
Calcula de forma cross-entidade o nível de afinidade entre elementos da rede, gerando novas arestas ponderadas por um `score_total` acumulado:
- **Usuários:** Avalia curtidas mútuas, comunidades compartilhadas, sobreposição de seguidores/seguidos e tópicos em comum.
- **Posts:** Avalia o compartilhamento de tópicos, concorrência de Hashtags e usuários engajados em comum.
- **Mídias, Comentários e Anúncios:** Mapeia comportamentos de bots (textos idênticos), afinidade de marcas e resoluções técnicas equivalentes.

###  Recomendação (`RECOMMENDED`)
Algoritmos de recomendação baseados em topologia estrutural:
- **Recomendação de Amigos:** Abordagem clássica de *Friend-of-a-Friend* (amigos em comum), recomendando usuários não conectados com validação de restrição de auto-vínculo.
- **Recomendação de Comunidades:** Identifica os clusters onde seus amigos mais engajam, mas que você ainda não faz parte.
- **Recomendação de Conteúdo (Posts, Eventos e Anúncios):** Filtros baseados em geolocalização residencial ou afinidade a tópicos específicos patrocinados por marcas.

---

##  Instalação e Execução Local

### 1. Clonar o Repositório
```bash
git clone https://github.com/adrikll/X4Good.git
```
### 2. Instalar dependências
```bash
pip install -r requirements.txt
```
### 3. Execução
```bash
streamlit run app.py
```

### Obs: Para execução local é necessária as credenciais do banco na nuvem (em .streamlit/secrets.toml)