from flask import Blueprint, render_template, request, redirect, url_for, flash
from utils.database import get_connection
import uuid

registro_bp = Blueprint('registro', __name__, template_folder='templates')

@registro_bp.route('/registro/consumidor', methods=['GET', 'POST'])
def registro_consumidor():
    if request.method == 'POST':
        nome = request.form.get('nome')
        sobrenome = request.form.get('sobrenome')
        cpf = request.form.get('cpf')
        email = request.form.get('email')
        senha = request.form.get('senha')
        numero = request.form.get('telefone')
        endereco = request.form.get('endereco')
        

        try:
            conn = get_connection()
            cursor = conn.cursor()
            id_cliente = str(uuid.uuid4())
            # 1 - cadastra cliente
            sql_cliente = "INSERT INTO cliente (id, email, senha) VALUES (%s, %s, %s)"
            cursor.execute(sql_cliente, (id_cliente, email, senha))
            conn.commit()
 

            # 2 - cadastra contato
            sql_contato = "INSERT INTO contato (id_cliente, numero) VALUES (%s, %s)"
            cursor.execute(sql_contato, (id_cliente, numero))
            conn.commit()
            # 3 - cadastra endereço
            sql_endereco = """
            INSERT INTO endereco (logradouro, numero, complemento, bairro, cidade, estado, pais, cep, id_cliente)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            cursor.execute(sql_endereco, (
                request.form.get('logradouro'),
                request.form.get('numero'),
                request.form.get('complemento'),
                request.form.get('bairro'),
                request.form.get('cidade'),
                request.form.get('estado'),
                request.form.get('pais'),
                request.form.get('cep'),
                id_cliente
            ))
            conn.commit()
            # 4 - cadastra consumidor
            sql_consumidor = "INSERT INTO consumidor (id, nome, sobrenome, cpf) VALUES (%s, %s, %s, %s)"
            cursor.execute(sql_consumidor, (id_cliente, nome, sobrenome, cpf))
            conn.commit()
        except Exception as e:
            flash('Erro ao registrar consumidor: ' + str(e), 'danger')
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()
        return redirect(url_for('home.login_register'))

    return render_template('registro_consumidor.html')

@registro_bp.route('/registro/restaurante', methods=['GET', 'POST'])
def registro_restaurante():
    if request.method == 'POST':
        nome = request.form.get('nome')
        tipo_culinaria = request.form.get('tipo_culinaria')
        email = request.form.get('email')
        senha = request.form.get('senha')
        numero = request.form.get('telefone')
        endereco = request.form.get('endereco')

        # Recebe listas de horários
        dias = request.form.getlist('dia[]')
        horas_inicio = request.form.getlist('hora_inicio[]')
        horas_fim = request.form.getlist('hora_fim[]')

        try:
            conn = get_connection()
            cursor = conn.cursor()

            id_cliente = str(uuid.uuid4())
            # 1 - cadastra cliente
            sql_cliente = "INSERT INTO cliente (id, email, senha) VALUES (%s, %s, %s)"
            cursor.execute(sql_cliente, (id_cliente, email, senha))
            conn.commit()
            # 2 - cadastra contato
            sql_contato = "INSERT INTO contato (id_cliente, numero) VALUES (%s, %s)"
            cursor.execute(sql_contato, (id_cliente, numero))
            conn.commit()
            # 3 - cadastra endereço
            sql_endereco = """
            INSERT INTO endereco (logradouro, numero, complemento, bairro, cidade, estado, pais, cep, id_cliente)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            cursor.execute(sql_endereco, (
                request.form.get('logradouro'),
                request.form.get('numero'),
                request.form.get('complemento'),
                request.form.get('bairro'),
                request.form.get('cidade'),
                request.form.get('estado'),
                request.form.get('pais'),
                request.form.get('cep'),
                id_cliente
            ))
            conn.commit()
            # 4 - cadastra restaurante
            sql_restaurante = "INSERT INTO restaurante (id, nome, tipo_culinaria) VALUES (%s, %s, %s)"
            cursor.execute(sql_restaurante, (id_cliente, nome, tipo_culinaria))
            conn.commit()
            # 5 - cadastra múltiplos horários
            for dia, h_inicio, h_fim in zip(dias, horas_inicio, horas_fim):
                cursor.execute(
                    "INSERT INTO horarios (id_restaurante, dia, hora_inicio, hora_fim) VALUES (%s, %s, %s, %s)",
                    (id_cliente, dia, h_inicio, h_fim)
                )
            conn.commit()
        except Exception as e:
            flash('Erro ao registrar restaurante: ' + str(e), 'danger')
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()
        return redirect(url_for('home.login_register'))

    return render_template('registro_restaurante.html')
