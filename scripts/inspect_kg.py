"""Read-only evidence snapshot of the current Neo4j graph after benchmarking."""
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from dotenv import load_dotenv
from src.graph import Neo4jGraph

QUERIES = {
    "article_255": "MATCH (a:Article)-[:HAS_CLAUSE]->(cl:Clause) WHERE a.doc_id = 'blhs-dieu-255' RETURN a.id AS article, cl.number AS number, cl.penalty AS penalty, cl.text AS text ORDER BY number",
    "duplicate_substances": "MATCH (s:Substance) WITH toLower(s.name) AS normalized, collect(s.name) AS names, count(*) AS n WHERE n > 1 RETURN normalized, names, n ORDER BY normalized",
    "counts": "MATCH (n) RETURN labels(n)[0] AS label, count(*) AS n ORDER BY n DESC",
    "relationships": "MATCH ()-[r]->() RETURN type(r) AS type, count(*) AS n ORDER BY n DESC",
    "broken_bridges": "MATCH (k:Case) WHERE NOT (k)-[:CHARGED_WITH]->() RETURN k.name AS name, k.doc_id AS doc_id, k.summary AS summary",
    "substances": "MATCH (s:Substance) RETURN s.name AS name ORDER BY toLower(s.name)",
    "empty_charges": "MATCH (p:Person)-[r:INVOLVED_IN]->(k:Case) WHERE r.charge = '' RETURN p.name AS person, r.role AS role, k.name AS case_name, k.doc_id AS doc_id",
    "mdma_cases": "MATCH (k:Case)-[:INVOLVES]->(s:Substance) WHERE toLower(s.name) = 'mdma' RETURN DISTINCT k.name AS name, k.doc_id AS doc_id, k.summary AS summary ORDER BY name",
    "crime_bridge": "MATCH (p:Person)-[:INVOLVED_IN]->(k:Case)-[:CHARGED_WITH]->(c:Crime)<-[:DEFINES]-(a:Article) RETURN p.name AS person, k.name AS case_name, c.name AS crime, a.id AS article ORDER BY person",
}

def main():
    load_dotenv(Path(__file__).resolve().parents[1] / '.env')
    graph = Neo4jGraph(os.getenv('NEO4J_URI', 'bolt://localhost:7687'), os.getenv('NEO4J_USER', 'neo4j'), os.getenv('NEO4J_PASSWORD', 'password123'))
    try:
        evidence = {name: {"cypher": query, "rows": graph.run(query)} for name, query in QUERIES.items()}
        questions = json.loads(Path('data/benchmark_kg.json').read_text(encoding='utf-8'))
        evidence['contexts_without_vector'] = {q['id']: graph.context(q['question'], []) for q in questions}
        Path('report/kg_evidence.json').write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        print('Saved report/kg_evidence.json')
    finally:
        graph.close()

if __name__ == '__main__':
    main()
