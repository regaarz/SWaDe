from flask import Flask, request, render_template
import psycopg2

app = Flask(__name__)

# Konfigurasi koneksi PostgreSQL
conn = psycopg2.connect(
    host="localhost",
    database="Impressive",
    user="tasklist_user",
    password="Arzula93."
)

# ------------------ POST: Simpan data organik, anorganik, b3 ------------------
@app.route('/send_distance', methods=['POST'])
def send_distance():
    try:
        data = request.get_json()
        print("DEBUG raw data:", request.data)
        print("DEBUG parsed json:", data)

        # Validasi data
        if not data or any(key not in data for key in ("organik", "anorganik", "b3")):
            return {"status": "error", "message": "Invalid JSON, expected organik, anorganik, b3"}, 400

        organik = int(data["organik"])
        anorganik = int(data["anorganik"])
        b3 = int(data["b3"])

        cur = conn.cursor()
        cur.execute(
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
                "timestamp": row[4].strftime("%Y-%m-%d %H:%M:%S")
            })

        return {
            "status": "success",
            "page": page,
            "total_pages": total_pages,
            "data": data_list
        }, 200

    except Exception as e:
        return {"status": "error", "message": str(e)}, 400

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
                "timestamp": row[4].strftime("%Y-%m-%d %H:%M:%S")
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
            "SELECT id, organik, anorganik, b3, timestamp FROM sensor_tong_1 ORDER BY timestamp ASC  LIMIT %s OFFSET %s",
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


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
