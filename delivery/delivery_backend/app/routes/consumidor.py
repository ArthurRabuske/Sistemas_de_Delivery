from flask import Blueprint, request, redirect, url_for, flash, render_template, session
from flask_login import current_user
from utils.database import get_connection
import uuid

consumidor_bp = Blueprint('consumidor', __name__, template_folder='templates')

@consumidor_bp.route('/dashboard')
def dashboard_consumidor():
    """
    Dashboard do consumidor com restaurantes e pedidos recentes.
    """
    restaurantes = []
    pedidos_recentes = []
    
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)

        # CARREGAR TODOS OS RESTAURANTES 
        cursor.execute("""
            SELECT id, nome, tipo_culinaria, avaliacao
            FROM restaurante 
            ORDER BY nome
        """)
        restaurantes = cursor.fetchall()
        
        # DEBUG: Verificar restaurantes encontrados
        print(f"DEBUG: Restaurantes encontrados: {len(restaurantes)}")

        # Recupera id do consumidor pelo usuário logado (JOIN com cliente)
        cursor.execute("""
            SELECT c.id AS id_consumidor
            FROM consumidor c
            JOIN cliente cl ON c.id = cl.id
            WHERE cl.email = %s
        """, (current_user.email,))
        result = cursor.fetchone()
        
        if result:
            id_consumidor = result["id_consumidor"]
            
            # CARREGAR PEDIDOS RECENTES DO CONSUMIDOR (últimos 5) - CORRIGIDO
            cursor.execute("""
                SELECT p.id, p.data_hora, p.stats, p.valor_total, p.forma_pagamento,
                       r.nome AS restaurante_nome
                FROM pedidos p
                JOIN restaurante r ON p.id_restaurante = r.id
                WHERE p.id_consumidor = %s
                ORDER BY p.data_hora DESC
                LIMIT 5
            """, (id_consumidor,))
            pedidos_data = cursor.fetchall()
            
            # Formatar pedidos recentes
            for pedido in pedidos_data:
                # Buscar itens do pedido (apenas nomes para resumo) - CORRIGIDO
                cursor.execute("""
                    SELECT pr.nome AS produto_nome
                    FROM item_pedido ip
                    JOIN produto pr ON ip.id_produto = pr.id
                    WHERE ip.id_pedido = %s
                    LIMIT 3  # Apenas primeiros 3 itens para resumo
                """, (pedido['id'],))
                itens_data = cursor.fetchall()
                
                itens_resumo = [item['produto_nome'] for item in itens_data]
                
                pedidos_recentes.append({
                    'id': pedido['id'],
                    'restaurante_nome': pedido['restaurante_nome'],
                    'data_hora': pedido['data_hora'],
                    'valor_total': pedido['valor_total'],
                    'stats': pedido['stats'],  # Usando 'stats' que existe na tabela
                    'forma_pagamento': pedido['forma_pagamento'],
                    'itens': itens_resumo
                })

    except Exception as e:
        flash("Erro ao carregar dados: " + str(e), "danger")
        print(f"DEBUG: Erro no dashboard: {str(e)}")
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

    return render_template(
        'dashboard_consumidor.html',
        restaurantes=restaurantes,
        pedidos=pedidos_recentes
    )

@consumidor_bp.route('/restaurante/<restaurante_id>')
def cardapio_restaurante(restaurante_id):
    """
    Mostra o cardápio de um restaurante específico
    """
    conn = None
    cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Buscar informações do restaurante
        cursor.execute("""
            SELECT r.*, 
                   (SELECT AVG(nota) FROM avaliacao WHERE id_restaurante = r.id) as avaliacao_media,
                   (SELECT COUNT(*) FROM avaliacao WHERE id_restaurante = r.id) as total_avaliacoes
            FROM restaurante r
            WHERE r.id = %s
        """, (restaurante_id,))
        restaurante = cursor.fetchone()
        
        if not restaurante:
            flash('Restaurante não encontrado.', 'danger')
            return redirect(url_for('dashboard_consumidor'))
        
        # Buscar produtos ativos do restaurante
        cursor.execute("""
            SELECT id, nome, descricao, preco, stats
            FROM produto
            WHERE id_restaurante = %s AND stats = 'ativo'
            ORDER BY nome
        """, (restaurante_id,))
        produtos = cursor.fetchall()
        
        # Buscar avaliações do restaurante
        cursor.execute("""
            SELECT a.*, c.nome as nome_consumidor
            FROM avaliacao a
            JOIN consumidor c ON a.id_consumidor = c.id
            WHERE a.id_restaurante = %s
            ORDER BY a.data_hora DESC
            LIMIT 10
        """, (restaurante_id,))
        avaliacoes = cursor.fetchall()
        
    except Exception as e:
        flash('Erro ao buscar dados: ' + str(e), 'danger')
        restaurante, produtos, avaliacoes = None, [], []
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
    
    return render_template('cardapio_restaurante.html', 
                         restaurante=restaurante, 
                         produtos=produtos, 
                         avaliacoes=avaliacoes)
                         

@consumidor_bp.route('/meus-dados')
def meus_dados():
    """
    Página principal de gerenciamento de dados do consumidor
    """
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Buscar dados do consumidor
        cursor.execute("""
            SELECT c.* 
            FROM consumidor c 
            WHERE c.id = %s
        """, (current_user.id,))
        consumidor = cursor.fetchone()
        
        # Buscar contatos
        cursor.execute("SELECT * FROM contato WHERE id_cliente = %s", (current_user.id,))
        contatos = cursor.fetchall()
        
        # Buscar endereços
        cursor.execute("SELECT * FROM endereco WHERE id_cliente = %s", (current_user.id,))
        enderecos = cursor.fetchall()
        
        # Buscar cartões
        cursor.execute("SELECT * FROM cartao_de_credito WHERE id_consumidor = %s", (current_user.id,))
        cartoes = cursor.fetchall()
        
        # Consumir resultados não lidos
        while cursor.nextset():
            pass
            
    except Exception as e:
        flash('Erro ao buscar dados: ' + str(e), 'danger')
        consumidor, contatos, enderecos, cartoes = None, [], [], []
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
    
    return render_template('meus_dados.html', 
                         consumidor=consumidor,
                         contatos=contatos,
                         enderecos=enderecos,
                         cartoes=cartoes)

# ===== CONTATOS =====
@consumidor_bp.route('/contato/adicionar', methods=['POST'])
def adicionar_contato():
    """Adicionar novo contato"""
    try:
        numero = request.form.get('numero')
        tipo = request.form.get('tipo')
        
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO contato (id, numero, tipo, id_cliente)
            VALUES (%s, %s, %s, %s)
        """, (str(uuid.uuid4()), numero, tipo, current_user.id))
        
        conn.commit()
        flash('Contato adicionado com sucesso!', 'success')
        
    except Exception as e:
        flash('Erro ao adicionar contato: ' + str(e), 'danger')
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
    
    return redirect(url_for('consumidor.meus_dados'))

@consumidor_bp.route('/contato/editar/<contato_id>', methods=['POST'])
def editar_contato(contato_id):
    """Editar contato existente"""
    try:
        numero = request.form.get('numero')
        tipo = request.form.get('tipo')
        
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE contato 
            SET numero = %s, tipo = %s 
            WHERE id = %s AND id_cliente = %s
        """, (numero, tipo, contato_id, current_user.id))
        
        conn.commit()
        flash('Contato atualizado com sucesso!', 'success')
        
    except Exception as e:
        flash('Erro ao atualizar contato: ' + str(e), 'danger')
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
    
    return redirect(url_for('consumidor.meus_dados'))

@consumidor_bp.route('/contato/excluir/<contato_id>')
def excluir_contato(contato_id):
    """Excluir contato"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            DELETE FROM contato 
            WHERE id = %s AND id_cliente = %s
        """, (contato_id, current_user.id))
        
        conn.commit()
        flash('Contato excluído com sucesso!', 'success')
        
    except Exception as e:
        flash('Erro ao excluir contato: ' + str(e), 'danger')
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
    
    return redirect(url_for('consumidor.meus_dados'))

# ===== ENDEREÇOS =====
@consumidor_bp.route('/endereco/adicionar', methods=['POST'])
def adicionar_endereco():
    """Adicionar novo endereço"""
    try:
        logradouro = request.form.get('logradouro')
        numero = request.form.get('numero')
        complemento = request.form.get('complemento')
        bairro = request.form.get('bairro')
        cidade = request.form.get('cidade')
        estado = request.form.get('estado')
        pais = request.form.get('pais')
        cep = request.form.get('cep')
        
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO endereco (id, logradouro, numero, complemento, bairro, cidade, estado, pais, cep, id_cliente)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (str(uuid.uuid4()), logradouro, numero, complemento, bairro, cidade, estado, pais, cep, current_user.id))
        
        conn.commit()
        flash('Endereço adicionado com sucesso!', 'success')
        
    except Exception as e:
        flash('Erro ao adicionar endereço: ' + str(e), 'danger')
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
    
    return redirect(url_for('consumidor.meus_dados'))

@consumidor_bp.route('/endereco/editar/<endereco_id>', methods=['POST'])
def editar_endereco(endereco_id):
    """Editar endereço existente"""
    try:
        logradouro = request.form.get('logradouro')
        numero = request.form.get('numero')
        complemento = request.form.get('complemento')
        bairro = request.form.get('bairro')
        cidade = request.form.get('cidade')
        estado = request.form.get('estado')
        pais = request.form.get('pais')
        cep = request.form.get('cep')
        
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE endereco 
            SET logradouro = %s, numero = %s, complemento = %s, bairro = %s, 
                cidade = %s, estado = %s, pais = %s, cep = %s
            WHERE id = %s AND id_cliente = %s
        """, (logradouro, numero, complemento, bairro, cidade, estado, pais, cep, endereco_id, current_user.id))
        
        conn.commit()
        flash('Endereço atualizado com sucesso!', 'success')
        
    except Exception as e:
        flash('Erro ao atualizar endereço: ' + str(e), 'danger')
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
    
    return redirect(url_for('consumidor.meus_dados'))

@consumidor_bp.route('/endereco/excluir/<endereco_id>')
def excluir_endereco(endereco_id):
    """Excluir endereço"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            DELETE FROM endereco 
            WHERE id = %s AND id_cliente = %s
        """, (endereco_id, current_user.id))
        
        conn.commit()
        flash('Endereço excluído com sucesso!', 'success')
        
    except Exception as e:
        flash('Erro ao excluir endereço: ' + str(e), 'danger')
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
    
    return redirect(url_for('consumidor.meus_dados'))

# ===== CARTÕES DE CRÉDITO =====
@consumidor_bp.route('/cartao/adicionar', methods=['POST'])
def adicionar_cartao():
    """Adicionar novo cartão de crédito"""
    conn = None
    cursor = None
    try:
        titular = request.form.get('titular')
        bandeira = request.form.get('bandeira')
        data_validade = request.form.get('data_validade')  # Formato MM/AA
        
        # Validações básicas
        if not all([titular, bandeira, data_validade]):
            flash('Todos os campos obrigatórios devem ser preenchidos!', 'danger')
            return redirect(url_for('consumidor.meus_dados'))
        
        # Validar data de validade no formato MM/AA - CORREÇÃO AQUI
        from datetime import datetime
        try:
            # Verificar formato MM/AA
            if len(data_validade) != 5 or data_validade[2] != '/':
                flash('Formato de data inválido! Use MM/AA (ex: 07/29)', 'danger')
                return redirect(url_for('consumidor.meus_dados'))
            
            mes = data_validade[:2]
            ano = data_validade[3:]
            
            # Validar mês
            if not mes.isdigit() or int(mes) < 1 or int(mes) > 12:
                flash('Mês inválido! Use de 01 a 12', 'danger')
                return redirect(url_for('consumidor.meus_dados'))
            
            # Validar ano
            if not ano.isdigit() or len(ano) != 2:
                flash('Ano inválido! Use 2 dígitos (ex: 29 para 2029)', 'danger')
                return redirect(url_for('consumidor.meus_dados'))
            
            # Converter para ano completo (20XX)
            ano_completo = f"20{ano}"
            
            # Criar data no primeiro dia do mês
            data_validade_obj = datetime.strptime(f"{ano_completo}-{mes}-01", '%Y-%m-%d')
            hoje = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            
            # A data de validade deve ser pelo menos o mês atual
            if data_validade_obj < hoje:
                flash('A data de validade não pode ser no passado!', 'danger')
                return redirect(url_for('consumidor.meus_dados'))
                
        except ValueError as e:
            flash('Data de validade inválida!', 'danger')
            return redirect(url_for('consumidor.meus_dados'))
        
        # Em produção, você deve usar um serviço de tokenização para cartões
        # Aqui estamos simulando um token
        token = f"tok_{uuid.uuid4().hex[:16]}"
        
        conn = get_connection()
        cursor = conn.cursor()
        
        # Salvar no formato MM/AA como veio do formulário
        cursor.execute("""
            INSERT INTO cartao_de_credito (id, token, titular, bandeira, data_validade, id_consumidor)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (str(uuid.uuid4()), token, titular, bandeira, data_validade, current_user.id))
        
        conn.commit()
        flash('Cartão adicionado com sucesso!', 'success')
        
    except Exception as e:
        flash('Erro ao adicionar cartão: ' + str(e), 'danger')
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
    
    return redirect(url_for('consumidor.meus_dados'))

@consumidor_bp.route('/cartao/excluir/<cartao_id>')
def excluir_cartao(cartao_id):
    """Excluir cartão de crédito"""
    conn = None
    cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # Verificar se o cartão pertence ao usuário
        cursor.execute("SELECT id FROM cartao_de_credito WHERE id = %s AND id_consumidor = %s", 
                      (cartao_id, current_user.id))
        if not cursor.fetchone():
            flash('Cartão não encontrado!', 'danger')
            return redirect(url_for('consumidor.meus_dados'))
        
        cursor.execute("""
            DELETE FROM cartao_de_credito 
            WHERE id = %s AND id_consumidor = %s
        """, (cartao_id, current_user.id))
        
        conn.commit()
        flash('Cartão excluído com sucesso!', 'success')
        
    except Exception as e:
        flash('Erro ao excluir cartão: ' + str(e), 'danger')
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
    
    return redirect(url_for('consumidor.meus_dados'))

@consumidor_bp.route('/adicionar-carrinho/<produto_id>', methods=['POST'])
def adicionar_carrinho(produto_id):
    """Adicionar produto ao carrinho"""
    conn = None
    cursor = None
    try:
        quantidade = int(request.form.get('quantidade', 1))
        
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Buscar informações do produto
        cursor.execute("""
            SELECT p.*, r.nome as restaurante_nome, r.id as restaurante_id
            FROM produto p 
            JOIN restaurante r ON p.id_restaurante = r.id 
            WHERE p.id = %s AND p.stats = 'ativo'
        """, (produto_id,))
        produto = cursor.fetchone()
        
        if not produto:
            flash('Produto não encontrado!', 'danger')
            return redirect(request.referrer)
        
        # Inicializar carrinho na sessão se não existir
        if 'carrinho' not in session:
            session['carrinho'] = {}
        
        carrinho = session['carrinho']
        
        # Verificar se já existe produto de outro restaurante no carrinho
        if carrinho:
            primeiro_item = next(iter(carrinho.values()))
            if primeiro_item['restaurante_id'] != produto['restaurante_id']:
                flash('Você só pode pedir de um restaurante por vez! Esvazie o carrinho para adicionar produtos de outro restaurante.', 'warning')
                return redirect(request.referrer)
        
        # Adicionar/atualizar produto no carrinho
        if produto_id in carrinho:
            carrinho[produto_id]['quantidade'] += quantidade
        else:
            carrinho[produto_id] = {
                'nome': produto['nome'],
                'preco': float(produto['preco']),
                'quantidade': quantidade,
                'restaurante_id': produto['restaurante_id'],
                'restaurante_nome': produto['restaurante_nome'],
                'observacoes': ''
            }
        
        session['carrinho'] = carrinho
        session.modified = True
        
        flash(f'{produto["nome"]} adicionado ao carrinho!', 'success')
        
    except Exception as e:
        flash('Erro ao adicionar ao carrinho: ' + str(e), 'danger')
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
    
    return redirect(request.referrer)
@consumidor_bp.route('/carrinho')
def carrinho():
    """Página do carrinho de compras"""
    carrinho = session.get('carrinho', {})
    total = sum(item['preco'] * item['quantidade'] for item in carrinho.values())
    
    # Buscar endereços do usuário
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM endereco WHERE id_cliente = %s", (current_user.id,))
    enderecos = cursor.fetchall()
    
    # Buscar cartões do usuário
    cursor.execute("SELECT * FROM cartao_de_credito WHERE id_consumidor = %s", (current_user.id,))
    cartoes = cursor.fetchall()
    
    cursor.close()
    conn.close()
    
    return render_template('carrinho.html', 
                         carrinho=carrinho, 
                         total=total,
                         enderecos=enderecos,
                         cartoes=cartoes)

@consumidor_bp.route('/atualizar-carrinho/<produto_id>', methods=['POST'])
def atualizar_carrinho(produto_id):
    """Atualizar quantidade ou remover item do carrinho"""
    try:
        carrinho = session.get('carrinho', {})
        
        if produto_id in carrinho:
            acao = request.form.get('acao')
            
            if acao == 'atualizar':
                nova_quantidade = int(request.form.get('quantidade', 1))
                if nova_quantidade > 0:
                    carrinho[produto_id]['quantidade'] = nova_quantidade
                    carrinho[produto_id]['observacoes'] = request.form.get('observacoes', '')
                else:
                    del carrinho[produto_id]
            elif acao == 'remover':
                del carrinho[produto_id]
            
            session['carrinho'] = carrinho
            session.modified = True
            flash('Carrinho atualizado!', 'success')
        else:
            flash('Item não encontrado no carrinho!', 'danger')
            
    except Exception as e:
        flash('Erro ao atualizar carrinho: ' + str(e), 'danger')
    
    return redirect(url_for('consumidor.carrinho'))

@consumidor_bp.route('/limpar-carrinho')
def limpar_carrinho():
    """Esvaziar carrinho"""
    session.pop('carrinho', None)
    flash('Carrinho esvaziado!', 'success')
    return redirect(url_for('consumidor.carrinho'))

@consumidor_bp.route('/finalizar-pedido', methods=['POST'])
def finalizar_pedido():
    """Finalizar pedido e criar no banco de dados"""
    conn = None
    cursor = None
    
    try:
        carrinho = session.get('carrinho', {})
        
        if not carrinho:
            flash('Carrinho vazio!', 'danger')
            return redirect(url_for('consumidor.carrinho'))
        
        # Dados do formulário
        endereco_id = request.form.get('endereco_entrega')
        forma_pagamento = request.form.get('forma_pagamento')
        cartao_id = request.form.get('cartao_id')
        observacoes_gerais = request.form.get('observacoes_gerais', '')
        
        # Validações
        if not endereco_id:
            flash('Selecione um endereço de entrega!', 'danger')
            return redirect(url_for('consumidor.carrinho'))
        
        if not forma_pagamento:
            flash('Selecione uma forma de pagamento!', 'danger')
            return redirect(url_for('consumidor.carrinho'))
        
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Buscar endereço selecionado
        cursor.execute("SELECT * FROM endereco WHERE id = %s AND id_cliente = %s", 
                      (endereco_id, current_user.id))
        endereco = cursor.fetchone()
        
        if not endereco:
            flash('Endereço não encontrado!', 'danger')
            return redirect(url_for('consumidor.carrinho'))
        
        # Calcular total
        total = sum(item['preco'] * item['quantidade'] for item in carrinho.values())
        
        # Buscar restaurante do primeiro item (todos são do mesmo restaurante)
        primeiro_item = next(iter(carrinho.values()))
        restaurante_id = primeiro_item['restaurante_id']
        
        # Criar pedido
        pedido_id = str(uuid.uuid4())
        cursor.execute("""
            INSERT INTO pedidos (id, data_hora, stats, forma_pagamento, valor_total, 
                               id_consumidor, id_restaurante, endereco_entrega, observacoes)
            VALUES (%s, NOW(), 'pendente', %s, %s, %s, %s, %s, %s)
        """, (pedido_id, forma_pagamento, total, current_user.id, restaurante_id, 
              f"{endereco['logradouro']}, {endereco['numero']} - {endereco['bairro']}", 
              observacoes_gerais))
        
        # Adicionar itens do pedido
        for produto_id, item in carrinho.items():
            subtotal = item['preco'] * item['quantidade']
            cursor.execute("""
                INSERT INTO item_pedido (id_pedido, id_produto, qtd, observacoes, subtotal)
                VALUES (%s, %s, %s, %s, %s)
            """, (pedido_id, produto_id, item['quantidade'], item.get('observacoes', ''), subtotal))
        
        conn.commit()
        
        # Limpar carrinho
        session.pop('carrinho', None)
        

        return redirect(url_for('consumidor.meus_pedidos'))
        
    except Exception as e:
        if conn:
            conn.rollback()
        flash('Erro ao finalizar pedido: ' + str(e), 'danger')
        return redirect(url_for('consumidor.carrinho'))
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

@consumidor_bp.route('/meus-pedidos')
def meus_pedidos():
    """
    Página para listar todos os pedidos do consumidor logado.
    """
    pedidos = []
    
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)

        # DEBUG: Verificar email do usuário logado
        print(f"DEBUG: Email do usuário logado: {current_user.email}")
        
        # Recupera id do consumidor pelo usuário logado (JOIN com cliente)
        cursor.execute("""
            SELECT c.id AS id_consumidor
            FROM consumidor c
            JOIN cliente cl ON c.id = cl.id
            WHERE cl.email = %s
        """, (current_user.email,))
        result = cursor.fetchone()
        
        # DEBUG: Verificar resultado da query
        print(f"DEBUG: Resultado da busca do consumidor: {result}")
        
        if not result:
            flash("Erro: consumidor não encontrado.", "danger")
            return render_template('meus_pedidos.html', pedidos=[])
        
        id_consumidor = result["id_consumidor"]
        
        # DEBUG: Verificar ID do consumidor
        print(f"DEBUG: ID do consumidor encontrado: {id_consumidor}")

        # CARREGAR PEDIDOS DO CONSUMIDOR - CORRIGIDO para usar colunas existentes
        cursor.execute("""
            SELECT p.id, p.data_hora, p.stats, p.valor_total, p.forma_pagamento, p.observacoes,
                   r.nome AS restaurante_nome
            FROM pedidos p
            JOIN restaurante r ON p.id_restaurante = r.id
            WHERE p.id_consumidor = %s
            ORDER BY p.data_hora DESC
        """, (id_consumidor,))
        pedidos_data = cursor.fetchall()
        
        # DEBUG: Verificar pedidos encontrados
        print(f"DEBUG: Pedidos encontrados: {len(pedidos_data)}")

        # Formatar os pedidos com seus itens
        pedidos_formatados = []
        for pedido in pedidos_data:
            # Buscar itens do pedido - CORRIGIDO para usar colunas existentes
            cursor.execute("""
                SELECT ip.qtd as quantidade, ip.subtotal as preco_unitario,
                       pr.nome AS produto_nome
                FROM item_pedido ip
                JOIN produto pr ON ip.id_produto = pr.id
                WHERE ip.id_pedido = %s
            """, (pedido['id'],))
            itens_data = cursor.fetchall()
            
            # Formatar itens do pedido
            itens_pedido = []
            for item in itens_data:
                itens_pedido.append({
                    'produto_nome': item['produto_nome'],
                    'quantidade': item['quantidade'],
                    'preco': item['preco_unitario']
                })
            
            # Formatar pedido completo - CORRIGIDO para usar colunas existentes
            pedido_formatado = {
                'id': pedido['id'],
                'restaurante_nome': pedido['restaurante_nome'],
                'data_hora': pedido['data_hora'],
                'valor_total': pedido['valor_total'],
                'status': pedido['stats'],  # Usando 'stats' que existe na tabela
                'forma_pagamento': pedido['forma_pagamento'],
                'observacoes_gerais': pedido['observacoes'],  # Corrigido: 'observacoes' não 'observacoes_gerais'
                'itens': itens_pedido
            }
            
            pedidos_formatados.append(pedido_formatado)
            
            # DEBUG: Verificar pedido formatado
            print(f"DEBUG: Pedido {pedido['id']} - {len(itens_pedido)} itens")

        pedidos = pedidos_formatados

    except Exception as e:
        flash("Erro ao carregar pedidos: " + str(e), "danger")
        print(f"DEBUG: Erro ocorrido: {str(e)}")
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

    return render_template('meus_pedidos.html', pedidos=pedidos)

@consumidor_bp.route('/remover-item-carrinho/<produto_id>', methods=['POST'])
def remover_item_carrinho(produto_id):
    """Remover item específico do carrinho"""
    try:
        carrinho = session.get('carrinho', {})
        
        if produto_id in carrinho:
            del carrinho[produto_id]
            session['carrinho'] = carrinho
            session.modified = True
            
            return {
                'success': True,
                'message': 'Item removido do carrinho',
                'carrinho_count': len(carrinho)
            }
        else:
            return {
                'success': False,
                'message': 'Item não encontrado no carrinho'
            }, 404
            
    except Exception as e:
        return {
            'success': False,
            'message': f'Erro ao remover item: {str(e)}'
        }, 500

@consumidor_bp.route('/cancelar-pedido/<pedido_id>')
def cancelar_pedido(pedido_id):
    """
    Cancelar pedido - apenas se o status for 'pendente'
    """
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)

        # Primeiro, verificar se o pedido existe e pertence ao consumidor logado
        cursor.execute("""
            SELECT c.id AS id_consumidor
            FROM consumidor c
            JOIN cliente cl ON c.id = cl.id
            WHERE cl.email = %s
        """, (current_user.email,))
        result = cursor.fetchone()
        
        if not result:
            flash("Erro: consumidor não encontrado.", "danger")
            return redirect(url_for('consumidor.meus_pedidos'))
        
        id_consumidor = result["id_consumidor"]

        # Verificar se o pedido existe, pertence ao consumidor e está com status 'pendente'
        cursor.execute("""
            SELECT p.id, p.stats, p.id_consumidor
            FROM pedidos p
            WHERE p.id = %s AND p.id_consumidor = %s
        """, (pedido_id, id_consumidor))
        pedido = cursor.fetchone()
        
        if not pedido:
            flash("Pedido não encontrado.", "danger")
            return redirect(url_for('consumidor.meus_pedidos'))
        
        # Verificar se o pedido está com status 'pendente'
        if pedido['stats'] != 'pendente':
            flash("Este pedido não pode ser cancelado. Apenas pedidos pendentes podem ser cancelados.", "warning")
            return redirect(url_for('consumidor.meus_pedidos'))
        
        # Atualizar o status do pedido para 'cancelado'
        cursor.execute("""
            UPDATE pedidos 
            SET stats = 'cancelado' 
            WHERE id = %s AND id_consumidor = %s
        """, (pedido_id, id_consumidor))
        
        conn.commit()
        flash("Pedido cancelado com sucesso!", "success")
        
    except Exception as e:
        flash("Erro ao cancelar pedido: " + str(e), "danger")
        print(f"DEBUG: Erro ao cancelar pedido: {str(e)}")
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
    
    return redirect(url_for('consumidor.meus_pedidos'))

@consumidor_bp.route('/avaliar-restaurante/<pedido_id>')
def avaliar_restaurante(pedido_id):
    """
    Página para avaliar o restaurante após pedido entregue
    """
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)

        # Buscar ID do consumidor logado
        cursor.execute("""
            SELECT c.id AS id_consumidor
            FROM consumidor c
            JOIN cliente cl ON c.id = cl.id
            WHERE cl.email = %s
        """, (current_user.email,))
        result = cursor.fetchone()
        
        if not result:
            flash("Erro: consumidor não encontrado.", "danger")
            return redirect(url_for('consumidor.meus_pedidos'))
        
        id_consumidor = result["id_consumidor"]

        # Buscar informações do pedido
        cursor.execute("""
            SELECT p.*, r.id as restaurante_id, r.nome as restaurante_nome
            FROM pedidos p
            JOIN restaurante r ON p.id_restaurante = r.id
            WHERE p.id = %s AND p.id_consumidor = %s
        """, (pedido_id, id_consumidor))
        pedido = cursor.fetchone()
        
        if not pedido:
            flash("Pedido não encontrado.", "danger")
            return redirect(url_for('consumidor.meus_pedidos'))
        
        # Verificar se o pedido foi entregue
        if pedido['stats'] != 'entregue':
            flash("Apenas pedidos entregues podem ser avaliados.", "warning")
            return redirect(url_for('consumidor.meus_pedidos'))
        
        # Verificar se já existe avaliação para este pedido
        cursor.execute("""
            SELECT id FROM avaliacao 
            WHERE id_restaurante = %s AND id_consumidor = %s
        """, (pedido['restaurante_id'], id_consumidor))
        avaliacao_existente = cursor.fetchone()
        
        return render_template('avaliar_restaurante.html', 
                             pedido=pedido, 
                             avaliacao_existente=bool(avaliacao_existente))
        
    except Exception as e:
        flash("Erro ao carregar página de avaliação: " + str(e), "danger")
        return redirect(url_for('consumidor.meus_pedidos'))
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

@consumidor_bp.route('/salvar-avaliacao/<pedido_id>', methods=['POST'])
def salvar_avaliacao(pedido_id):
    """
    Salvar avaliação do restaurante
    """
    conn = None
    cursor = None
    
    try:
        nota = request.form.get('nota')
        feedback = request.form.get('feedback', '').strip()
        
        # Validações
        if not nota:
            flash("Por favor, selecione uma nota.", "danger")
            return redirect(url_for('consumidor.avaliar_restaurante', pedido_id=pedido_id))
        
        nota = int(nota)
        if nota < 1 or nota > 5:
            flash("A nota deve ser entre 1 e 5.", "danger")
            return redirect(url_for('consumidor.avaliar_restaurante', pedido_id=pedido_id))
        
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)

        # Buscar ID do consumidor logado
        cursor.execute("""
            SELECT c.id AS id_consumidor
            FROM consumidor c
            JOIN cliente cl ON c.id = cl.id
            WHERE cl.email = %s
        """, (current_user.email,))
        result = cursor.fetchone()
        
        if not result:
            flash("Erro: consumidor não encontrado.", "danger")
            return redirect(url_for('consumidor.meus_pedidos'))
        
        id_consumidor = result["id_consumidor"]

        # Buscar informações do pedido
        cursor.execute("""
            SELECT p.*, r.id as restaurante_id, r.nome as restaurante_nome
            FROM pedidos p
            JOIN restaurante r ON p.id_restaurante = r.id
            WHERE p.id = %s AND p.id_consumidor = %s
        """, (pedido_id, id_consumidor))
        pedido = cursor.fetchone()
        
        if not pedido:
            flash("Pedido não encontrado.", "danger")
            return redirect(url_for('consumidor.meus_pedidos'))
        
        # Verificar se o pedido foi entregue
        if pedido['stats'] != 'entregue':
            flash("Apenas pedidos entregues podem ser avaliados.", "warning")
            return redirect(url_for('consumidor.meus_pedidos'))
        
        # Verificar se já existe avaliação para este pedido
        cursor.execute("""
            SELECT id FROM avaliacao 
            WHERE id_restaurante = %s AND id_consumidor = %s
        """, (pedido['restaurante_id'], id_consumidor))
        avaliacao_existente = cursor.fetchone()
        
        if avaliacao_existente:
            # Atualizar avaliação existente
            cursor.execute("""
                UPDATE avaliacao 
                SET nota = %s, feedback = %s, data_hora = NOW()
                WHERE id_restaurante = %s AND id_consumidor = %s
            """, (nota, feedback, pedido['restaurante_id'], id_consumidor))
            flash("Avaliação atualizada com sucesso!", "success")
        else:
            # Criar nova avaliação
            cursor.execute("""
                INSERT INTO avaliacao (id, feedback, data_hora, nota, id_restaurante, id_consumidor)
                VALUES (%s, %s, NOW(), %s, %s, %s)
            """, (str(uuid.uuid4()), feedback, nota, pedido['restaurante_id'], id_consumidor))
            flash("Avaliação enviada com sucesso!", "success")
        
        # Atualizar média de avaliações do restaurante
        cursor.execute("""
            SELECT AVG(nota) as media, COUNT(*) as total
            FROM avaliacao 
            WHERE id_restaurante = %s
        """, (pedido['restaurante_id'],))
        stats = cursor.fetchone()
        
        if stats and stats['media']:
            cursor.execute("""
                UPDATE restaurante 
                SET avaliacao = %s
                WHERE id = %s
            """, (float(stats['media']), pedido['restaurante_id']))
        
        conn.commit()
        
    except Exception as e:
        if conn:
            conn.rollback()
        flash("Erro ao salvar avaliação: " + str(e), "danger")
        return redirect(url_for('consumidor.avaliar_restaurante', pedido_id=pedido_id))
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
    
    return redirect(url_for('consumidor.meus_pedidos'))