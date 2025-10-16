from flask import Blueprint, request, redirect, url_for, flash, render_template
from utils.database import get_connection

home_route = Blueprint('home', __name__, template_folder='templates')

@home_route.route('/')
def index():
    """
    Rota principal que renderiza o index com restaurantes em destaque.
    """
    conn = None
    cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Buscar restaurantes com as maiores avaliações (ordenados por avaliação decrescente)
        # Limitamos a 6 restaurantes para a página inicial
        cursor.execute("""
            SELECT r.*, 
                   COALESCE(AVG(a.nota), 0) as media_avaliacao,
                   COUNT(a.id) as total_avaliacoes
            FROM restaurante r
            LEFT JOIN avaliacao a ON r.id = a.id_restaurante
            GROUP BY r.id, r.nome, r.tipo_culinaria, r.avaliacao
            ORDER BY media_avaliacao DESC, total_avaliacoes DESC
            LIMIT 6
        """)
        restaurantes = cursor.fetchall()
        
        # Consumir todos os resultados
        while cursor.nextset():
            pass
            
    except Exception as e:
        flash('Erro ao buscar dados: ' + str(e), 'danger')
        restaurantes = []
        print(f"DEBUG: Erro ao buscar restaurantes: {str(e)}")
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
    
    return render_template('index.html', restaurantes=restaurantes)

@home_route.route('/login-register')
def login_register():
    """
    Rota que renderiza a página com as opções de login e registro.
    """
    return render_template('login_register.html')

@home_route.route('/dashboard/consumidor')
def dashboard_consumidor():
    """
    Dashboard para consumidor: mostra restaurantes disponíveis
    """
    conn = None
    cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Buscar todos os restaurantes com seus produtos
        cursor.execute("""
            SELECT r.*, 
                   COALESCE(AVG(a.nota), 0) as media_avaliacao,
                   COUNT(a.id) as total_avaliacoes,
                   p.id as produto_id,
                   p.nome as produto_nome,
                   p.descricao as produto_descricao,
                   p.preco as produto_preco,
                   p.stats as produto_status,
            FROM restaurante r
            LEFT JOIN avaliacao a ON r.id = a.id_restaurante
            LEFT JOIN produto p ON r.id = p.id_restaurante AND p.stats = 'ativo'
            GROUP BY r.id, r.nome, r.tipo_culinaria, r.avaliacao, 
                     p.id, p.nome, p.descricao, p.preco, p.stats
            ORDER BY media_avaliacao DESC, r.nome
        """)
        
        resultados = cursor.fetchall()
        
        # Organizar dados por restaurante
        restaurantes = {}
        for row in resultados:
            restaurante_id = row['id']
            if restaurante_id not in restaurantes:
                restaurantes[restaurante_id] = {
                    'id': row['id'],
                    'nome': row['nome'],
                    'tipo_culinaria': row['tipo_culinaria'],
                    'logo_url': row.get('logo_url'),
                    'media_avaliacao': row['media_avaliacao'],
                    'total_avaliacoes': row['total_avaliacoes'],
                    'produtos': []
                }
            
            # Adicionar produto se existir
            if row['produto_id']:
                restaurantes[restaurante_id]['produtos'].append({
                    'id': row['produto_id'],
                    'nome': row['produto_nome'],
                    'descricao': row['produto_descricao'],
                    'preco': row['produto_preco']
                })
        
        # Converter para lista
        restaurantes = list(restaurantes.values())
        
        # Consumir todos os resultados
        while cursor.nextset():
            pass
            
    except Exception as e:
        flash('Erro ao buscar dados: ' + str(e), 'danger')
        restaurantes = []
        print(f"DEBUG: Erro em dashboard_consumidor: {str(e)}")
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
    
    return render_template('dashboard_consumidor.html', restaurantes=restaurantes)

@home_route.route('/dashboard/restaurante')
def dashboard_restaurante():
    """
    Dashboard para restaurante: exibe formulário para cadastro de horários e produtos,
    e uma lista de produtos já cadastrados.
    """
    conn = None
    cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        # Por exemplo, o id do restaurante pode vir via sessão. Para demonstração, usamos query string:
        id_restaurante = request.args.get('id', 1)
        cursor.execute("SELECT * FROM produto WHERE id_restaurante = %s", (id_restaurante,))
        produtos = cursor.fetchall()
    except Exception as e:
        flash('Erro ao buscar produtos: ' + str(e), 'danger')
        produtos = []
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
    return render_template('dashboard_restaurante.html', produtos=produtos)