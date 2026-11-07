import os
import psycopg2
import psycopg2.extras
import pandas as pd
from flask import Flask, jsonify, request
from flask_cors import CORS
from datetime import datetime

app = Flask(__name__)
CORS(app) # Permite que tu Vercel se comunique con este servidor

# La URL de conexión la pondremos en Render como "Variable de Entorno"
DATABASE_URL = os.getenv("DATABASE_URL")

class GestorMotoresNube:
    def __init__(self):
        self.inicializar_base_datos()

    def conectar(self):
        # Nos conectamos a Neon usando la URL
        conn = psycopg2.connect(DATABASE_URL)
        return conn

    def inicializar_base_datos(self):
        conn = self.conectar()
        cursor = conn.cursor()
        
        # En Postgres AUTOINCREMENT se escribe como SERIAL
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS motores (
                id_motor TEXT PRIMARY KEY,
                marca TEXT NOT NULL,
                fuerza_hp TEXT NOT NULL,
                tamano TEXT NOT NULL,
                estado TEXT DEFAULT 'Disponible',
                operador_actual TEXT DEFAULT 'Sin asignar'
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS mantenimientos (
                id SERIAL PRIMARY KEY,
                id_motor TEXT NOT NULL,
                fecha TEXT NOT NULL,
                que_se_hizo TEXT NOT NULL,
                quien_lo_hizo TEXT NOT NULL,
                FOREIGN KEY (id_motor) REFERENCES motores(id_motor)
            )
        ''')
        conn.commit()
        conn.close()

    def obtener_motores_lista(self):
        conn = self.conectar()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        cursor.execute('SELECT * FROM motores')
        motores = cursor.fetchall()
        conn.close()
        return [dict(row) for row in motores]

    def agregar_motor(self, data):
        conn = self.conectar()
        cursor = conn.cursor()
        try:
            # En Postgres usamos %s en lugar de ?
            cursor.execute('''
                INSERT INTO motores (id_motor, marca, fuerza_hp, tamano, estado, operador_actual)
                VALUES (%s, %s, %s, %s, %s, %s)
            ''', (data.get('id_motor'), data.get('marca'), data.get('fuerza_hp'), data.get('tamano'), 'Disponible', data.get('operador_actual', 'Sin asignar')))
            conn.commit()
            exito = True
        except psycopg2.IntegrityError:
            conn.rollback()
            exito = False
        finally:
            conn.close()
        return exito

    def actualizar_uso(self, data):
        conn = self.conectar()
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE motores SET estado = %s, operador_actual = %s WHERE id_motor = %s
        ''', (data.get('estado'), data.get('operador_actual'), data.get('id_motor')))
        conn.commit()
        conn.close()

    def obtener_mantenimientos_lista(self):
        conn = self.conectar()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        cursor.execute('''
            SELECT m.id, m.id_motor, mot.marca, mot.fuerza_hp, m.fecha, m.que_se_hizo, m.quien_lo_hizo
            FROM mantenimientos m
            LEFT JOIN motores mot ON m.id_motor = mot.id_motor
            ORDER BY m.id DESC
        ''')
        historial = cursor.fetchall()
        conn.close()
        return [dict(row) for row in historial]

    def registrar_mantenimiento(self, data):
        fecha = data.get('fecha', '').strip() or datetime.now().strftime("%d/%m/%Y %H:%M")
        conn = self.conectar()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO mantenimientos (id_motor, fecha, que_se_hizo, quien_lo_hizo)
            VALUES (%s, %s, %s, %s)
        ''', (data.get('id_motor'), fecha, data.get('que_se_hizo'), data.get('quien_lo_hizo')))
        
        cursor.execute('''
            UPDATE motores SET estado = %s, operador_actual = %s WHERE id_motor = %s
        ''', (data.get('nuevo_estado', 'Disponible'), data.get('quien_lo_hizo'), data.get('id_motor')))
        
        conn.commit()
        conn.close()

db_manager = GestorMotoresNube()

@app.route('/api/motores', methods=['GET'])
def api_obtener_motores():
    return jsonify(db_manager.obtener_motores_lista())

@app.route('/api/motores', methods=['POST'])
def api_agregar_motor():
    exito = db_manager.agregar_motor(request.json)
    if exito: return jsonify({"mensaje": "Motor registrado con éxito"}), 201
    return jsonify({"error": "El ID de motor ya existe"}), 400

@app.route('/api/motores/uso', methods=['PUT'])
def api_actualizar_uso():
    db_manager.actualizar_uso(request.json)
    return jsonify({"mensaje": "Estado actualizado"}), 200

@app.route('/api/mantenimientos', methods=['GET'])
def api_obtener_mantenimientos():
    return jsonify(db_manager.obtener_mantenimientos_lista())

@app.route('/api/mantenimientos', methods=['POST'])
def api_agregar_mantenimiento():
    db_manager.registrar_mantenimiento(request.json)
    return jsonify({"mensaje": "Mantenimiento registrado"}), 201

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)