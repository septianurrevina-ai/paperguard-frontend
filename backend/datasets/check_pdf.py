import sqlite3

db_path = r"C:\Users\DAVID\.cache\kagglehub\datasets\dipeshlohchab\arxiv-research-papers\versions\1\data\db\documents.db"

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

result = cursor.execute("""
    SELECT id, title, local_path
    FROM documents
    WHERE id = 'arxiv_adap-org_9712004'
""").fetchone()

print(result)

conn.close()