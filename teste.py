from neo4j import GraphDatabase, TrustSystemCAs

uri = "neo4j+s://ddd06f2d.databases.neo4j.io"

driver = GraphDatabase.driver(
    uri,
    auth=(
        "ddd06f2d",
        "Uttnfl0s2VLUnpRl2Oya-X6TaeqR6ndk6TRKkIxT4vM"
    ),
    trusted_certificates=TrustSystemCAs()
)

try:

    driver.verify_connectivity()

    print("Conectado!")

except Exception as e:

    print(type(e))

    print(e)