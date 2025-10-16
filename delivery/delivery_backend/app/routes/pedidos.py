from flask import Blueprint, request, jsonify
from app.utils.database import db
import mysql.connector

pedidos_bp = Blueprint('pedidos', __name__)

@pedidos_bp.route('/', methods=['POST'])
def criar_pedido():
    try:
        data = request.get_json()
        consumidor_id = data.get('consumidor_id')
        restaurante_id = data.get('restaurante_id')
        forma_pagamento = data.get('forma_pagamento')
        itens = data.get('itens', [])
        
        connection = db.get_connection()
        cursor = connection.cursor()
        
        # Calcular valor total
        valor_total = 0
        for item in itens:
            cursor.execute("SELECT preco FROM produto WHERE id = %s", (item['produto_id'],))
            produto = cursor.fetchone()
            if produto:
                valor_total += produto[0] * item['quantidade']
        
        # Adicionar taxa de 3%
        valor_total *= 1.03
        
        # Criar pedido
        cursor.execute("""
            INSERT INTO pedidos (data_hora, status, forma_pagamento, valor_total, consumidor_id, restaurante_id)
            VALUES (NOW(), 'preparacao', %s, %s, %s, %s)
        """, (forma_pagamento, valor_total, consumidor_id, restaurante_id))
        
        pedido_id = cursor.lastrowid
        
        # Adicionar itens do pedido
        for item in itens:
            cursor.execute("SELECT preco FROM produto WHERE id = %s", (item['produto_id'],))
            produto = cursor.fetchone()
            if produto:
                subtotal = produto[0] * item['quantidade']
                cursor.execute("""
                    INSERT INTO item_pedido (qtd, observacoes, subtotal, pedido_id, produto_id)
                    VALUES (%s, %s, %s, %s, %s)
                """, (item['quantidade'], item.get('observacoes', ''), subtotal, pedido_id, item['produto_id']))
        
        connection.commit()
        return jsonify({'message': 'Pedido criado com sucesso', 'pedido_id': pedido_id}), 201
        
    except mysql.connector.Error as err:
        return jsonify({'error': str(err)}), 500
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()

@pedidos_bp.route('/cliente/<int:consumidor_id>', methods=['GET'])
def get_pedidos_cliente(consumidor_id):
    try:
        connection = db.get_connection()
        cursor = connection.cursor(dictionary=True)
        
        cursor.execute("""
            SELECT p.*, r.nome as restaurante_nome 
            FROM pedidos p 
            JOIN restaurante r ON p.restaurante_id = r.id 
            WHERE p.consumidor_id = %s 
            ORDER BY p.data_hora DESC
        """, (consumidor_id,))
        pedidos = cursor.fetchall()
        
        # Buscar itens para cada pedido
        for pedido in pedidos:
            cursor.execute("""
                SELECT ip.*, prod.nome as produto_nome 
                FROM item_pedido ip 
                JOIN produto prod ON ip.produto_id = prod.id 
                WHERE ip.pedido_id = %s
            """, (pedido['id'],))
            pedido['itens'] = cursor.fetchall()
        
        return jsonify(pedidos), 200
        
    except mysql.connector.Error as err:
        return jsonify({'error': str(err)}), 500
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()

@pedidos_bp.route('/<int:pedido_id>/status', methods=['PUT'])
def atualizar_status(pedido_id):
    try:
        data = request.get_json()
        novo_status = data.get('status')
        
        connection = db.get_connection()
        cursor = connection.cursor()
        
        cursor.execute("UPDATE pedidos SET status = %s WHERE id = %s", (novo_status, pedido_id))
        connection.commit()
        
        return jsonify({'message': 'Status atualizado com sucesso'}), 200
        
    except mysql.connector.Error as err:
        return jsonify({'error': str(err)}), 500
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()