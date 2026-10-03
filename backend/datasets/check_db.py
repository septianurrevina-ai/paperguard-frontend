import sqlite3

path = r"C:\Users\DAVID\.cache\kagglehub\datasets\dipeshlohchab\arxiv-research-papers\versions\1\data\db\documents.db"

conn = sqlite3.connect(path)
cursor = conn.cursor()

papers = cursor.execute("""
    SELECT id, title, source, license
    FROM documents
    LIMIT 10
""").fetchall()

for paper in papers:
    print(paper)

conn.close()