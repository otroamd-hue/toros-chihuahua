from flask import Flask, request, redirect, send_file, session
import os, urllib.parse, psycopg2
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from functools import wraps

app = Flask(__name__)
app.secret_key = "toros_chihuahua_2026_v3"
ESCUELA = "Club Toros Futbol Chihuahua"

DATABASE_URL = os.environ.get("DATABASE_URL")

def get_con():
    return psycopg2.connect(DATABASE_URL)

def init_db():
    con = get_con(); cur = con.cursor()
    cur.execute("CREATE TABLE IF NOT EXISTS categorias(nombre TEXT PRIMARY KEY, precio REAL)")
    cur.execute("CREATE TABLE IF NOT EXISTS alumnos(id SERIAL PRIMARY KEY, nombre TEXT, tel TEXT, categoria TEXT, beca INTEGER, credito REAL DEFAULT 0)")
    cur.execute("CREATE TABLE IF NOT EXISTS mensualidades(id SERIAL PRIMARY KEY, alumno_id INTEGER, mes TEXT, debe REAL, pagado REAL DEFAULT 0, estado TEXT DEFAULT 'DEBE')")
    cur.execute("CREATE TABLE IF NOT EXISTS pagos(id SERIAL PRIMARY KEY, alumno_id INTEGER, alumno_nombre TEXT, mes TEXT, monto REAL, fecha TEXT, nota TEXT)")
    cur.execute("CREATE TABLE IF NOT EXISTS entregas(id SERIAL PRIMARY KEY, monto REAL, fecha TEXT)")
    cur.execute("CREATE TABLE IF NOT EXISTS gastos(id SERIAL PRIMARY KEY, concepto TEXT, monto REAL, fecha TEXT)")
    cur.execute("CREATE TABLE IF NOT EXISTS config(clave TEXT PRIMARY KEY, valor TEXT)")
    con.commit()
    cur.close(); con.close()
    if not get_config('profe1_nombre'): set_config('profe1_nombre','chuy')
    if not get_config('profe2_nombre'): set_config('profe2_nombre','Dueño')
    if not get_config('profe3_nombre'): set_config('profe3_nombre','Esposa')
    if not get_config('pass_profe1'): set_config('pass_profe1','1111')
    if not get_config('pass_admin'): set_config('pass_admin','1234')
    if not get_config('pass_profe3'): set_config('pass_profe3','2222')

def get_config(clave, default=""):
    try:
        con=get_con(); cur=con.cursor()
        cur.execute("CREATE TABLE IF NOT EXISTS config(clave TEXT PRIMARY KEY, valor TEXT)")
        cur.execute("SELECT valor FROM config WHERE clave=%s",(clave,))
        r=cur.fetchone()
        con.commit(); cur.close(); con.close()
        return r[0] if r else default
    except: return default

def set_config(clave, valor):
    con=get_con(); cur=con.cursor()
    cur.execute("CREATE TABLE IF NOT EXISTS config(clave TEXT PRIMARY KEY, valor TEXT)")
    cur.execute("INSERT INTO config(clave, valor) VALUES(%s,%s) ON CONFLICT(clave) DO UPDATE SET valor=EXCLUDED.valor",(clave, valor))
    con.commit(); cur.close(); con.close()

def get_pass_p1(): return get_config('pass_profe1','1111')
def get_pass_p2(): return get_config('pass_admin','1234')
def get_pass_p3(): return get_config('pass_profe3','2222')

# Ejecuta init al arrancar
try:
    if DATABASE_URL: init_db()
except Exception as e: print("INIT DB ERROR", e)

def get_saldos():
    con=get_con(); cur=con.cursor()
    cur.execute("SELECT SUM(monto) FROM pagos"); tp=cur.fetchone()[0] or 0
    cur.execute("SELECT SUM(monto) FROM entregas"); te=cur.fetchone()[0] or 0
    cur.execute("SELECT SUM(monto) FROM gastos"); tg=cur.fetchone()[0] or 0
    cur.close(); con.close()
    return tp, te, tg, tp-te, te-tg

def meses_lista():
    año_actual = datetime.now().year
    lista=[]
    for y in range(2024, año_actual + 3):
        for m in range(1,13):
            lista.append(f"{y}-{m:02d}")
    return lista

mes_global = datetime.now().strftime("%Y-%m")

def login_required(f):
    @wraps(f)
    def dec(*args, **kwargs):
        if 'rol' not in session: return redirect("/login")
        return f(*args, **kwargs)
    return dec

def admin_required(f):
    @wraps(f)
    def dec(*args, **kwargs):
        if session.get('rol') not in ['p2','p3','admin']:
            return menu_html("<h3 style='color:red'>Solo Admin (Dueño / Esposa) puede entrar aquí</h3>", mes_global)
        return f(*args, **kwargs)
    return dec

def menu_html(content, mes_actual=None):
    if not mes_actual: mes_actual=mes_global
    opts="".join([f"<option value='{m}' {'selected' if m==mes_actual else ''}>{m}</option>" for m in meses_lista()[::-1]])
    p1=get_config('profe1_nombre','Profe 1'); p2=get_config('profe2_nombre','Profe 2'); p3=get_config('profe3_nombre','Profe 3')
    rol=session.get('rol','')
    if rol=='p1': badge=f"<span style='background:#fbbc05;padding:4px 8px;border-radius:5px'>{p1}</span>"
    elif rol=='p2': badge=f"<span style='background:green;color:white;padding:4px 8px;border-radius:5px'>{p2} ADMIN</span>"
    elif rol=='p3': badge=f"<span style='background:blue;color:white;padding:4px 8px;border-radius:5px'>{p3} ADMIN</span>"
    else: badge=""
    return f"<meta name='viewport' content='width=device-width, initial-scale=1'><style>body{{font-family:Arial;padding:12px}}.btn{{display:block;padding:14px;margin:8px 0;background:#1a73e8;color:white;text-align:center;text-decoration:none;border-radius:10px}}.btn2{{background:#34a853}}.btn3{{background:#fbbc05;color:black}}.btn4{{background:#ea4335}} input,select,textarea{{padding:10px;margin:4px}} table{{width:100%;border-collapse:collapse}} td,th{{border:1px solid #ccc;padding:6px;font-size:13px}}</style><div style='display:flex;justify-content:space-between'><a href='/' style='text-decoration:none'><h3>🐂 TOROS</h3></a><div>{badge} <a href='/logout'>Salir</a></div></div><form action='/setmes'>Mes:<select name='mes' onchange='this.form.submit()'>{opts}</select></form>{content}<br><a href='/'>← INICIO</a>"

@app.route("/login", methods=["GET","POST"])
def login():
    if request.method=="POST":
        pw=request.form.get('pw','').strip()
        if pw==get_pass_p2(): session['rol']='p2'; return redirect("/")
        if pw==get_pass_p3(): session['rol']='p3'; return redirect("/")
        if pw==get_pass_p1(): session['rol']='p1'; return redirect("/")
        if pw==get_config('pass_admin','1234'): session['rol']='p2'; return redirect("/")
        return menu_html("<p style='color:red'>Pass incorrecto</p>", mes_global)
    return "<meta name='viewport' content='width=device-width, initial-scale=1'><style>body{font-family:Arial;padding:20px} input{padding:14px;width:90%;margin:10px 0}</style><h2>🐂 TOROS - Entrar</h2><form method='post'>Pass:<br><input name='pw' type='password' required><br><button style='padding:14px;background:black;color:white;width:100%'>Entrar</button></form>"

@app.route("/logout")
def logout(): session.clear(); return redirect("/login")

@app.route("/setmes")
@login_required
def setmes():
    global mes_global; mes_global=request.args.get('mes', mes_global); return redirect(request.referrer or "/")

@app.route("/")
@login_required
def inicio():
    tp,te,tg,caja,saldo=get_saldos()
    p1=get_config('profe1_nombre','chuy'); p2=get_config('profe2_nombre','Profe 2'); p3=get_config('profe3_nombre','Esposa')
    if session.get('rol')=='p1':
        return menu_html(f"<div style='background:#e8f0fe;padding:10px;border-radius:10px'>Hola <b>{p1}</b><br>Mes: <b>{mes_global}</b><br>CAJA {p1}: ${caja}</div><a class='btn btn3' href='/cobrar'>1. COBRAR {mes_global}</a><a class='btn' style='background:#000' href='/reporte'>2. Reporte</a>", mes_global)
    return menu_html(f"<div style='background:#e8f0fe;padding:10px;border-radius:10px'><b>{p1} / {p2} / {p3}</b> - Mes: <b>{mes_global}</b><br>CAJA {p1}: ${caja} | SALDO ADMIN: ${saldo}</div><a class='btn' href='/categorias'>1. Categorias</a><a class='btn btn2' href='/alumnos'>2. Alumnos</a><a class='btn btn3' href='/cobrar'>3. COBRAR {mes_global}</a><a class='btn' href='/caja'>4. Caja {p1}-> Admin</a><a class='btn btn4' href='/gastos'>5. Gastos</a><a class='btn' style='background:#000' href='/reporte'>6. Reporte</a><a class='btn' style='background:#666' href='/config'>⚙️ Config (Pass y Nombres)</a>", mes_global)

@app.route("/categorias")
@login_required
@admin_required
def categorias():
    con=get_con(); cur=con.cursor(); cur.execute("SELECT * FROM categorias"); cats=cur.fetchall(); cur.close(); con.close()
    rows="".join([f"<tr><td>{c[0]}</td><td>${c[1]}</td><td><a href='/categorias/editar/{urllib.parse.quote(c[0])}' style='background:#1a73e8;color:white;padding:6px 10px;border-radius:5px;text-decoration:none'>Editar</a></td></tr>" for c in cats])
    return menu_html(f"<h3>Categorias</h3><form action='/categorias/add' method='post'><input name='nombre' placeholder='Nombre' required><input name='precio' type='number' placeholder='Precio' required><button>Agregar</button></form><table><tr><th>Nombre</th><th>Precio</th><th>Acc</th></tr>{rows}</table>", mes_global)

@app.route("/categorias/add", methods=["POST"])
@login_required
@admin_required
def categorias_add():
    con=get_con(); cur=con.cursor(); cur.execute("INSERT INTO categorias VALUES(%s,%s) ON CONFLICT(nombre) DO NOTHING",(request.form['nombre'], float(request.form['precio']))); con.commit(); cur.close(); con.close(); return redirect("/categorias")

@app.route("/categorias/editar/<n>", methods=["GET","POST"])
@login_required
@admin_required
def cat_editar(n):
    n = urllib.parse.unquote(n)
    con=get_con(); cur=con.cursor(); cur.execute("SELECT * FROM categorias WHERE nombre=%s",(n,)); cat=cur.fetchone()
    if not cat: cur.close(); con.close(); return redirect("/categorias")
    if request.method=="POST":
        nuevo_nombre=request.form['nombre'].strip(); nuevo_precio=float(request.form['precio'])
        cur.execute("UPDATE categorias SET nombre=%s, precio=%s WHERE nombre=%s",(nuevo_nombre, nuevo_precio, n))
        cur.execute("UPDATE alumnos SET categoria=%s WHERE categoria=%s",(nuevo_nombre, n))
        con.commit(); cur.close(); con.close(); return redirect("/categorias")
    cur.close(); con.close()
    return menu_html(f"<h3>Editar Categoria: {n}</h3><form method='post'>Nombre:<br><input name='nombre' value='{cat[0]}' required style='width:95%'><br>Precio:<br><input name='precio' type='number' step='0.01' value='{cat[1]}' required style='width:95%'><br><br><button style='padding:12px;background:green;color:white;width:100%;border-radius:8px'>💾 Guardar cambios</button></form><hr style='margin:20px 0'><h4 style='color:red'>Zona de peligro - Borrar</h4><form action='/categorias/borrar/{urllib.parse.quote(n)}' method='post' onsubmit=\"return confirm('¿ESTAS 100% SEGURO de BORRAR {n}?')\">Pass Admin para borrar:<br><input name='pass' type='password' required placeholder='Pon tu pass de Dueño/Esposa' style='width:95%;border:2px solid red'><br><br><button style='padding:12px;background:#ea4335;color:white;width:100%;border-radius:8px'>🗑️ BORRAR DEFINITIVAMENTE</button></form>", mes_global)

@app.route("/categorias/borrar/<n>", methods=["POST"])
@login_required
@admin_required
def cat_borrar(n):
    n = urllib.parse.unquote(n)
    if request.form.get('pass') not in [get_pass_p2(), get_pass_p3(), get_config('pass_admin','1234')]: return menu_html("<h3 style='color:red'>Pass incorrecto - No se borró nada</h3>", mes_global)
    con=get_con(); cur=con.cursor(); cur.execute("DELETE FROM categorias WHERE nombre=%s",(n,)); con.commit(); cur.close(); con.close(); return redirect("/categorias")

@app.route("/alumnos")
@login_required
@admin_required
def alumnos():
    con=get_con(); cur=con.cursor(); cur.execute("SELECT * FROM categorias"); cats=cur.fetchall(); cur.execute("SELECT * FROM alumnos ORDER BY id"); als=cur.fetchall(); cur.execute("SELECT COUNT(*) FROM mensualidades WHERE mes=%s",(mes_global,)); count_mes=cur.fetchone()[0]; cur.close(); con.close()
    opt="".join([f"<option value='{c[0]}'>{c[0]} - ${c[1]}</option>" for c in cats])
    rows=""
    for a in als: rows+=f"<tr><td>{a[1]}</td><td>{a[2]}</td><td>{a[3]}</td><td>${a[5]}</td><td><a href='/wapp/{a[0]}' style='background:#25D366;color:white;padding:6px 10px;border-radius:5px;text-decoration:none'>WA</a> <a href='/alumnos/editar/{a[0]}' style='background:#1a73e8;color:white;padding:6px 10px;border-radius:5px;text-decoration:none;margin-left:4px'>Editar</a></td></tr>"
    return menu_html(f"<h3>Alumnos - {mes_global} ({count_mes}/{len(als)})</h3><form action='/alumnos/generar_mes' method='post'><button style='background:green;color:white;padding:12px'>GENERAR COBRO {mes_global}</button></form><form action='/alumnos/add' method='post'>Nombre:<input name='nombre' required> Tel:<input name='tel' required> Cat:<select name='categoria' required>{opt}</select> Beca:<select name='beca'><option value='0'>0%</option><option value='50'>50%</option></select><button>Agregar</button></form><table><tr><th>Nombre</th><th>Tel</th><th>Cat</th><th>Cred</th><th>Acc</th></tr>{rows}</table>", mes_global)

@app.route("/alumnos/add", methods=["POST"])
@login_required
@admin_required
def alumnos_add():
    con=get_con(); cur=con.cursor(); cur.execute("INSERT INTO alumnos(nombre, tel, categoria, beca, credito) VALUES(%s,%s,%s,%s,0)",(request.form['nombre'], request.form['tel'], request.form['categoria'], int(request.form['beca']))); con.commit(); cur.close(); con.close(); return redirect("/alumnos")

@app.route("/alumnos/editar/<int:id>", methods=["GET","POST"])
@login_required
@admin_required
def alumnos_editar(id):
    con=get_con(); cur=con.cursor(); cur.execute("SELECT * FROM alumnos WHERE id=%s",(id,)); a=cur.fetchone(); cur.execute("SELECT * FROM categorias"); cats=cur.fetchall()
    if not a: cur.close(); con.close(); return redirect("/alumnos")
    if request.method=="POST":
        nombre=request.form['nombre'].strip(); tel=request.form['tel'].strip(); categoria=request.form['categoria']; beca=int(request.form['beca']); credito=float(request.form.get('credito',0))
        cur.execute("UPDATE alumnos SET nombre=%s, tel=%s, categoria=%s, beca=%s, credito=%s WHERE id=%s",(nombre, tel, categoria, beca, credito, id)); con.commit(); cur.close(); con.close(); return redirect("/alumnos")
    opt="".join([f"<option value='{c[0]}' {'selected' if c[0]==a[3] else ''}>{c[0]}</option>" for c in cats])
    beca_opt=f"<option value='0' {'selected' if a[4]==0 else ''}>0%</option><option value='50' {'selected' if a[4]==50 else ''}>50%</option><option value='100' {'selected' if a[4]==100 else ''}>100%</option>"
    cur.close(); con.close()
    return menu_html(f"<h3>Editar Alumno: {a[1]}</h3><form method='post'>Nombre:<br><input name='nombre' value='{a[1]}' required style='width:95%'><br>Tel:<br><input name='tel' value='{a[2]}' required style='width:95%'><br>Categoria:<br><select name='categoria' style='width:98%;padding:10px'>{opt}</select><br>Beca:<br><select name='beca' style='width:98%;padding:10px'>{beca_opt}</select><br>Credito:<br><input name='credito' type='number' step='0.01' value='{a[5]}' style='width:95%'><br><br><button style='padding:12px;background:green;color:white;width:100%;border-radius:8px'>💾 Guardar cambios</button></form><hr><h4 style='color:red'>Borrar alumno</h4><form action='/alumnos/borrar/{a[0]}' method='post' onsubmit=\"return confirm('¿BORRAR a {a[1]}?')\">Pass Admin:<br><input name='pass' type='password' required style='width:95%;border:2px solid red'><br><br><button style='padding:12px;background:#ea4335;color:white;width:100%;border-radius:8px'>🗑️ BORRAR ALUMNO</button></form>", mes_global)

@app.route("/alumnos/borrar/<int:id>", methods=["POST"])
@login_required
@admin_required
def alumnos_borrar(id):
    if request.form.get('pass') not in [get_pass_p2(), get_pass_p3(), get_config('pass_admin','1234')]: return menu_html("<h3 style='color:red'>Pass incorrecto</h3>", mes_global)
    con=get_con(); cur=con.cursor(); cur.execute("DELETE FROM alumnos WHERE id=%s",(id,)); cur.execute("DELETE FROM mensualidades WHERE alumno_id=%s",(id,)); con.commit(); cur.close(); con.close(); return redirect("/alumnos")

@app.route("/alumnos/generar_mes", methods=["POST"])
@login_required
@admin_required
def generar_mes():
    con=get_con(); cur=con.cursor(); cur.execute("SELECT * FROM alumnos"); als=cur.fetchall()
    for a in als:
        cur.execute("SELECT id FROM mensualidades WHERE alumno_id=%s AND mes=%s",(a[0], mes_global))
        if not cur.fetchone():
            cur.execute("SELECT precio FROM categorias WHERE nombre=%s",(a[3],)); cat=cur.fetchone()
            if cat:
                precio=cat[0]*(1-a[4]/100); debe_real=max(0, precio-a[5]); nuevo_credito=max(0, a[5]-precio)
                cur.execute("INSERT INTO mensualidades(alumno_id, mes, debe, pagado, estado) VALUES(%s,%s,%s,%s,%s)",(a[0], mes_global, debe_real, 0, 'DEBE' if debe_real>0 else 'PAGADO')); cur.execute("UPDATE alumnos SET credito=%s WHERE id=%s",(nuevo_credito, a[0]))
    con.commit(); cur.close(); con.close(); return redirect("/alumnos")

@app.route("/cobrar")
@login_required
def cobrar():
    q=request.args.get('q',''); con=get_con(); cur=con.cursor()
    if q: cur.execute("SELECT a.id, a.nombre, a.tel, a.categoria, a.credito, m.debe, m.pagado, m.estado FROM alumnos a LEFT JOIN mensualidades m ON a.id=m.alumno_id AND m.mes=%s WHERE a.nombre ILIKE %s",(mes_global, '%'+q+'%'))
    else: cur.execute("SELECT a.id, a.nombre, a.tel, a.categoria, a.credito, m.debe, m.pagado, m.estado FROM alumnos a LEFT JOIN mensualidades m ON a.id=m.alumno_id AND m.mes=%s",(mes_global,))
    datos=cur.fetchall(); cur.execute("SELECT * FROM pagos WHERE mes=%s OR mes LIKE %s ORDER BY id DESC",(mes_global, '%'+mes_global+'%')); pagos_mes=cur.fetchall(); cur.close(); con.close()
    rows=""; morosos=[]
    for d in datos:
        if d[5] is None: continue
        por=d[5]-d[6]; color='red' if por>0 else 'green'
        if por>0: morosos.append(d)
        rows+=f"<tr><td>{d[1]}</td><td>{d[2]}</td><td>${d[5]}</td><td>${d[6]}</td><td style='color:{color}'><b>${por}</b></td><td><a class='btn' href='/cobrar/{d[0]}/{mes_global}'>Cobrar</a></td></tr>"
    html_mor=""
    for m in morosos:
        por=m[5]-m[6]; msg=f"Hola, soy del {ESCUELA}. Alumno: {m[1]}. Adeudo ${por} Mes: {mes_global}."; wa=f"https://wa.me/52{m[2]}?text={urllib.parse.quote(msg)}" if m[2] else "#"
        html_mor+=f"<tr><td>{m[1]}</td><td>{m[2]}</td><td>${por}</td><td><a href='{wa}' target='_blank' style='background:#25D366;color:white;padding:8px;border-radius:5px;text-decoration:none'>WA</a></td></tr>"
    html_p="".join([f"<tr><td>{p[5]}</td><td>{p[2]}</td><td>{p[3]}</td><td>${p[4]}</td><td><a href='/recibo/{p[0]}'>Ver</a></td></tr>" for p in pagos_mes])
    return menu_html(f"<h3>Cobrar {mes_global}</h3><form method='get'><input name='q' value='{q}' placeholder='Buscar'><button>Buscar</button></form><h4>Por cobrar</h4><table><tr><th>Alumno</th><th>Tel</th><th>Debe</th><th>Pagado</th><th>Falta</th><th>Acc</th></tr>{rows}</table><h4 style='color:red'>Morosos</h4><table>{html_mor}</table><h4>Pagos</h4><table>{html_p}</table>", mes_global)

@app.route("/cobrar/<int:alumno_id>/<mes>")
@login_required
def cobrar_form(alumno_id, mes):
    con=get_con(); cur=con.cursor(); cur.execute("SELECT * FROM alumnos WHERE id=%s",(alumno_id,)); a=cur.fetchone(); cur.execute("SELECT * FROM mensualidades WHERE alumno_id=%s AND mes=%s",(alumno_id, mes)); m=cur.fetchone(); cur.close(); con.close()
    por=m[3]-m[4] if m else 0; rol=session.get('rol'); p1=get_config('profe1_nombre','chuy'); dest=f"CAJA {p1}" if rol=='p1' else "SALDO ADMIN"
    return menu_html(f"<h3>{a[1]} - {mes}</h3><p>Debe: ${por} -> {dest}</p><form action='/cobrar/pagar/{alumno_id}/{mes}' method='post'>Tipo:<select name='tipo' id='tipo' onchange='cambioTipo()' style='width:100%;padding:12px'><option value='MENSUALIDAD'>MENSUALIDAD {mes}</option><option value='UNIFORME'>UNIFORME</option><option value='ARBITRAJE'>ARBITRAJE</option><option value='INSCRIPCION'>INSCRIPCION</option><option value='OTRO'>OTRO</option></select><br>Concepto:<input name='concepto_final' id='concepto_final' value='{mes}' readonly style='background:#eee'><br>Monto:<input name='monto' id='monto' type='number' step='0.01' value='{por}' required><br>Nota:<input name='nota'><br><br><button style='background:green;color:white;padding:15px;width:100%'>PAGAR a {dest}</button></form><script>function cambioTipo(){{let t=document.getElementById('tipo').value;let c=document.getElementById('concepto_final');let m=document.getElementById('monto');if(t=='MENSUALIDAD'){{c.value='{mes}';c.readOnly=true;m.value='{por}';}}else{{c.value=t;c.readOnly=false;m.value='';}}}}</script>", mes)

@app.route("/cobrar/pagar/<int:alumno_id>/<mes>", methods=["POST"])
@login_required
def cobrar_pagar(alumno_id, mes):
    monto=float(request.form['monto']); nota=request.form['nota']; tipo=request.form.get('tipo','MENSUALIDAD'); concepto_final=request.form.get('concepto_final', mes).strip().upper() or tipo
    p1=get_config('profe1_nombre','chuy'); p2=get_config('profe2_nombre','Dueño'); p3=get_config('profe3_nombre','Esposa')
    rol=session.get('rol')
    if rol=='p1': quien_nombre=p1; quien='p1'
    elif rol=='p3': quien_nombre=p3; quien='p3'
    else: quien_nombre=p2; quien='p2'
    con=get_con(); cur=con.cursor(); cur.execute("SELECT * FROM alumnos WHERE id=%s",(alumno_id,)); a=cur.fetchone(); cur.execute("SELECT * FROM mensualidades WHERE alumno_id=%s AND mes=%s",(alumno_id, mes)); m=cur.fetchone(); por=m[3]-m[4] if m else 0
    nota_final=f"[{quien_nombre} - {tipo}] {nota}" if nota else f"[{quien_nombre} - {tipo}]"
    cur.execute("INSERT INTO pagos(alumno_id, alumno_nombre, mes, monto, fecha, nota) VALUES(%s,%s,%s,%s,%s,%s) RETURNING id",(alumno_id, a[1], concepto_final, monto, datetime.now().strftime("%Y-%m-%d %H:%M"), nota_final)); pago_id=cur.fetchone()[0]
    if tipo=='MENSUALIDAD' and m:
        if monto < por: cur.execute("UPDATE mensualidades SET pagado=pagado+%s, estado='ABONO' WHERE id=%s",(monto, m[0]))
        else:
            sob=monto-por; cur.execute("UPDATE mensualidades SET pagado=debe, estado='PAGADO' WHERE id=%s",(m[0],))
            if sob>0: cur.execute("UPDATE alumnos SET credito=credito+%s WHERE id=%s",(sob, alumno_id))
    if quien in ['p2','p3']:
        cur.execute("INSERT INTO entregas(monto, fecha) VALUES(%s,%s)",(monto, f"{datetime.now().strftime('%Y-%m-%d %H:%M')} AUTO {quien_nombre} {tipo}"))
    con.commit(); cur.close(); con.close(); return redirect(f"/recibo/{pago_id}")

@app.route("/recibo/<int:pago_id>")
@login_required
def recibo(pago_id):
    con=get_con(); cur=con.cursor(); cur.execute("SELECT * FROM pagos WHERE id=%s",(pago_id,)); p=cur.fetchone()
    tel=None
    if p:
        cur.execute("SELECT tel FROM alumnos WHERE id=%s",(p[1],)); t=cur.fetchone(); tel=t[0] if t else ""
    cur.close(); con.close()
    if not p: return "No existe"
    filename=f"recibo_{pago_id}.pdf"; path=os.path.join("/tmp", filename)
    c=canvas.Canvas(path, pagesize=letter); c.setFont("Helvetica-Bold", 16); c.drawString(50, 750, ESCUELA); c.setFont("Helvetica", 12); c.drawString(50, 730, f"Folio: {p[0]}"); c.drawString(50, 710, f"Fecha: {p[5]}"); c.drawString(50, 690, f"Alumno: {p[2]}"); c.drawString(50, 670, f"Concepto: {p[3]}"); c.drawString(50, 650, f"Monto: ${p[4]}"); c.drawString(50, 630, f"Nota: {p[6]}"); c.save()
    msg=f"Hola, recibo {ESCUELA}. Alumno: {p[2]} Concepto: {p[3]} Monto: ${p[4]} Folio: {p[0]} Nota: {p[6]}"; wa=f"https://wa.me/52{tel}?text={urllib.parse.quote(msg)}" if tel else f"https://wa.me/?text={urllib.parse.quote(msg)}"
    return menu_html(f"<div style='text-align:center'><h2 style='color:green'>✓ Pago registrado</h2><a href='/recibo_pdf/{pago_id}' target='_blank' class='btn' style='background:#000'>📄 PDF</a><a href='{wa}' target='_blank' class='btn' style='background:#25D366'>💬 WhatsApp a {tel}</a><a href='/cobrar' class='btn btn3'>← Seguir cobrando</a></div>", mes_global)

@app.route("/recibo_pdf/<int:pago_id>")
@login_required
def recibo_pdf(pago_id):
    return send_file(os.path.join("/tmp", f"recibo_{pago_id}.pdf"), as_attachment=True)

@app.route("/wapp/<int:alumno_id>", methods=["GET", "POST"])
@login_required
def wapp_alumno(alumno_id):
    con=get_con(); cur=con.cursor(); cur.execute("SELECT * FROM alumnos WHERE id=%s",(alumno_id,)); a=cur.fetchone(); cur.close(); con.close()
    if not a: return "Alumno no existe"
    if request.method=="POST":
        msg=request.form.get('msg',''); wa=f"https://wa.me/52{a[2]}?text={urllib.parse.quote(msg)}"; return redirect(wa)
    msg_default=f"Hola, soy del {ESCUELA}. Alumno: {a[1]}. Te escribo para avisarte de..."
    return menu_html(f"<h3>WhatsApp a {a[1]} - {a[2]}</h3><form method='post'>Mensaje:<br><textarea name='msg' rows='5' style='width:100%; padding:12px'>{msg_default}</textarea><br><br><button style='background:#25D366;color:white;padding:15px;width:100%;border-radius:10px'>💬 Enviar WhatsApp</button></form><a href='/alumnos' class='btn' style='background:#666'>← Volver</a>", mes_global)

@app.route("/caja")
@login_required
@admin_required
def caja():
    tp,te,tg,caja,saldo=get_saldos()
    return menu_html(f"<h3>Caja chuy: ${caja}</h3><form action='/entregar' method='post'>Monto:<input name='monto' type='number' max='{caja}' required> Pass Admin:<input name='pass' type='password' required><button>Entregar a Admin</button></form>", mes_global)

@app.route("/entregar", methods=["POST"])
@login_required
@admin_required
def entregar():
    if request.form.get('pass') not in [get_pass_p2(), get_pass_p3(), get_config('pass_admin','1234')]: return menu_html("Pass incorrecto")
    con=get_con(); cur=con.cursor(); cur.execute("INSERT INTO entregas(monto, fecha) VALUES(%s,%s)",(float(request.form['monto']), datetime.now().strftime("%Y-%m-%d %H:%M"))); con.commit(); cur.close(); con.close(); return redirect("/caja")

@app.route("/gastos")
@login_required
@admin_required
def gastos():
    tp,te,tg,caja,saldo=get_saldos(); con=get_con(); cur=con.cursor(); cur.execute("SELECT * FROM gastos ORDER BY id DESC"); gs=cur.fetchall(); cur.close(); con.close();
    rows="".join([f"<tr><td>{g[3]}</td><td>{g[1]}</td><td>${g[2]}</td><td><a href='/gastos/editar/{g[0]}' style='background:#1a73e8;color:white;padding:6px 10px;border-radius:5px;text-decoration:none'>Editar</a></td></tr>" for g in gs])
    return menu_html(f"<h3>Gastos Saldo ${saldo}</h3><form action='/gastos/add' method='post'>Concepto:<input name='concepto' required> Monto:<input name='monto' type='number' required> Pass:<input name='pass' type='password' required><button>Gasto</button></form><table><tr><th>Fecha</th><th>Concepto</th><th>Monto</th><th>Acc</th></tr>{rows}</table>", mes_global)

@app.route("/gastos/editar/<int:id>", methods=["GET","POST"])
@login_required
@admin_required
def gastos_editar(id):
    con=get_con(); cur=con.cursor(); cur.execute("SELECT * FROM gastos WHERE id=%s",(id,)); g=cur.fetchone()
    if not g: cur.close(); con.close(); return redirect("/gastos")
    if request.method=="POST":
        if request.form.get('pass') not in [get_pass_p2(), get_pass_p3(), get_config('pass_admin','1234')]: cur.close(); con.close(); return menu_html("Pass incorrecto", mes_global)
        concepto=request.form['concepto'].strip(); monto=float(request.form['monto']); cur.execute("UPDATE gastos SET concepto=%s, monto=%s WHERE id=%s",(concepto, monto, id)); con.commit(); cur.close(); con.close(); return redirect("/gastos")
    cur.close(); con.close()
    return menu_html(f"<h3>Editar Gasto #{g[0]}</h3><p>Fecha: {g[3]}</p><form method='post'>Concepto:<br><input name='concepto' value='{g[1]}' required style='width:95%'><br>Monto:<br><input name='monto' type='number' step='0.01' value='{g[2]}' required style='width:95%'><br>Pass Admin para guardar:<br><input name='pass' type='password' required style='width:95%'><br><br><button style='padding:12px;background:green;color:white;width:100%;border-radius:8px'>💾 Guardar cambios</button></form><hr><h4 style='color:red'>Borrar gasto</h4><form action='/gastos/borrar/{g[0]}' method='post' onsubmit=\"return confirm('¿BORRAR gasto ${g[2]}?')\">Pass Admin:<br><input name='pass' type='password' required style='width:95%;border:2px solid red'><br><br><button style='padding:12px;background:#ea4335;color:white;width:100%;border-radius:8px'>🗑️ BORRAR GASTO</button></form>", mes_global)

@app.route("/gastos/borrar/<int:id>", methods=["POST"])
@login_required
@admin_required
def gastos_borrar(id):
    if request.form.get('pass') not in [get_pass_p2(), get_pass_p3(), get_config('pass_admin','1234')]: return menu_html("<h3 style='color:red'>Pass incorrecto</h3>", mes_global)
    con=get_con(); cur=con.cursor(); cur.execute("DELETE FROM gastos WHERE id=%s",(id,)); con.commit(); cur.close(); con.close(); return redirect("/gastos")

@app.route("/gastos/add", methods=["POST"])
@login_required
@admin_required
def gastos_add():
    if request.form.get('pass') not in [get_pass_p2(), get_pass_p3(), get_config('pass_admin','1234')]: return menu_html("Pass incorrecto")
    con=get_con(); cur=con.cursor(); cur.execute("INSERT INTO gastos(concepto, monto, fecha) VALUES(%s,%s,%s)",(request.form['concepto'], float(request.form['monto']), datetime.now().strftime("%Y-%m-%d %H:%M"))); con.commit(); cur.close(); con.close(); return redirect("/gastos")

@app.route("/reporte")
@login_required
def reporte():
    tp,te,tg,caja,saldo=get_saldos(); con=get_con(); cur=con.cursor(); cur.execute("SELECT mes, SUM(debe), SUM(pagado) FROM mensualidades GROUP BY mes ORDER BY mes"); por_mes=cur.fetchall(); cur.close(); con.close(); rows="".join([f"<tr><td>{r[0]}</td><td>${r[1]}</td><td>${r[2]}</td></tr>" for r in por_mes])
    return menu_html(f"<h3>Reporte</h3><p>Cobrado:${tp} Entregado:${te} Gastos:${tg} Caja:${caja} Saldo:${saldo}</p><table>{rows}</table>", mes_global)

@app.route("/config", methods=["GET", "POST"])
@login_required
@admin_required
def config():
    p1=get_config('profe1_nombre','chuy'); p2=get_config('profe2_nombre','Dueño'); p3=get_config('profe3_nombre','Esposa')
    return menu_html(f"<h3>⚙️ Config Admin</h3><form action='/config/guardar' method='post'><fieldset><legend>Nombres</legend>Profe1:<input name='profe1' value='{p1}' required><br>Profe2 Dueño:<input name='profe2' value='{p2}' required><br>Profe3 Esposa:<input name='profe3' value='{p3}' required></fieldset><fieldset style='border:2px solid red'><legend>Passwords</legend>Pass {p1}:<input name='nuevo_p1' placeholder='actual: {get_pass_p1()}'><br>Pass {p2}:<input name='nuevo_p2' placeholder='actual: {get_pass_p2()}'><br>Pass {p3}:<input name='nuevo_p3' placeholder='actual: {get_pass_p3()}'></fieldset><button style='padding:12px;background:black;color:white;width:100%'>Guardar</button></form>", mes_global)

@app.route("/config/guardar", methods=["POST"])
@login_required
@admin_required
def config_guardar():
    if request.form.get('nuevo_p1','').strip(): set_config('pass_profe1', request.form.get('nuevo_p1').strip())
    if request.form.get('nuevo_p2','').strip(): set_config('pass_admin', request.form.get('nuevo_p2').strip())
    if request.form.get('nuevo_p3','').strip(): set_config('pass_profe3', request.form.get('nuevo_p3').strip())
    set_config('profe1_nombre', request.form.get('profe1','chuy').strip()); set_config('profe2_nombre', request.form.get('profe2','Dueño').strip()); set_config('profe3_nombre', request.form.get('profe3','Esposa').strip())
    return redirect("/")

if __name__=="__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
