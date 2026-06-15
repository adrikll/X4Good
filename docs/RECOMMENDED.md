## Recomendação de Amigos

Se o Usuário A é amigo do Usuário B, e o Usuário B é amigo do Usuário C,
o sistema vai recomendar o Usuário C para o Usuário A 
(desde que eles já não sejam amigos).

MATCH (u:User)-[:FRIEND_OF]-(amigo)-[:FRIEND_OF]-(fof:User)
WHERE NOT (u)-[:FRIEND_OF]-(fof) AND u <> fof
WITH u, fof, count(amigo) AS mutual_friends
WHERE mutual_friends >= 1
MERGE (u)-[r:RECOMMENDED]->(fof)
SET r.timestamp = datetime(),
    r.tipo = "Amigo",
    r.motivo = "Vocês possuem " + mutual_friends + " amigo(s) em comum."
RETURN u.id AS usuario, fof.id AS recomendado, mutual_friends

## Recomendação de Comunidades

Recomendar comunidades onde os seus amigos já são membros, mas que você ainda
não faz parte. Quanto mais amigos seus estiverem lá dentro, mais forte será a 
recomendação.

MATCH (u:User)-[:FRIEND_OF]-(amigo)-[:MEMBER_OF]->(c:Community)
WHERE NOT (u)-[:MEMBER_OF]->(c)
WITH u, c, count(amigo) AS amigos_membros
MERGE (u)-[r:RECOMMENDED]->(c)
SET r.timestamp = datetime(),
    r.tipo = "Comunidade",
    r.motivo = "Você tem " + amigos_membros + " amigo(s) nesta comunidade."
RETURN u.id AS usuario, c.name AS comunidade, amigos_membros

## Recomendação de Conteúdo (posts)

Recomenda posts que os seus amigos curtiram (LIKES) ou compartilharam (SHARES),
mas que você ainda não interagiu.

MATCH (u:User)-[:FRIEND_OF]-(amigo)-[:LIKES|SHARES]->(p:Post)
WHERE NOT (u)-[:LIKES|SHARES|COMMENTS_ON]->(p) AND p.user_id <> u.id
WITH u, p, count(amigo) AS interacoes_amigos
MERGE (u)-[r:RECOMMENDED]->(p)
SET r.timestamp = datetime(),
    r.tipo = "Post",
    r.motivo = "Curtido por " + interacoes_amigos + " amigo(s) seu(s)."
RETURN u.id AS usuario, p.id AS post, interacoes_amigos

## Recomendação de Conteúdo (eventos)

ecomenda eventos que vão acontecer na mesma localização (Location) onde
o usuário reside ou costuma acessar a rede.

MATCH (u:User)-[:LOCATED_IN]->(l:Location)<-[:LOCATED_IN]-(e:Event)
// Garante que o usuário já não seja o organizador do evento
WHERE NOT (u)-[:ORGANIZED]->(e) 
MERGE (u)-[r:RECOMMENDED]->(e)
SET r.timestamp = datetime(),
    r.tipo = "Evento",
    r.motivo = "Evento disponível na sua região: " + l.name
RETURN u.id AS usuario, e.name AS evento, l.name AS local

## Recomendação de Conteudo (anuncios)

Se o usuário curte ou comenta em um Post, e esse Post pertence a um determinado Tópico (ou Hashtag), nós recomendamos campanhas de Anúncios que patrocinam esse mesmo Tópico.

MATCH (u:User)-[:LIKES|COMMENTS_ON]->(p:Post)-[:HAS_TOPIC]->(t:Topic)<-[:HAS_TOPIC]-(ad:Advertisement)
WITH u, ad, t, count(p) AS afinidade
MERGE (u)-[r:RECOMMENDED]->(ad)
SET r.timestamp = datetime(),
    r.tipo = "Anúncio",
    r.motivo = "Baseado no seu interesse pelo tema: " + t.name
RETURN u.id AS usuario, ad.name AS anuncio, t.name AS tema