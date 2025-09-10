from flask import Flask, request, render_template
import psycopg2
import urllib.parse as up
import os
import sqlite3
import plotly.graph_objs as go
import plotly.offline as pyo

app = Flask(__name__)

# ------------------ DATABASE CONNECTION ------------------
DATABASE_URL = os.getenv("DATABASE_URL")

conn = None
if DATABASE_URL:
    try:
        up.uses_netloc.append("postgres")
        url = up.urlparse(DATABASE_URL)

        conn = psycopg2.connect(
            database=url.path[1:],
            user=url.username,
            password=url.password,
            host=url.hostname,
            port=url.port
        )
        print("✅ Connected to PostgreSQL on Railway")
    except Exception as e:
        print("❌ Failed to connect PostgreSQL:", e)
else:
    print("⚠️ DATABASE_URL not found, using SQLite for local testing")
    conn = sqlite3.connect("local.db", check_same_thread=False)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS sensor_tong_1 (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            organik INTEGER,
            anorganik INTEGER,
            b3 INTEGER,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()

# ------------------ POST: Simpan data organik, anorganik, b3 ------------------
@app.route('/send_distance', methods=['POST'])
def send_distance():
    try:
        data = request.get_json()
        print("DEBUG raw data:", request.data)
        print("DEBUG parsed json:", data)

        if not data or any(key not in data for key in ("organik", "anorganik", "b3")):
            return {"status": "error", "message": "Invalid JSON, expected organik, anorganik, b3"}, 400

        organik = int(data["organik"])
        anorganik = int(data["anorganik"])
        b3 = int(data["b3"])

        cur = conn.cursor()
        cur.execute(
            "INSERT INTO sensor_tong_1 (organik, anorganik, b3) VALUES (?, ?, ?)" 
            if isinstance(conn, sqlite3.Connection) else
            "INSERT INTO sensor_tong_1 (organik, anorganik, b3) VALUES (%s, %s, %s)",
            (organik, anorganik, b3)
        )
        conn.commit()
        cur.close()

        return {"status": "success", "message": "Data saved"}, 200

    except Exception as e:
        conn.rollback()
        print("ERROR:", e)
        return {"status": "error", "message": str(e)}, 400


# ------------------ GET: Ambil 10 data terbaru dalam JSON ------------------
@app.route('/get_distance', methods=['GET'])
def get_distance():
    try:
        page = request.args.get('page', default=1, type=int)
        limit = 10
        offset = (page - 1) * limit

        cur = conn.cursor()
        cur.execute(
            "SELECT id, organik, anorganik, b3, timestamp FROM sensor_tong_1 ORDER BY timestamp ASC LIMIT ? OFFSET ?" 
            if isinstance(conn, sqlite3.Connection) else
            "SELECT id, organik, anorganik, b3, timestamp FROM sensor_tong_1 ORDER BY timestamp ASC LIMIT %s OFFSET %s",
            (limit, offset)
        )
        rows = cur.fetchall()

        cur.execute("SELECT COUNT(*) FROM sensor_tong_1")
        total_count = cur.fetchone()[0]
        cur.close()

        total_pages = (total_count + limit - 1) // limit

        data_list = []
        for row in rows:
            data_list.append({
                "id": row[0],
                "organik": row[1],
                "anorganik": row[2],
                "b3": row[3],
                "timestamp": row[4] if isinstance(conn, sqlite3.Connection) else row[4].strftime("%Y-%m-%d %H:%M:%S")
            })

        return {
            "status": "success",
            "page": page,
            "total_pages": total_pages,
            "data": data_list
        }, 200

    except Exception as e:
        return {"status": "error", "message": str(e)}, 400


# ------------------ GET: Ambil semua data JSON ------------------
@app.route('/view_all', methods=['GET'])
def view_all():
    try:
        cur = conn.cursor()
        cur.execute("SELECT id, organik, anorganik, b3, timestamp FROM sensor_tong_1 ORDER BY timestamp ASC")
        rows = cur.fetchall()
        cur.close()

        data_list = []
        for row in rows:
            data_list.append({
                "id": row[0],
                "organik": row[1],
                "anorganik": row[2],
                "b3": row[3],
                "timestamp": row[4] if isinstance(conn, sqlite3.Connection) else row[4].strftime("%Y-%m-%d %H:%M:%S")
            })

        return {"status": "success", "data": data_list}, 200

    except Exception as e:
        return {"status": "error", "message": str(e)}, 400


# ------------------ GET: Tampilkan data di HTML ------------------
@app.route('/view_data', methods=['GET'])
def view_data():
    try:
        page = request.args.get('page', default=1, type=int)
        limit = 20
        offset = (page - 1) * limit

        cur = conn.cursor()
        cur.execute(
            "SELECT id, organik, anorganik, b3, timestamp FROM sensor_tong_1 ORDER BY timestamp ASC LIMIT ? OFFSET ?" 
            if isinstance(conn, sqlite3.Connection) else
            "SELECT id, organik, anorganik, b3, timestamp FROM sensor_tong_1 ORDER BY timestamp ASC LIMIT %s OFFSET %s",
            (limit, offset)
        )
        rows = cur.fetchall()

        cur.execute("SELECT COUNT(*) FROM sensor_tong_1")
        total_count = cur.fetchone()[0]
        cur.close()

        total_pages = (total_count + limit - 1) // limit

        return render_template("monitoring.html", rows=rows, page=page, total_pages=total_pages)

    except Exception as e:
        return f"Terjadi error: {e}", 500
@app.route('/view_graph', methods=['GET'])
def view_graph():
    try:
        # Ambil semua data
        cur = conn.cursor()
        cur.execute("SELECT timestamp, organik, anorganik, b3 FROM sensor_tong_1 ORDER BY timestamp ASC")
        rows = cur.fetchall()
        cur.close()

        # Pisahkan data untuk grafik
        timestamps = [row[0].strftime("%Y-%m-%d %H:%M:%S") for row in rows]
        organik = [row[1] for row in rows]
        anorganik = [row[2] for row in rows]
        b3 = [row[3] for row in rows]

        # Buat trace untuk Plotly
        trace1 = go.Scatter(x=timestamps, y=organik, mode='lines+markers', name='Organik')
        trace2 = go.Scatter(x=timestamps, y=anorganik, mode='lines+markers', name='Anorganik')
        trace3 = go.Scatter(x=timestamps, y=b3, mode='lines+markers', name='B3')

        layout = go.Layout(
            title='Grafik Sensor Tong Sampah',
            xaxis=dict(title='Timestamp'),
            yaxis=dict(title='Nilai'),
            hovermode='closest'
        )
        fig = go.Figure(data=[trace1, trace2, trace3], layout=layout)
        graph_html = pyo.plot(fig, output_type='div', include_plotlyjs=True)

        # Render di template HTML
        return render_template("graph.html", graph_html=graph_html)

    except Exception as e:
        return f"Terjadi error: {e}", 500



if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
