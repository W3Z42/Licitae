from flask import Flask, render_template, request, redirect, url_for, flash
import database
import api_client
from datetime import datetime, timedelta

app = Flask(__name__)
app.secret_key = 'troque-esta-chave-em-producao'

database.init_db()

@app.route('/')
def index():
    alertas = database.listar_alertas()
    
    filtros = {
        "termo": request.args.get('termo', '').strip(),
        "categoria": request.args.get('categoria', ''),
        "modalidade": request.args.get('modalidade', ''),
        "uf": request.args.get('uf', ''),
        "municipio": request.args.get('municipio', '').strip(),
        "valor_min": request.args.get('valor_min', ''),
        "valor_max": request.args.get('valor_max', ''),
        "me_epp": request.args.get('me_epp', '') # NOVO CAMPO
    }
    
    tem_filtro = any(filtros.values())
    licitacoes = []
    
    if tem_filtro or request.args.get('buscar') == '1':
        if not tem_filtro:
            data_fim = datetime.now()
            data_inicio = data_fim - timedelta(days=30)
            filtros["data_inicial"] = data_inicio.strftime("%Y-%m-%d")
            filtros["data_final"] = data_fim.strftime("%Y-%m-%d")
            flash('Nenhum filtro selecionado. Exibindo as licitações mais recentes do país.', 'sucesso')
        
        licitacoes = api_client.buscar_licitacoes_pncp(filtros)
        
        if not licitacoes:
            flash('A busca não retornou resultados. Tente novamente.', 'erro')
            
    return render_template('index.html', lista_alertas=alertas, licitacoes=licitacoes, filtros=filtros, tem_filtro=tem_filtro)

@app.route('/ajuda')
def ajuda():
    return render_template('ajuda.html')

@app.route('/guia')
def guia():
    return render_template('guia.html')

@app.route('/alertas', methods=['POST'])
def adicionar_alerta():
    palavra = request.form.get('palavra_chave', '').strip()
    if palavra:
        database.inserir_alerta(palavra)
        flash(f'Alerta "{palavra}" cadastrado com sucesso.', 'sucesso')
    else:
        flash('Digite uma palavra-chave válida.', 'erro')
    return redirect(url_for('index'))

@app.route('/alertas/excluir/<int:id_alerta>', methods=['POST'])
def excluir_alerta(id_alerta):
    database.excluir_alerta(id_alerta)
    flash('Alerta removido.', 'sucesso')
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)
