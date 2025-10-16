from flask import Blueprint, request, redirect, url_for, flash, render_template
from flask_login import login_user
from utils.database import get_connection
from models.usuario import Usuario   
from flask_login import logout_user

login_bp = Blueprint('login', __name__, template_folder='templates')

@login_bp.route('/login/consumidor', methods=['GET', 'POST'])
def login_consumidor():
    if request.method == 'POST':
        email = request.form.get('email')
        senha = request.form.get('password')
        try:
            conn = get_connection()
            cursor = conn.cursor(dictionary=True)
            cursor.execute("""
                SELECT c.id, c.email, c.senha, con.nome, con.sobrenome, con.cpf
                FROM cliente c
                JOIN consumidor con ON c.id = con.id
                WHERE c.email = %s
            """, (email,))
            usuario = cursor.fetchone()

            if usuario and usuario.get('senha') == senha:
                # cria objeto Usuario e loga com Flask-Login
                
                user = Usuario(usuario['id'], usuario['email'], tipo="consumidor")
                login_user(user)
                return redirect(url_for('home.dashboard_consumidor'))
            else:
                flash('E-mail ou senha inválidos para consumidor.', 'danger')

        except Exception as e:
            flash('Erro de conexão: ' + str(e), 'danger')
        finally:
            if cursor: cursor.close()
            if conn: conn.close()

    return render_template('login_consumidor.html')


@login_bp.route('/login/restaurante', methods=['GET', 'POST'])
def login_restaurante():
    if request.method == 'POST':
        email = request.form.get('email')
        senha = request.form.get('password')
        try:
            conn = get_connection()
            cursor = conn.cursor(dictionary=True)
            cursor.execute("""
                SELECT c.id, c.email, c.senha, re.nome, re.tipo_culinaria
                FROM cliente c
                JOIN restaurante re ON c.id = re.id
                WHERE c.email = %s
            """, (email,))
            usuario = cursor.fetchone()

            if usuario and usuario.get('senha') == senha:
            # pega id_restaurante a partir do id_cliente (que logou como restaurante)
                cursor.execute("SELECT id FROM restaurante WHERE id = %s", (usuario['id'],))
                result = cursor.fetchone()

                if not result:
                    flash('Erro: restaurante não encontrado.', 'danger')
                    return redirect(url_for('home.login_register'))

                id_restaurante = result['id']

                # cria usuário logado com id_restaurante
                user = Usuario(usuario['id'], usuario['email'], tipo="restaurante", id_restaurante=id_restaurante)
                login_user(user)

                return redirect(url_for('home.dashboard_restaurante'))
            else:
                flash('E-mail ou senha inválidos para restaurante.', 'danger')

        except Exception as e:
            flash('Erro de conexão: ' + str(e), 'danger')
        finally:
            if cursor: cursor.close()
            if conn: conn.close()

    return render_template('login_restaurante.html')

@login_bp.route('/logout')
def logout():
    """Faz logout do usuário e redireciona para a página inicial"""
    logout_user()
    return redirect(url_for('home.index'))
