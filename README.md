# 🌐 X4Good - Infraestrutura e Painel de Controle de Banco de Dados em Grafos

Este repositório contém a implementação completa do banco de dados e da interface gráfica administrativa para a plataforma de mídia social de próxima geração **X4Good**. O ecossistema fornece um mecanismo rápido, visual e flexível para gerenciar bilhões de nós interconectados, além de contar com um console integrado para execução de scripts analíticos em Cypher.

## Funcionalidades

- **Inserção Expressa (GUI):** Formulários visuais dinâmicos para criar nós e conexões instantaneamente, sem precisar digitar código.
- **Console Cypher Integrado:** Permite a execução direta de queries para fins de administração e desenvolvimento.
- **Rastreabilidade Temporal e Contextual:** Todos os relacionamentos criados via interface adicionam propriedades de carimbo de data/hora (`timestamp`) e dados contextuais (`reaction`).

---

## Requisitos e Preparação do Ambiente

### 1. Banco de Dados Neo4j
Certifique-se de possuir uma instância do **Neo4j** (local via Neo4j Desktop, via Docker ou na nuvem pelo Neo4j Aura) ativa.

Se preferir subir rapidamente via **Docker**, utilize o comando:
```bash
docker run \
    --name neo4j-x4good \
    -p 7474:7474 -p 7687:7687 \
    -d \
    -e NEO4J_AUTH=neo4j/sua_senha_aqui \
    neo4j:latest