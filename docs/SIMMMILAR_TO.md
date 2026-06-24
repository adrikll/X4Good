# Implementação de SIMILAR_TO para Usuários

Calcula a similaridade entre usuários com base em interações e interesses em comum, consolidando os pesos em um score final.

## 1. Curtidas em comum

```cypher
MATCH (u1:User)-[:LIKES]->(p:Post)<-[:LIKES]-(u2:User)
WHERE u1.id < u2.id

WITH u1, u2, count(p) AS curtidas_comum

// Cria ou atualiza o relacionamento de similaridade
MERGE (u1)-[s:SIMILAR_TO]->(u2)
SET s.score_curtidas = curtidas_comum,
    s.timestamp = datetime();
```

## 2. Comunidades em comum

```cypher
MATCH (u1:User)-[:MEMBER_OF]->(c:Community)<-[:MEMBER_OF]-(u2:User)
WHERE u1.id < u2.id

WITH u1, u2, count(c) AS comunidades_comum

MERGE (u1)-[s:SIMILAR_TO]->(u2)
SET s.score_comunidades = comunidades_comum,
    s.timestamp = datetime();
```

## 3. Seguidores ou Seguidos em comum

```cypher
MATCH (u1:User), (u2:User)
WHERE u1.id < u2.id

// Identifica pessoas que ambos seguem
OPTIONAL MATCH (u1)-[:FOLLOWS]->(comumSeguido:User)<-[:FOLLOWS]-(u2)
// Identifica pessoas que seguem a ambos
OPTIONAL MATCH (u1)<-[:FOLLOWS]-(comumSeguidor:User)-[:FOLLOWS]->(u2)

WITH u1, u2, 
     count(distinct comumSeguido) AS seguidos, 
     count(distinct comumSeguidor) AS seguidores

WITH u1, u2, (seguidos + seguidores) AS conexoes_total
WHERE conexoes_total > 0

MERGE (u1)-[s:SIMILAR_TO]->(u2)
SET s.score_conexoes = conexoes_total,
    s.timestamp = datetime();
```

## 4. Tópicos de interesse em comum

```cypher
MATCH (u1:User)-[:POSTED|LIKES]->(:Post)-[:HAS_TOPIC]->(t:Topic)<-[:HAS_TOPIC]-(:Post)<-[:POSTED|LIKES]-(u2:User)
WHERE u1.id < u2.id

WITH u1, u2, count(distinct t) AS topicos_comum

MERGE (u1)-[s:SIMILAR_TO]->(u2)
SET s.score_topicos = topicos_comum,
    s.timestamp = datetime();
```

## 5. Consolidação do Score Total de Similaridade de Usuários

```cypher
MATCH (u1:User)-[s:SIMILAR_TO]->(u2:User)

WITH s, 
     coalesce(s.score_curtidas, 0) AS c,
     coalesce(s.score_comunidades, 0) AS cm,
     coalesce(s.score_conexoes, 0) AS cx,
     coalesce(s.score_topicos, 0) AS tp

// Calcula a soma simples (ou você pode multiplicar por pesos se quiser dar mais relevância a um fator)
SET s.score_total = c + cm + cx + tp;
```

# Implementação de SIMILAR_TO para Posts

## 1. Posts que compartilham o mesmo Tópico

```cypher
MATCH (p1:Post)-[:HAS_TOPIC]->(t:Topic)<-[:HAS_TOPIC]-(p2:Post)
WHERE p1.id < p2.id

WITH p1, p2, count(t) AS topicos_comum

// Cria ou atualiza o relacionamento de similaridade entre os posts
MERGE (p1)-[s:SIMILAR_TO]->(p2)
SET s.score_topicos = topicos_comum,
    s.timestamp = datetime();
```

## 2. Posts que utilizam as mesmas Hashtags

```cypher
MATCH (p1:Post)-[:TAGGED_WITH]->(h:Hashtag)<-[:TAGGED_WITH]-(p2:Post)
WHERE p1.id < p2.id

WITH p1, p2, count(h) AS tags_comum

MERGE (p1)-[s:SIMILAR_TO]->(p2)
SET s.score_tags = tags_comum,
    s.timestamp = datetime();
```

## 3. Posts que foram curtidos pelas mesmas pessoas

```cypher
MATCH (p1:Post)<-[:LIKES]-(u:User)-[:LIKES]->(p2:Post)
WHERE p1.id < p2.id

WITH p1, p2, count(u) AS curtidas_comum

MERGE (p1)-[s:SIMILAR_TO]->(p2)
SET s.score_curtidas = curtidas_comum,
    s.timestamp = datetime();
```

## 4. Consolidação do Score Total para os Posts

```cypher
MATCH (p1:Post)-[s:SIMILAR_TO]->(p2:Post)

WITH s, 
     coalesce(s.score_topicos, 0) AS tp,
     coalesce(s.score_tags, 0) AS tg,
     coalesce(s.score_curtidas, 0) AS lk

SET s.score_total = tp + tg + lk;
```

# Implementação de SIMILAR_TO para Media

## 1. Mídias com mesma categoria e formato técnico

```cypher
MATCH (m1:Media), (m2:Media)
WHERE m1.id < m2.id 
  AND m1.tipo = m2.tipo 
  AND m1.mime_type = m2.mime_type

WITH m1, m2, 1 AS score_formato

// Cria o vínculo inicial de similaridade
MERGE (m1)-[s:SIMILAR_TO]->(m2)
SET s.score_tecnico = score_formato,
    s.timestamp = datetime();
```

## 2. Mídias com resoluções idênticas

```cypher
MATCH (m1:Media), (m2:Media)
WHERE m1.id < m2.id 
  AND m1.resolucao IS NOT NULL 
  AND m1.resolucao = m2.resolucao

WITH m1, m2, 2 AS score_res // Peso maior por ser uma métrica mais específica

MERGE (m1)-[s:SIMILAR_TO]->(m2)
SET s.score_resolucao = score_res,
    s.timestamp = datetime();
```

## 3. Mídias que aparecem juntas no mesmo Post ou Evento

```cypher
MATCH (publicacao)-[:HAS_MEDIA|ATTACHED_TO]->(m1:Media)
MATCH (publicacao)-[:HAS_MEDIA|ATTACHED_TO]->(m2:Media)
WHERE m1.id < m2.id

WITH m1, m2, count(publicacao) AS ocorrencias_comum

MERGE (m1)-[s:SIMILAR_TO]->(m2)
SET s.score_contexto = ocorrencias_comum * 3, // Peso alto para vínculo social ativo
    s.timestamp = datetime();
```

## 4. Consolidação final do score para entidades de Mídia

```cypher
MATCH (m1:Media)-[s:SIMILAR_TO]->(m2:Media)

WITH s,
     coalesce(s.score_tecnico, 0) AS st,
     coalesce(s.score_resolucao, 0) AS sr,
     coalesce(s.score_contexto, 0) AS sc

SET s.score_total = st + sr + sc;
```

# Implementação de SIMILAR_TO para Comentários

## 1. Comentários criados dentro do mesmo Post alvo

```cypher
MATCH (c1:Comment)-[:BELONGS_TO]->(p:Post)<-[:BELONGS_TO]-(c2:Comment)
WHERE c1.id < c2.id

WITH c1, c2, 1 AS score_contexto

// Cria o vínculo de similaridade
MERGE (c1)-[s:SIMILAR_TO]->(c2)
SET s.score_debate = score_contexto,
    s.timestamp = datetime();
```

## 2. Comentários com nível de engajamento equivalente

```cypher
MATCH (c1:Comment), (c2:Comment)
WHERE c1.id < c2.id 
  AND c1.num_likes = c2.num_likes 
  AND c1.num_respostas = c2.num_respostas
  AND c1.num_likes > 5 // Filtro para dar relevância apenas a comentários engajados

WITH c1, c2, 2 AS score_engajamento

MERGE (c1)-[s:SIMILAR_TO]->(c2)
SET s.score_engajamento = score_engajamento,
    s.timestamp = datetime();
```

## 3. Comentários escritos pelo mesmo autor e com conteúdos parecidos

```cypher
MATCH (u:User)-[:COMMENTS_ON]->(c1:Comment)
MATCH (u)-[:COMMENTS_ON]->(c2:Comment)
WHERE c1.id < c2.id

// Verifica se o texto é exatamente igual (comportamento de bot/spam)
WITH c1, c2, CASE WHEN c1.conteudo = c2.conteudo THEN 5 ELSE 1 END AS score_autor

MERGE (c1)-[s:SIMILAR_TO]->(c2)
SET s.score_autoria = score_autor,
    s.timestamp = datetime();
```

## 4. Consolidação final do score para entidades de Comentário

```cypher
MATCH (c1:Comment)-[s:SIMILAR_TO]->(c2:Comment)

WITH s,
     coalesce(s.score_debate, 0) AS sd,
     coalesce(s.score_engajamento, 0) AS se,
     coalesce(s.score_autoria, 0) AS sa

SET s.score_total = sd + se + sa;
```

# Implementação de SIMILAR_TO para Comunidades

## 1. Comunidades que possuem membros em comum

```cypher
MATCH (u:User)-[:MEMBER_OF]->(c1:Community)
MATCH (u)-[:MEMBER_OF]->(c2:Community)
WHERE c1.id < c2.id

WITH c1, c2, count(u) AS membros_comum

// Cria ou atualiza o vínculo de similaridade entre as comunidades
MERGE (c1)-[s:SIMILAR_TO]->(c2)
SET s.score_membros = membros_comum,
    s.timestamp = datetime();
```

## 2. Comunidades cujos membros interagem com os mesmos Tópicos

```cypher
MATCH (c1:Community)<-[:MEMBER_OF]-(u1:User)-[:POSTED|LIKES]->(:Post)-[:HAS_TOPIC]->(t:Topic)
MATCH (t)<-[:HAS_TOPIC]-(:Post)<-[:POSTED|LIKES]-(u2:User)-[:MEMBER_OF]->(c2:Community)
WHERE c1.id < c2.id AND u1 <> u2

WITH c1, c2, count(distinct t) AS topicos_comum

MERGE (c1)-[s:SIMILAR_TO]->(c2)
SET s.score_topicos = topicos_comum,
    s.timestamp = datetime();
```

## 3. Consolidação final do score para entidades de Comunidade

```cypher
MATCH (c1:Community)-[s:SIMILAR_TO]->(c2:Community)

WITH s,
     coalesce(s.score_membros, 0) AS sm,
     coalesce(s.score_topicos, 0) AS st

SET s.score_total = sm + st;
```

# Implementação de SIMILAR_TO para Hashtags

## 1. Hashtags que aparecem juntas no mesmo Post

```cypher
MATCH (p:Post)-[:TAGGED_WITH]->(h1:Hashtag)
MATCH (p)-[:TAGGED_WITH]->(h2:Hashtag)
WHERE h1.id < h2.id

WITH h1, h2, count(p) AS posts_comum

// Cria ou atualiza o vínculo de similaridade entre as Hashtags
MERGE (h1)-[s:SIMILAR_TO]->(h2)
SET s.score_posts = posts_comum,
    s.timestamp = datetime();
```

## 2. Hashtags consumidas ou usadas pelos mesmos Usuários

```cypher
MATCH (u:User)-[:POSTED|LIKES]->(:Post)-[:TAGGED_WITH]->(h1:Hashtag)
MATCH (u)-[:POSTED|LIKES]->(:Post)-[:TAGGED_WITH]->(h2:Hashtag)
WHERE h1.id < h2.id

WITH h1, h2, count(distinct u) AS usuarios_comum

MERGE (h1)-[s:SIMILAR_TO]->(h2)
SET s.score_usuarios = usuarios_comum,
    s.timestamp = datetime();
```

## 3. Consolidação final do score para entidades de Hashtag

```cypher
MATCH (h1:Hashtag)-[s:SIMILAR_TO]->(h2:Hashtag)

WITH s,
     coalesce(s.score_posts, 0) AS sp,
     coalesce(s.score_usuarios, 0) AS su

// Multiplicamos por 2 o score de posts para dar mais relevância ao contexto direto
SET s.score_total = (sp * 2) + su;
```

# Implementação de SIMILAR_TO para Devices

```cypher
// Mapeia dispositivos do mesmo tipo e sistema operacional
MATCH (d1:Device), (d2:Device)
WHERE d1.id < d2.id 
  AND d1.tipo = d2.tipo 
  AND d1.sistema_operacional = d2.sistema_operacional

WITH d1, d2, 2 AS score_hardware

MERGE (d1)-[s:SIMILAR_TO]->(d2)
SET s.score_tecnico = score_hardware,
    s.timestamp = datetime();
```

# Implementação de SIMILAR_TO para Localização

```cypher
// Identifica localizações que compartilham a mesma base de usuários
MATCH (u:User)-[:LOCATED_IN]->(l1:Location), (u)-[:LOCATED_IN]->(l2:Location)
WHERE l1.id < l2.id

WITH l1, l2, count(u) AS usuarios_comum

MERGE (l1)-[s:SIMILAR_TO]->(l2)
SET s.score_populacao = usuarios_comum,
    s.timestamp = datetime();
```

# Implementação de SIMILAR_TO para Advertisements (Anúncios)

## 1. Calcula afinidade por empresa e por histórico de visualizações (VIEWED)

```cypher
MATCH (u:User)-[:VIEWED]->(a1:Advertisement), (u)-[:VIEWED]->(a2:Advertisement)
WHERE a1.id < a2.id

WITH a1, a2, count(u) AS views_comum
OPTIONAL MATCH (a1), (a2) WHERE a1.empresa = a2.empresa
WITH a1, a2, views_comum, CASE WHEN a1.empresa = a2.empresa THEN 3 ELSE 0 END AS score_marca

MERGE (a1)-[s:SIMILAR_TO]->(a2)
SET s.score_publico = views_comum,
    s.score_anunciante = score_marca,
    s.timestamp = datetime();
```

## 2. Consolidação do Score de Anúncios

```cypher
MATCH (a1:Advertisement)-[s:SIMILAR_TO]->(a2:Advertisement)
SET s.score_total = coalesce(s.score_publico, 0) + coalesce(s.score_anunciante, 0);
```

# Implementação de SIMILAR_TO para Tópicos

```cypher
// Encontra tópicos que costumam andar juntos nos mesmos Posts
MATCH (p:Post)-[:HAS_TOPIC]->(t1:Topic), (p)-[:HAS_TOPIC]->(t2:Topic)
WHERE t1.id < t2.id

WITH t1, t2, count(p) AS posts_comum

MERGE (t1)-[s:SIMILAR_TO]->(t2)
SET s.score_contexto = posts_comum,
    s.timestamp = datetime();
```