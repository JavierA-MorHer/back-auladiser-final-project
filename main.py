import flask
from flask import request, Response
from flask_cors import CORS
import psycopg2
from psycopg2.extras import RealDictCursor
import pandas as pd
import matplotlib
matplotlib.use('Agg')  # Backend sin GUI
import matplotlib.pyplot as plt
import io
from datetime import datetime
import os

app = flask.Flask(__name__)
CORS(app)  # Habilitar CORS para todas las rutas

def get_db_connection():
    """Obtiene la conexión a la base de datos PostgreSQL"""
    # Leer la cadena de conexión desde el archivo
    with open('cad con render.txt', 'r') as f:
        connection_string = f.read().strip()
    
    return psycopg2.connect(connection_string)

@app.get('/hello-world')
def hello_world_get():
    return "Hello, World GET!"

@app.post('/hello-world')
def hello_world_post():
    return  "Hello, World POST!"

@app.get('/sales/branches/line-chart')
def sales_branches_line_chart():
    """Endpoint que genera una gráfica de líneas de ventas mensuales por sucursal"""
    try:
        # Obtener el parámetro year, si no se envía usar el año actual
        year = request.args.get('year', type=int)
        if year is None:
            year = datetime.now().year
        
        # Conectar a la base de datos
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # Consultar ventas mensuales por sucursal para el año especificado
        query = """
            SELECT 
                b.name AS branch_name,
                EXTRACT(MONTH FROM s.date) AS month,
                SUM(s.total) AS total_sales
            FROM sales s
            INNER JOIN branches b ON s.branch_id = b.id
            WHERE EXTRACT(YEAR FROM s.date) = %s
            GROUP BY b.name, EXTRACT(MONTH FROM s.date)
            ORDER BY month, b.name
        """
        
        cursor.execute(query, (year,))
        results = cursor.fetchall()
        
        # Cerrar conexión
        cursor.close()
        conn.close()
        
        # Verificar que existan ventas en el año ingresado
        if not results:
            return flask.jsonify({
                'error': f'No se encontraron ventas para el año {year}'
            }), 404
        
        # Convertir resultados a DataFrame
        df = pd.DataFrame(results)
        
        # Preparar datos para la gráfica
        # Crear un DataFrame pivoteado con meses como índice y sucursales como columnas
        pivot_df = df.pivot(index='month', columns='branch_name', values='total_sales')
        
        # Asegurar que todos los meses del año estén presentes (1-12)
        all_months = pd.DataFrame({'month': range(1, 13)})
        pivot_df = all_months.merge(pivot_df, on='month', how='left')
        pivot_df = pivot_df.set_index('month')
        
        # Crear la gráfica
        plt.figure(figsize=(12, 6))
        
        # Graficar una línea por cada sucursal
        for branch in pivot_df.columns:
            plt.plot(pivot_df.index, pivot_df[branch], marker='o', label=branch, linewidth=2)
        
        # Configurar la gráfica
        plt.title(f'Ventas Mensuales por Sucursal - Año {year}', fontsize=16, fontweight='bold')
        plt.xlabel('Mes', fontsize=12)
        plt.ylabel('Ventas Totales', fontsize=12)
        plt.legend(loc='best', fontsize=10)
        plt.grid(True, alpha=0.3)
        plt.xticks(range(1, 13), ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 
                                   'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic'])
        plt.tight_layout()
        
        # Guardar la gráfica en un buffer de memoria
        img_buffer = io.BytesIO()
        plt.savefig(img_buffer, format='png', dpi=100)
        img_buffer.seek(0)
        plt.close()
        
        # Devolver la imagen como respuesta
        response = Response(
            img_buffer.getvalue(),
            mimetype='image/png',
            headers={'Content-Disposition': f'inline; filename=sales_chart_{year}.png'}
        )
        # Los headers CORS se agregan automáticamente por flask-cors
        return response
        
    except Exception as e:
        return flask.jsonify({
            'error': f'Error al generar la gráfica: {str(e)}'
        }), 500

if __name__ == "__main__":
    app.run(debug=True)
