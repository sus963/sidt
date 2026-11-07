import sqlite3
import pandas as pd
from flask import Flask, jsonify, request
from flask_cors import CORS
from datetime import datetime

app = Flask(__name__)
CORS(app)

class GestorMotores:
    """
    Clase orientada a objetos para la gestión de motores y mantenimientos.
    Cumple con los principios de POO y permite la integración con Pandas 
    para análisis de Ciencia de Datos.
    """
    def __init__(self, db_name="gestion_motores2.db"):
        self.db_name = db_name
        self.inicializar_base_datos()

    def conectar(self):
        """Crea una conexión con SQLite configurada con filas en formato diccionario"""
        conn = sqlite3.connect(self.db_name)
        conn.row_factory = sqlite3.Row
        return conn

    def inicializar_base_datos(self):
        """Crea las tablas relacionales de motores y mantenimientos si no existen"""
        conn = self.conectar()
        cursor = conn.cursor()
        
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
                id INTEGER PRIMARY KEY AUTOINCREMENT,
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
        """Retorna todos los motores como una lista de diccionarios"""
        conn = self.conectar()
        motores = conn.execute('SELECT * FROM motores').fetchall()
        conn.close()
        return [dict(row) for row in motores]

    def agregar_motor(self, data):
        """Método de objeto para registrar un nuevo motor en la BD"""
        id_motor = data.get('id_motor', '').strip()
        marca = data.get('marca', '').strip()
        fuerza_hp = data.get('fuerza_hp', '').strip()
        tamano = data.get('tamano', '').strip()
        estado = data.get('estado', 'Disponible')
        operador_actual = data.get('operador_actual', 'Sin asignar').strip()

        conn = self.conectar()
        cursor = conn.cursor()
        try:
            cursor.execute('''
                INSERT INTO motores (id_motor, marca, fuerza_hp, tamano, estado, operador_actual)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (id_motor, marca, fuerza_hp, tamano, estado, operador_actual))
            conn.commit()
            exito = True
        except sqlite3.IntegrityError:
            exito = False
        finally:
            conn.close()
        return exito

    def actualizar_uso(self, data):
        """Actualiza el estado de uso o el operador a cargo del motor"""
        id_motor = data.get('id_motor')
        estado = data.get('estado')
        operador_actual = data.get('operador_actual')

        conn = self.conectar()
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE motores SET estado = ?, operador_actual = ? WHERE id_motor = ?
        ''', (estado, operador_actual, id_motor))
        conn.commit()
        conn.close()

    def obtener_mantenimientos_lista(self):
        """Retorna el historial completo uniendo las tablas por relaciones"""
        conn = self.conectar()
        query = '''
            SELECT m.id, m.id_motor, mot.marca, mot.fuerza_hp, m.fecha, m.que_se_hizo, m.quien_lo_hizo
            FROM mantenimientos m
            LEFT JOIN motores mot ON m.id_motor = mot.id_motor
            ORDER BY m.id DESC
        '''
        historial = conn.execute(query).fetchall()
        conn.close()
        return [dict(row) for row in historial]

    def registrar_mantenimiento(self, data):
        """Registra un mantenimiento y actualiza automáticamente el estado del motor"""
        id_motor = data.get('id_motor')
        fecha = data.get('fecha', '').strip()
        if not fecha:
            fecha = datetime.now().strftime("%d/%m/%Y %H:%M")
        que_se_hizo = data.get('que_se_hizo', '').strip()
        quien_lo_hizo = data.get('quien_lo_hizo', '').strip()
        nuevo_estado = data.get('nuevo_estado', 'Disponible')

        conn = self.conectar()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO mantenimientos (id_motor, fecha, que_se_hizo, quien_lo_hizo)
            VALUES (?, ?, ?, ?)
        ''', (id_motor, fecha, que_se_hizo, quien_lo_hizo))
        
        cursor.execute('''
            UPDATE motores SET estado = ?, operador_actual = ? WHERE id_motor = ?
        ''', (nuevo_estado, quien_lo_hizo, id_motor))
        
        conn.commit()
        conn.close()

    def obtener_dataframe_motores(self):
        """Método orientado a Ciencia de Datos: exporta SQLite a Pandas DataFrame"""
        conn = self.conectar()
        df = pd.read_sql_query("SELECT * FROM motores", conn)
        conn.close()
        return df


# Instanciamos el objeto principal del sistema
db_manager = GestorMotores()


# --- RUTAS WEB (FLASK API REST) ---

@app.route('/api/motores', methods=['GET'])
def api_obtener_motores():
    return jsonify(db_manager.obtener_motores_lista())

@app.route('/api/motores', methods=['POST'])
def api_agregar_motor():
    exito = db_manager.agregar_motor(request.json)
    if exito:
        return jsonify({"mensaje": "Motor registrado con éxito"}), 201
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
    # Arranca el servidor local para la interfaz y la simulación
    app.run(host='0.0.0.0', port=5000, debug=True)