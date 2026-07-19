import sqlite3
c = sqlite3.connect('saas.db')
print([x[0] for x in c.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()])
