import os
import psycopg2
from flask import Flask, render_template_string, request, redirect

app = Flask(__name__)

DATABASE_URL = os.environ.get("DATABASE_URL")

def get_conn():
    conn = psycopg2.connect(DATABASE_URL)
    return conn

def init_db():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS equipos (
            id SERIAL PRIMARY KEY,
            nombre TEXT,
            categoria TEXT,
            contacto TEXT
        )
    """)
    conn.commit()
    cur.close()
    conn.close()

init_db()

HTML = """
<!DOCTYPE html>
<html><head><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Toros Chihuahua</title></head>
<body style="font-family:Arial; padding:20px; max-width:600px; margin:auto;">
<h1>Toros Chihuahua - Registro</h1>
<form method="POST" action="/agregar">
<input name="nombre" placeholder="Nombre del equipo" required style="width:100%;padding:10px;margin:5px 0"><br>
<input name="categoria" placeholder="Categoria" required style="width:100%;padding:10px;margin:5px 0"><br>
<input name="contacto" placeholder="Contacto" required style="width:100%;padding:10px;margin:5px 0"><br>
<button style="width:100%;padding:12px;background:#111;color:#fff;">Agregar Equipo</button>
</form>
<hr>
<h2>Equipos Registrados ({{ equipos|length }})</h2>
{% for e in equipos %}
<div style="border:1px solid #ccc;padding:10px;margin:5px 0;">{{ e[1] }} - {{ e[2] }} - {{ e[3] }} <a href="/eliminar/{{ e[0] }}" style="color:red;float:right;">Eliminar</a></div>
{% endfor %}
</body></html>
"""

@app.route("/")
def index():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM equipos ORDER BY id DESC")
    equipos = cur.fetchall()
    cur.close()
    conn.close()
    return render_template_string(HTML, equipos=equipos)

@app.route("/agregar", methods=["POST"])
def agregar():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("INSERT INTO equipos (nombre, categoria, contacto) VALUES (%s, %s, %s)",
                (request.form["nombre"], request.form["categoria"], request.form["contacto"]))
    conn.commit()
    cur.close()
    conn.close()
    return redirect("/")

@app.route("/eliminar/<int:id>")
def eliminar(id):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("DELETE FROM equipos WHERE id = %s", (id,))
    conn.commit()
    cur.close()
    conn.close()
    return redirect("/")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
