from flask import Blueprint, request, redirect, url_for, flash, render_template
from flask_login import current_user
from utils.database import get_connection
import uuid
from datetime import datetime  

restaurante_bp = Blueprint('restaurante', __name__, template_folder='templates')


@restaurante_bp.route('/dashboard/produtos', methods=['GET', 'POST'])
def dashboard_produtos():
    """
    Página para cadastrar e listar produtos do restaurante logado.
    """
    # Inicializar variáveis com valores padrão
    produtos = []
    pedidos = []
    avaliacoes = []
    stats_avaliacoes = {'media_avaliacoes': 0, 'total_avaliacoes': 0}
    nome_restaurante = "Restaurante"
    tipo_culinaria = ""
    produto_editar = None
    
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)

        # Recupera id do restaurante pelo usuário logado
        cursor.execute("""
            SELECT r.id AS id_restaurante, r.nome AS nome_restaurante, r.tipo_culinaria
            FROM restaurante r
            JOIN cliente c ON r.id = c.id
            WHERE c.email = %s
        """, (current_user.email,))
        result = cursor.fetchone()
        
        if not result:
            flash("Erro: restaurante não encontrado.", "danger")
            return redirect(url_for("home.index"))
        
        id_restaurante = result["id_restaurante"]
        nome_restaurante = result["nome_restaurante"]
        tipo_culinaria = result["tipo_culinaria"] or ""
        
        print(f"DEBUG: Restaurante ID: {id_restaurante}")

        # CARREGAR PRODUTOS
        cursor.execute("""
            SELECT id, nome, descricao, preco, stats
            FROM produto
            WHERE id_restaurante = %s
            ORDER BY nome
        """, (id_restaurante,))
        produtos = cursor.fetchall()
        print(f"DEBUG: Total de produtos: {len(produtos)}")

        # VERIFICAR SE É PARA EDITAR UM PRODUTO
        produto_id_editar = request.args.get('editar')
        print(f"DEBUG: Produto ID para editar: {produto_id_editar}")
        
        if produto_id_editar:
            cursor.execute("""
                SELECT id, nome, descricao, preco, stats
                FROM produto
                WHERE id = %s AND id_restaurante = %s
            """, (produto_id_editar, id_restaurante))
            produto_editar = cursor.fetchone()
            print(f"DEBUG: Produto encontrado para edição: {produto_editar}")

        # VERIFICAR SE É PARA EXCLUIR UM PRODUTO
        produto_id_excluir = request.args.get('excluir')
        if produto_id_excluir:
            cursor.execute("""
                DELETE FROM produto
                WHERE id = %s AND id_restaurante = %s
            """, (produto_id_excluir, id_restaurante))
            conn.commit()
            flash("Produto excluído com sucesso!", "success")
            return redirect(url_for('restaurante.dashboard_produtos'))

        # CARREGAR PEDIDOS DO RESTAURANTE
        cursor.execute("""
            SELECT p.id, p.data_hora, p.stats, p.valor_total, 
                   c.nome AS nome_consumidor
            FROM pedidos p
            JOIN consumidor c ON p.id_consumidor = c.id
            WHERE p.id_restaurante = %s
            ORDER BY p.data_hora DESC
        """, (id_restaurante,))
        pedidos = cursor.fetchall()

        # CARREGAR AVALIAÇÕES DO RESTAURANTE
        cursor.execute("""
            SELECT a.feedback, a.data_hora, a.nota, 
                   c.nome AS nome_consumidor
            FROM avaliacao a
            JOIN consumidor c ON a.id_consumidor = c.id
            WHERE a.id_restaurante = %s
            ORDER BY a.data_hora DESC
        """, (id_restaurante,))
        avaliacoes = cursor.fetchall()

        # CALCULAR MÉDIA DAS AVALIAÇÕES
        cursor.execute("""
            SELECT AVG(nota) as media_avaliacoes, COUNT(*) as total_avaliacoes
            FROM avaliacao
            WHERE id_restaurante = %s
        """, (id_restaurante,))
        stats_result = cursor.fetchone()
        
        if stats_result:
            stats_avaliacoes = {
                'media_avaliacoes': float(stats_result['media_avaliacoes'] or 0),
                'total_avaliacoes': stats_result['total_avaliacoes'] or 0
            }

        # PROCESSAR FORMULÁRIOS POST
        if request.method == 'POST':
            # Verificar se é um cadastro de produto
            if 'nome' in request.form and 'produto_id' not in request.form:
                nome = request.form.get('nome')
                descricao = request.form.get('descricao')
                preco = request.form.get('preco')
                status = request.form.get('status', 'ativo')
                
                cursor.execute("""
                    INSERT INTO produto (id_restaurante, nome, descricao, preco, stats)
                    VALUES (%s, %s, %s, %s, %s)
                """, (id_restaurante, nome, descricao, preco, status))
                conn.commit()
                flash("Produto cadastrado com sucesso!", "success")
                return redirect(url_for('restaurante.dashboard_produtos'))
            
            # Verificar se é uma atualização de produto
            elif 'produto_id' in request.form:
                produto_id = request.form.get('produto_id')
                nome = request.form.get('nome')
                descricao = request.form.get('descricao')
                preco = request.form.get('preco')
                status = request.form.get('status', 'ativo')
                
                print(f"DEBUG: Atualizando produto ID: {produto_id}")
                print(f"DEBUG: Novos dados - Nome: {nome}, Preço: {preco}, Status: {status}")
                
                cursor.execute("""
                    UPDATE produto 
                    SET nome = %s, descricao = %s, preco = %s, stats = %s
                    WHERE id = %s AND id_restaurante = %s
                """, (nome, descricao, preco, status, produto_id, id_restaurante))
                conn.commit()
                flash("Produto atualizado com sucesso!", "success")
                return redirect(url_for('restaurante.dashboard_produtos'))
            
            # Verificar se é uma atualização de status de pedido
            elif 'pedido_id' in request.form and 'novo_status' in request.form:
                pedido_id = request.form.get('pedido_id')
                novo_status = request.form.get('novo_status')
                
                cursor.execute("""
                    UPDATE pedidos 
                    SET stats = %s 
                    WHERE id = %s AND id_restaurante = %s
                """, (novo_status, pedido_id, id_restaurante))
                conn.commit()
                return redirect(url_for('restaurante.dashboard_produtos'))

    except Exception as e:
        flash("Erro ao processar: " + str(e), "danger")
        print(f"DEBUG: Erro ocorrido: {str(e)}")
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

    return render_template("dashboard_restaurante.html", 
                         produtos=produtos, 
                         pedidos=pedidos, 
                         avaliacoes=avaliacoes,
                         stats_avaliacoes=stats_avaliacoes,
                         nome_restaurante=nome_restaurante,
                         tipo_culinaria=tipo_culinaria,
                         produto_editar=produto_editar)

@restaurante_bp.route('/dados-restaurante')
def dados_restaurante():
    """
    Página de gerenciamento de dados do restaurante
    """
    enderecos = []
    contatos = []
    restaurante_info = None
    
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)

        # Buscar ID do restaurante pelo usuário logado
        cursor.execute("""
            SELECT r.id AS id_restaurante, r.nome AS nome_restaurante,
                   r.tipo_culinaria, r.avaliacao
            FROM restaurante r
            JOIN cliente c ON r.id = c.id
            WHERE c.email = %s
        """, (current_user.email,))
        result = cursor.fetchone()
        
        if not result:
            flash("Erro: restaurante não encontrado.", "danger")
            return redirect(url_for("home.index"))
        
        id_restaurante = result["id_restaurante"]
        restaurante_info = result

        # Buscar endereços do restaurante
        cursor.execute("""
            SELECT * FROM endereco 
            WHERE id_cliente = %s
            ORDER BY logradouro
        """, (id_restaurante,))
        enderecos = cursor.fetchall()

        # Buscar contatos do restaurante
        cursor.execute("""
            SELECT * FROM contato 
            WHERE id_cliente = %s
            ORDER BY tipo, numero
        """, (id_restaurante,))
        contatos = cursor.fetchall()

    except Exception as e:
        flash("Erro ao carregar dados: " + str(e), "danger")
        print(f"DEBUG: Erro em dados_restaurante: {str(e)}")
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

    return render_template("meus_dados_restaurante.html",
                         restaurante=restaurante_info,
                         enderecos=enderecos,
                         contatos=contatos)

@restaurante_bp.route('/horarios-atendimento')
def horarios_atendimento():
    """
    Página para gerenciar horários de atendimento do restaurante
    """
    horarios = []
    restaurante_info = None
    
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)

        # Buscar ID do restaurante
        cursor.execute("""
            SELECT r.id AS id_restaurante, r.nome AS nome_restaurante,
                   r.tipo_culinaria
            FROM restaurante r
            JOIN cliente c ON r.id = c.id
            WHERE c.email = %s
        """, (current_user.email,))
        result = cursor.fetchone()
        
        if not result:
            flash("Erro: restaurante não encontrado.", "danger")
            return redirect(url_for("home.index"))
        
        id_restaurante = result["id_restaurante"]
        restaurante_info = result

        # Buscar horários do restaurante
        cursor.execute("""
            SELECT * FROM horarios 
            WHERE id_restaurante = %s
            ORDER BY 
                CASE 
                    WHEN dia = 'Domingo' THEN 1
                    WHEN dia = 'Segunda' THEN 2
                    WHEN dia = 'Terça' THEN 3
                    WHEN dia = 'Quarta' THEN 4
                    WHEN dia = 'Quinta' THEN 5
                    WHEN dia = 'Sexta' THEN 6
                    WHEN dia = 'Sábado' THEN 7
                END
        """, (id_restaurante,))
        horarios = cursor.fetchall()

    except Exception as e:
        flash("Erro ao carregar horários: " + str(e), "danger")
        print(f"DEBUG: Erro em horarios_atendimento: {str(e)}")
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

    return render_template("horarios_atendimento.html",
                         restaurante=restaurante_info,
                         horarios=horarios)

@restaurante_bp.route('/horario/adicionar', methods=['POST'])
def adicionar_horario():
    """Adicionar novo horário de atendimento"""
    try:
        dia = request.form.get('dia')
        hora_inicio = request.form.get('hora_inicio')
        hora_fim = request.form.get('hora_fim')
        
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)

        # Buscar ID do restaurante
        cursor.execute("""
            SELECT r.id AS id_restaurante
            FROM restaurante r
            JOIN cliente c ON r.id = c.id
            WHERE c.email = %s
        """, (current_user.email,))
        result = cursor.fetchone()
        
        if not result:
            flash("Erro: restaurante não encontrado.", "danger")
            return redirect(url_for('restaurante.horarios_atendimento'))
        
        id_restaurante = result["id_restaurante"]
        
        # Verificar se já existe horário para este dia
        cursor.execute("""
            SELECT id FROM horarios 
            WHERE id_restaurante = %s AND dia = %s
        """, (id_restaurante, dia))
        
        if cursor.fetchone():
            flash(f'Já existe um horário cadastrado para {dia}.', 'warning')
            return redirect(url_for('restaurante.horarios_atendimento'))
        
        # Inserir horário
        cursor.execute("""
            INSERT INTO horarios (id, dia, hora_inicio, hora_fim, id_restaurante)
            VALUES (%s, %s, %s, %s, %s)
        """, (str(uuid.uuid4()), dia, hora_inicio, hora_fim, id_restaurante))
        
        conn.commit()
        flash('Horário adicionado com sucesso!', 'success')
        
    except Exception as e:
        flash('Erro ao adicionar horário: ' + str(e), 'danger')
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
    
    return redirect(url_for('restaurante.horarios_atendimento'))

@restaurante_bp.route('/horario/editar/<horario_id>', methods=['POST'])
def editar_horario(horario_id):
    """Editar horário de atendimento existente"""
    try:
        dia = request.form.get('dia')
        hora_inicio = request.form.get('hora_inicio')
        hora_fim = request.form.get('hora_fim')
        
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)

        # Buscar ID do restaurante
        cursor.execute("""
            SELECT r.id AS id_restaurante
            FROM restaurante r
            JOIN cliente c ON r.id = c.id
            WHERE c.email = %s
        """, (current_user.email,))
        result = cursor.fetchone()
        
        if not result:
            flash("Erro: restaurante não encontrado.", "danger")
            return redirect(url_for('restaurante.horarios_atendimento'))
        
        id_restaurante = result["id_restaurante"]
        
        # Atualizar horário
        cursor.execute("""
            UPDATE horarios 
            SET dia = %s, hora_inicio = %s, hora_fim = %s
            WHERE id = %s AND id_restaurante = %s
        """, (dia, hora_inicio, hora_fim, horario_id, id_restaurante))
        
        conn.commit()
        flash('Horário atualizado com sucesso!', 'success')
        
    except Exception as e:
        flash('Erro ao atualizar horário: ' + str(e), 'danger')
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
    
    return redirect(url_for('restaurante.horarios_atendimento'))

@restaurante_bp.route('/horario/excluir/<horario_id>')
def excluir_horario(horario_id):
    """Excluir horário de atendimento"""
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)

        # Buscar ID do restaurante
        cursor.execute("""
            SELECT r.id AS id_restaurante
            FROM restaurante r
            JOIN cliente c ON r.id = c.id
            WHERE c.email = %s
        """, (current_user.email,))
        result = cursor.fetchone()
        
        if not result:
            flash("Erro: restaurante não encontrado.", "danger")
            return redirect(url_for('restaurante.horarios_atendimento'))
        
        id_restaurante = result["id_restaurante"]
        
        # Excluir horário
        cursor.execute("""
            DELETE FROM horarios 
            WHERE id = %s AND id_restaurante = %s
        """, (horario_id, id_restaurante))
        
        conn.commit()
        flash('Horário excluído com sucesso!', 'success')
        
    except Exception as e:
        flash('Erro ao excluir horário: ' + str(e), 'danger')
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
    
    return redirect(url_for('restaurante.horarios_atendimento'))

# ===== ENDEREÇOS DO RESTAURANTE =====
@restaurante_bp.route('/endereco/adicionar', methods=['POST'])
def adicionar_endereco_restaurante():
    """Adicionar novo endereço para o restaurante"""
    try:
        logradouro = request.form.get('logradouro')
        numero = request.form.get('numero')
        complemento = request.form.get('complemento', '')
        bairro = request.form.get('bairro')
        cidade = request.form.get('cidade')
        estado = request.form.get('estado')
        pais = request.form.get('pais', 'Brasil')
        cep = request.form.get('cep')
        
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)

        # Buscar ID do restaurante
        cursor.execute("""
            SELECT r.id AS id_restaurante
            FROM restaurante r
            JOIN cliente c ON r.id = c.id
            WHERE c.email = %s
        """, (current_user.email,))
        result = cursor.fetchone()
        
        if not result:
            flash("Erro: restaurante não encontrado.", "danger")
            return redirect(url_for('restaurante.dados_restaurante'))
        
        id_restaurante = result["id_restaurante"]
        
        # Inserir endereço
        cursor.execute("""
            INSERT INTO endereco (id, logradouro, numero, complemento, bairro, 
                                cidade, estado, pais, cep, id_cliente)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (str(uuid.uuid4()), logradouro, numero, complemento, bairro, 
              cidade, estado, pais, cep, id_restaurante))
        
        conn.commit()
        flash('Endereço adicionado com sucesso!', 'success')
        
    except Exception as e:
        flash('Erro ao adicionar endereço: ' + str(e), 'danger')
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
    
    return redirect(url_for('restaurante.dados_restaurante'))

@restaurante_bp.route('/endereco/editar/<endereco_id>', methods=['POST'])
def editar_endereco_restaurante(endereco_id):
    """Editar endereço existente do restaurante"""
    try:
        logradouro = request.form.get('logradouro')
        numero = request.form.get('numero')
        complemento = request.form.get('complemento', '')
        bairro = request.form.get('bairro')
        cidade = request.form.get('cidade')
        estado = request.form.get('estado')
        pais = request.form.get('pais', 'Brasil')
        cep = request.form.get('cep')
        
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)

        # Buscar ID do restaurante
        cursor.execute("""
            SELECT r.id AS id_restaurante
            FROM restaurante r
            JOIN cliente c ON r.id = c.id
            WHERE c.email = %s
        """, (current_user.email,))
        result = cursor.fetchone()
        
        if not result:
            flash("Erro: restaurante não encontrado.", "danger")
            return redirect(url_for('restaurante.dados_restaurante'))
        
        id_restaurante = result["id_restaurante"]
        
        # Atualizar endereço
        cursor.execute("""
            UPDATE endereco 
            SET logradouro = %s, numero = %s, complemento = %s, bairro = %s, 
                cidade = %s, estado = %s, pais = %s, cep = %s
            WHERE id = %s AND id_cliente = %s
        """, (logradouro, numero, complemento, bairro, cidade, estado, pais, cep, 
              endereco_id, id_restaurante))
        
        conn.commit()
        flash('Endereço atualizado com sucesso!', 'success')
        
    except Exception as e:
        flash('Erro ao atualizar endereço: ' + str(e), 'danger')
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
    
    return redirect(url_for('restaurante.dados_restaurante'))

@restaurante_bp.route('/endereco/excluir/<endereco_id>')
def excluir_endereco_restaurante(endereco_id):
    """Excluir endereço do restaurante"""
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)

        # Buscar ID do restaurante
        cursor.execute("""
            SELECT r.id AS id_restaurante
            FROM restaurante r
            JOIN cliente c ON r.id = c.id
            WHERE c.email = %s
        """, (current_user.email,))
        result = cursor.fetchone()
        
        if not result:
            flash("Erro: restaurante não encontrado.", "danger")
            return redirect(url_for('restaurante.dados_restaurante'))
        
        id_restaurante = result["id_restaurante"]
        
        # Excluir endereço
        cursor.execute("""
            DELETE FROM endereco 
            WHERE id = %s AND id_cliente = %s
        """, (endereco_id, id_restaurante))
        
        conn.commit()
        flash('Endereço excluído com sucesso!', 'success')
        
    except Exception as e:
        flash('Erro ao excluir endereço: ' + str(e), 'danger')
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
    
    return redirect(url_for('restaurante.dados_restaurante'))

# ===== CONTATOS DO RESTAURANTE =====
@restaurante_bp.route('/contato/adicionar', methods=['POST'])
def adicionar_contato_restaurante():
    """Adicionar novo contato para o restaurante"""
    try:
        numero = request.form.get('numero')
        tipo = request.form.get('tipo')
        
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)

        # Buscar ID do restaurante
        cursor.execute("""
            SELECT r.id AS id_restaurante
            FROM restaurante r
            JOIN cliente c ON r.id = c.id
            WHERE c.email = %s
        """, (current_user.email,))
        result = cursor.fetchone()
        
        if not result:
            flash("Erro: restaurante não encontrado.", "danger")
            return redirect(url_for('restaurante.dados_restaurante'))
        
        id_restaurante = result["id_restaurante"]
        
        # Inserir contato
        cursor.execute("""
            INSERT INTO contato (id, numero, tipo, id_cliente)
            VALUES (%s, %s, %s, %s)
        """, (str(uuid.uuid4()), numero, tipo, id_restaurante))
        
        conn.commit()
        flash('Contato adicionado com sucesso!', 'success')
        
    except Exception as e:
        flash('Erro ao adicionar contato: ' + str(e), 'danger')
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
    
    return redirect(url_for('restaurante.dados_restaurante'))

@restaurante_bp.route('/contato/editar/<contato_id>', methods=['POST'])
def editar_contato_restaurante(contato_id):
    """Editar contato existente do restaurante"""
    try:
        numero = request.form.get('numero')
        tipo = request.form.get('tipo')
        
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)

        # Buscar ID do restaurante
        cursor.execute("""
            SELECT r.id AS id_restaurante
            FROM restaurante r
            JOIN cliente c ON r.id = c.id
            WHERE c.email = %s
        """, (current_user.email,))
        result = cursor.fetchone()
        
        if not result:
            flash("Erro: restaurante não encontrado.", "danger")
            return redirect(url_for('restaurante.dados_restaurante'))
        
        id_restaurante = result["id_restaurante"]
        
        # Atualizar contato
        cursor.execute("""
            UPDATE contato 
            SET numero = %s, tipo = %s 
            WHERE id = %s AND id_cliente = %s
        """, (numero, tipo, contato_id, id_restaurante))
        
        conn.commit()
        flash('Contato atualizado com sucesso!', 'success')
        
    except Exception as e:
        flash('Erro ao atualizar contato: ' + str(e), 'danger')
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
    
    return redirect(url_for('restaurante.dados_restaurante'))

@restaurante_bp.route('/contato/excluir/<contato_id>')
def excluir_contato_restaurante(contato_id):
    """Excluir contato do restaurante"""
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)

        # Buscar ID do restaurante
        cursor.execute("""
            SELECT r.id AS id_restaurante
            FROM restaurante r
            JOIN cliente c ON r.id = c.id
            WHERE c.email = %s
        """, (current_user.email,))
        result = cursor.fetchone()
        
        if not result:
            flash("Erro: restaurante não encontrado.", "danger")
            return redirect(url_for('restaurante.dados_restaurante'))
        
        id_restaurante = result["id_restaurante"]
        
        # Excluir contato
        cursor.execute("""
            DELETE FROM contato 
            WHERE id = %s AND id_cliente = %s
        """, (contato_id, id_restaurante))
        
        conn.commit()
        flash('Contato excluído com sucesso!', 'success')
        
    except Exception as e:
        flash('Erro ao excluir contato: ' + str(e), 'danger')
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
    
    return redirect(url_for('restaurante.dados_restaurante'))

