#json_generator.py
import json
from pdf_reader import standardize_cnpj

def format_number(value):
    """Converte números do formato brasileiro para o internacional"""
    if isinstance(value, str):
        # Remove pontos de milhar e substitui vírgula por ponto
        value = value.replace('.', '')  # Remove separador de milhar
        value = value.replace(',', '.')  # Converte decimal para ponto
    return value

def generate_json_input(pdf_text, short_text, is_servico, supplier_code, total_value, material_code="ZA040282"):
    if not pdf_text:
        return None
    
    item_type = "S" if is_servico else "M"
    formatted_short_text = f"[{item_type},{supplier_code}] {short_text}"
    
    # Converter valor aqui
    formatted_value = format_number(total_value)
    
    json_input = [
        {
            "PREQ_ITEM": "0010",
            "MATERIAL": material_code,  
            "SHORT_TEXT": formatted_short_text, 
            "QUANTITY": "1",  
            "PREQ_PRICE": formatted_value  # Usar valor convertido
        }
    ]
    
    return json.dumps(json_input, indent=4)

# Função que gera o JSON de entrada pra Vivo Móvel, faturas compostas
def generate_json_input_vivo_movel(data, is_servico, supplier_data, material_code="ZA040282"):
    json_input = []
    preq_item = 10

    #auto_description = f"MesRef{data['mes_referencia']} NumConta{data['numero_conta']}"
    auto_description = "Fatura Vivo Movel"
    
    # Mapeamento fixo de CNPJs da Vivo para códigos SAP
    vivo_mapping = {
        "02558157000162": "1000029760",
        "02558157000243": "1000029762",
        "02558157000324": "1000029764",
        "02558157000839": "1000029766",
        "02558157000910": "1000029794",
        "02558157001134": "1000029796",
        "02558157001304": "1000029798",
        "02558157001487": "1000029800",
        "02558157001720": "1000029802",
        "02558157002297": "1000029804",
        "02558157002459": "1000029806",
        "02558157013574": "1000029808",
        "02558157015941": "1000029810",
        "02558157018703": "1000032155",
        "02558157051824": "1000029812",
        "02558157075685": "1000029814"
    }
    
    for nf in data["notas_fiscais"]:
        item_type = "S" if is_servico else "M"
        cnpj = standardize_cnpj(nf['cnpj'])
        
        # Tentar obter o código do supplier_data primeiro
        supplier_code = supplier_data.get(cnpj)
        
        # Se não encontrou, tentar do mapeamento fixo
        if not supplier_code:
            supplier_code = vivo_mapping.get(cnpj)
        
        formatted_short_text = (
            f"[{item_type},{supplier_code}] {auto_description}"
            if supplier_code
            else f"[{item_type},{cnpj}] {auto_description}"
        )
        
        # Converter valor aqui
        formatted_value = format_number(nf["total"])
        
        json_input.append({
            "PREQ_ITEM": f"{preq_item:04}",
            "MATERIAL": material_code,
            "SHORT_TEXT": formatted_short_text,
            "QUANTITY": "1",
            "PREQ_PRICE": formatted_value  # Usar valor convertido
        })
        preq_item += 10
    
    return json.dumps(json_input, indent=4)