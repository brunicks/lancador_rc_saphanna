#pdf_reader.py
import fitz
import re

# Função que padroniza o CNPJ
def standardize_cnpj(cnpj):
    """Remove all non-numeric characters from CNPJ"""
    return re.sub(r'[^0-9]', '', cnpj)

# Função que extrai o texto de um PDF
def extract_text_from_pdf(filepath):
    text = ""
    total_value = None  
    try:
        with fitz.open(filepath) as doc:
            # Extrair texto normal primeiro
            for page in doc:
                page_text = page.get_text("text")
                page_text = " ".join(page_text.splitlines())
                text += page_text + "\n"
        
            if not text.strip():
                raise ValueError("Nenhum texto extraído do PDF.")
            
            # Tentar métodos de extração em ordem de prioridade
            total_value = extract_total_value(text)
            
            # Se não encontrar valor pelo texto, tentar por posição
            if not total_value:
                total_value = extract_values_by_position(doc)
            
            # Tentar o método genérico de busca de valores monetários
            if not total_value:
                total_value = find_all_monetary_values(text)
            
            # Método específico para boletos
            if not total_value:
                total_value = extract_boleto_value(doc)
            
            if not total_value:
                raise ValueError("Não foi possível encontrar o valor total da fatura.")
        
    except Exception as e:
        text = f"Erro ao ler o PDF: {e}"

    return text, total_value

# Função que extrai o valor total de uma fatura
def extract_total_value(text):
    patterns = [
        r"R\$\s*([\d\.]+,\d{2})",  # Padrão básico para R$ seguido de valor
        r"VALOR.*?R\$\s*([\d\.]+,\d{2})",
        r"TOTAL\s*R\$\s*([\d\.]+,\d{2})",
        r"TOTAL.*?R\$\s*([\d\.]+,\d{2})",
        r"TOTAL FATURA.*?R\$\s*([\d\.]+,\d{2})",
        r"LÍQUIDO FATURA.*?([\d\.]+,\d{2})",
        r"TOTAL\s+LÍQUIDO\s+FATURA\s*R\$\s*([\d\.]+,\d{2})",
        r"TOTAL\s+FATURA\s*R\$\s*([\d\.]+,\d{2})",
        r"TOTAL\s+FATURA.*?R\$\s*([\d\.]+,\d{2})",
        r"VALOR TOTAL\s*R\$\s*([\d\.]+,\d{2})",
        r"TOTAL SERVIÇOS DE TELECOMUNICAÇÕES\s*R\$\s*([\d\.]+,\d{2})",
        r"TOTAL VOGEL SOL\. EM TEL\. E INF\. S\.A\.\s*([\d\.]+,\d{2})",
        r"VALOR\s*DO\s*DOCUMENTO\s*R?\$?\s*([\d\.]+,\d{2})",  # Boletos
        r"VALOR\s*COBRADO\s*R?\$?\s*([\d\.]+,\d{2})",         # Boletos
        r"VALOR\s*A\s*PAGAR\s*R?\$?\s*([\d\.]+,\d{2})",       # Boletos
        r"PAGAMENTO\s*R?\$?\s*([\d\.]+,\d{2})",               # Diversos
        r"VALOR\s*LÍQUIDO\s*R?\$?\s*([\d\.]+,\d{2})",         # Diversos
        r"(?:^|\s)([\d\.]{1,},[0-9]{2})(?:$|\s)",             # Valor isolado no formato NN.NNN,NN
    ]
    all_values = []
    for pattern in patterns:
        matches = re.findall(pattern, text, re.IGNORECASE | re.DOTALL) 
        all_values.extend(matches)
    unique_values = []
    seen = set()
    for value in all_values:
        if value not in seen:
            unique_values.append(value)
            seen.add(value)  
    return unique_values if unique_values else None

# Nova função: extrai valores baseados na sua posição no PDF
def extract_values_by_position(doc):
    """Extrai valores monetários baseado na sua posição no layout do PDF"""
    all_values = []
    
    # Posições comuns para valores totais (bottom-right, por exemplo)
    for page_num in range(len(doc)):
        page = doc[page_num]
        
        # Extrai blocos de texto com suas posições
        blocks = page.get_text("dict")["blocks"]
        
        for b in blocks:
            if "lines" not in b:
                continue
                
            for l in b["lines"]:
                for s in l["spans"]:
                    text = s["text"].strip()
                    
                    # Verifica se o texto parece ser um valor monetário
                    currency_match = re.search(r"R?\$?\s*([\d\.]+,\d{2})", text)
                    if currency_match:
                        value = currency_match.group(1)
                        all_values.append(value)
                    
                    # Textos isolados que parecem valores monetários
                    if re.match(r"^[\d\.]+,\d{2}$", text):
                        all_values.append(text)
                    
                    # Verificar se o texto está na parte inferior direita (comum em valores totais)
                    # Verificamos a posição relativa na página
                    bbox = s["bbox"]  # [x0, y0, x1, y1]
                    page_width = page.rect.width
                    page_height = page.rect.height
                    
                    # Posição relativa (0 a 1)
                    rel_x = bbox[0] / page_width
                    rel_y = bbox[1] / page_height
                    
                    # Se estiver no quadrante inferior direito e parecer um valor
                    if rel_x > 0.5 and rel_y > 0.5 and re.match(r"^[\d\.]+,\d{2}$", text):
                        all_values.append(text)
    
    # Remover duplicatas
    unique_values = []
    seen = set()
    for value in all_values:
        if value not in seen:
            unique_values.append(value)
            seen.add(value)
            
    return unique_values if unique_values else None

# Nova função: encontra todos os valores monetários no documento
def find_all_monetary_values(text):
    """Encontra todos os valores que parecem ser monetários no formato brasileiro"""
    # Padrão genérico para valores monetários no formato brasileiro
    pattern = r"(?:^|\s)([\d\.]{1,},[0-9]{2})(?:$|\s)"
    
    matches = re.findall(pattern, text)
    
    # Filtra valores muito pequenos (ex: menos de 10 reais) que provavelmente não são valor total
    filtered_values = [v for v in matches if float(v.replace(".", "").replace(",", ".")) >= 10]
    
    # Ordena por valor decrescente - normalmente o valor total é um dos maiores
    sorted_values = sorted(filtered_values, 
                         key=lambda x: float(x.replace(".", "").replace(",", ".")), 
                         reverse=True)
    
    return sorted_values if sorted_values else None

# Nova função: extração específica para boletos bancários
def extract_boleto_value(doc):
    """Extrai valores específicos de boletos bancários"""
    all_values = []
    
    for page_num in range(len(doc)):
        page = doc[page_num]
        
        # 1. Verifica se existe o texto indicativo de boleto
        text = page.get_text("text")
        is_boleto = any(term in text.upper() for term in [
            "BOLETO", "CÓDIGO DE BARRAS", "FICHA DE COMPENSAÇÃO", 
            "PAGAMENTO", "VENCIMENTO", "CEDENTE"
        ])
        
        if not is_boleto:
            continue
            
        # 2. Extrai usando padrões específicos de boletos
        boleto_patterns = [
            r"(?:VALOR|DOCUMENTO)[\s:]*R?\$?\s*([\d\.]+,\d{2})",
            r"(?:COBRADO|PAGÁVEL)[\s:]*R?\$?\s*([\d\.]+,\d{2})",
            r"(?:PAGAMENTO|TOTAL)[\s:]*R?\$?\s*([\d\.]+,\d{2})"
        ]
        
        for pattern in boleto_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            all_values.extend(matches)
            
        # 3. Verificar a linha digitável/código de barras para extrair o valor
        barcode_pattern = r"[\d\s]{47,48}"  # Padrão básico de linha digitável
        barcode_matches = re.findall(barcode_pattern, text)
        
        for barcode in barcode_matches:
            # Remover espaços
            barcode = barcode.replace(" ", "")
            
            # Tentar extrair valor do código de barras se for um boleto convencional
            if len(barcode) >= 47:
                # O valor geralmente está em posições específicas
                try:
                    # Posição do valor depende do formato do boleto
                    if barcode[0] == "8":  # Arrecadação (contas, tributos)
                        value_str = barcode[4:15]
                        # Verificar se são dígitos e converter para formato de moeda
                        if value_str.isdigit():
                            value = int(value_str) / 100  # Converter para reais
                            formatted_value = f"{value:.2f}".replace(".", ",")
                            all_values.append(formatted_value)
                    else:  # Boleto bancário convencional
                        value_str = barcode[37:47]
                        if value_str.isdigit():
                            value = int(value_str) / 100
                            formatted_value = f"{value:.2f}".replace(".", ",")
                            all_values.append(formatted_value)
                except:
                    pass
    
    # Remove duplicatas
    unique_values = []
    seen = set()
    for value in all_values:
        if value not in seen:
            unique_values.append(value)
            seen.add(value)
            
    return unique_values if unique_values else None

# Função que extrai os dados de uma fatura da Vivo Móvel
def extrair_dados_vivo_movel(text):
    data = {
        "numero_conta": "",
        "mes_referencia": "",
        "total_a_pagar": "",
        "notas_fiscais": []
    }
    
    conta_match = re.search(r"Nº da Conta:\s*(\d+)", text)
    if conta_match:
        data["numero_conta"] = conta_match.group(1)
    
    mes_ref_match = re.search(r"Mês de referência:\s*(\d{2}/\d{4})", text)
    if mes_ref_match:
        data["mes_referencia"] = mes_ref_match.group(1)
    
    total_pagar_match = re.search(r"Total a Pagar - R\$\s*([\d.,]+)", text)
    if total_pagar_match:
        data["total_a_pagar"] = total_pagar_match.group(1)
    
    nf_matches = re.finditer(
        r"NOTA FISCAL DE SERVIÇOS DE TELECOMUNICAÇÕES.*?"
        r"CNPJ:\s*([\d.-]+/[\d-]+).*?"
        r"TOTAL NOTA FISCAL TELEFONICA BRASIL S.A.\s*([\d.,]+)",
        text, re.DOTALL)
    
    for match in nf_matches:
        cnpj_raw = match.group(1)
        data["notas_fiscais"].append({
            "cnpj": standardize_cnpj(cnpj_raw),
            "total": match.group(2)
        })
    
    return data