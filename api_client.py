import requests
from datetime import datetime, timedelta
from urllib.parse import quote_plus

def obter_codigo_ibge(nome_municipio, uf):
    if not nome_municipio or not uf:
        return ""
    try:
        url = f"https://servicodados.ibge.gov.br/api/v1/localidades/estados/{uf}/municipios"
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        municipios = response.json()
        for m in municipios:
            if m["nome"].lower() == nome_municipio.lower():
                return str(m["id"])
    except Exception as e:
        print(f"Erro ao buscar IBGE: {e}")
    return ""

def extrair_partes_controle(numero_controle):
    if not numero_controle:
        return None, None, None
    try:
        partes = numero_controle.split('-')
        if len(partes) < 3:
            return None, None, None
        cnpj = partes[0]
        resto = partes[2]
        seq_ano = resto.split('/')
        if len(seq_ano) != 2:
            return None, None, None
        sequencial = seq_ano[0]
        ano = seq_ano[1]
        return cnpj, ano, sequencial
    except Exception:
        return None, None, None

def buscar_licitacoes_pncp(filtros):
    termo_busca = filtros.get("termo", "").strip().lower()
    categoria = filtros.get("categoria", "")
    apenas_me_epp = filtros.get("me_epp") == "on" # Captura o checkbox
    
    data_inicial = filtros.get("data_inicial", "").replace("-", "")
    data_final = filtros.get("data_final", "").replace("-", "")
    
    if not data_inicial or not data_final:
        data_fim = datetime.now()
        data_inicio = data_fim - timedelta(days=30)
        data_inicial = data_inicio.strftime("%Y%m%d")
        data_final = data_fim.strftime("%Y%m%d")

    palavras_categorias = {
        "aquisicao": ["aquisição", "aquisicao", "compra", "fornecimento"],
        "servico": ["serviço", "servico", "prestação", "prestacao", "contratação de empresa"],
        "credenciamento": ["credenciamento"],
        "obras": ["obra", "engenharia", "reforma", "construção", "construcao"]
    }

    sinonimos = {
        "cadeira": ["cadeira", "assento", "mobiliário", "movel"],
        "mesa": ["mesa", "mobiliário", "movel", "escrivaninha"],
        "computador": ["computador", "desktop", "notebook", "informática", "hardware"],
        "papel": ["papel", "sulfite", "papelaria", "expediente"],
        "limpeza": ["limpeza", "higiene", "detergente", "saneante", "material de limpeza"],
        "carro": ["carro", "veículo", "automóvel", "locação de veículos", "transporte"]
    }

    url = "https://pncp.gov.br/api/consulta/v1/contratacoes/proposta"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json"
    }

    resultados = []
    
    codigo_ibge = ""
    if filtros.get("municipio") and filtros.get("uf"):
        codigo_ibge = obter_codigo_ibge(filtros["municipio"], filtros["uf"])

    val_min = float(filtros.get("valor_min") or 0.0)
    val_max = float(filtros.get("valor_max") or 0.0)

    termos_para_buscar = [termo_busca]
    if termo_busca:
        for chave, lista_sinonimos in sinonimos.items():
            if termo_busca in chave:
                termos_para_buscar.extend(lista_sinonimos)
                break

    for pagina in range(1, 3):
        params = {
            "dataInicial": data_inicial,
            "dataFinal": data_final,
            "pagina": pagina,
            "tamanhoPagina": 50
        }
        
        if filtros.get("modalidade"):
            params["codigoModalidadeContratacao"] = filtros["modalidade"]
        if filtros.get("uf"):
            params["uf"] = filtros["uf"]
        if codigo_ibge:
            params["codigoMunicipioIbge"] = codigo_ibge
        
        # PARÂMETRO OFICIAL DA API PARA ME/EPP
        if apenas_me_epp:
            params["excluirMeEpp"] = "false" 

        try:
            response = requests.get(url, params=params, headers=headers, timeout=15)
            
            if response.status_code == 404:
                break
                
            response.raise_for_status()
            dados = response.json()
            itens = dados.get("data", [])
            
            if not itens:
                break

            for item in itens:
                objeto = item.get("objetoCompra", "")
                objeto_lower = objeto.lower()
                
                match_termo = False
                if termo_busca:
                    for t in termos_para_buscar:
                        if t in objeto_lower:
                            match_termo = True
                            break
                    if not match_termo:
                        continue
                
                if categoria and categoria in palavras_categorias:
                    match_categoria = False
                    for palavra in palavras_categorias[categoria]:
                        if palavra in objeto_lower:
                            match_categoria = True
                            break
                    if not match_categoria:
                        continue

                valor_bruto = item.get("valorTotalEstimado", 0.0) or 0.0
                
                if val_min > 0 and valor_bruto < val_min:
                    continue
                if val_max > 0 and valor_bruto > val_max:
                    continue

                if valor_bruto == 0.0:
                    valor_formatado = "Sigiloso / Não informado"
                else:
                    valor_formatado = f"R$ {valor_bruto:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
                
                numero_controle = item.get("numeroControlePNCP", "")
                
                cnpj, ano, sequencial = extrair_partes_controle(numero_controle)
                if cnpj and ano and sequencial:
                    link_pncp = f"https://pncp.gov.br/app/editais/{cnpj}/{ano}/{sequencial}"
                else:
                    link_pncp = "#"

                orgao = item.get("orgaoEntidade", {}).get("razaoSocial", "")
                termo_google = f'"{numero_controle}" OR "edital {orgao}" licitação'
                link_google = f"https://www.google.com/search?q={quote_plus(termo_google)}"

                resultados.append({
                    "id": numero_controle,
                    "orgao": orgao or "Órgão não informado",
                    "objeto": objeto,
                    "uf": item.get("unidadeOrgao", {}).get("ufSigla", ""),
                    "municipio": item.get("unidadeOrgao", {}).get("municipioNome", ""),
                    "valor": valor_formatado,
                    "link_edital": link_pncp,
                    "link_google": link_google
                })
                    
        except requests.exceptions.Timeout:
            print(f"Timeout na página {pagina}. Pulando...")
            break
        except requests.exceptions.RequestException as e:
            print(f"Erro na página {pagina}: {e}")
            break

    return resultados
