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
            for page in doc:
                page_text = page.get_text("text")
                page_text = " ".join(page_text.splitlines())
                text += page_text + "\n"
        
        if not text.strip():
            raise ValueError("Nenhum texto extraído do PDF.")
        
        total_value = extract_total_value(text)
        if not total_value:
            raise ValueError("Não foi possível encontrar o valor total da fatura.")
        
    except Exception as e:
        text = f"Erro ao ler o PDF: {e}"

    return text, total_value

# Função que extrai o valor total de uma fatura
def extract_total_value(text):
    patterns = [
       # r"R\$\s*([\d\.]+,\d{2})",
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