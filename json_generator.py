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

def generate_json_input(pdf_text, short_text, is_servico, supplier_code, total_value):
    if not pdf_text:
        return None
    
    item_type = "S" if is_servico else "M"
    formatted_short_text = f"[{item_type},{supplier_code}] {short_text}"
    
    # Converter valor aqui
    formatted_value = format_number(total_value)
    
    json_input = [
        {
            "PREQ_ITEM": "0010",
            "MATERIAL": "ZA040282",  
            "SHORT_TEXT": formatted_short_text, 
            "QUANTITY": "1",  
            "PREQ_PRICE": formatted_value  # Usar valor convertido
        }
    ]
    
    return json.dumps(json_input, indent=4)

# Função que gera o JSON de entrada pra Vivo Móvel, faturas compostas
def generate_json_input_vivo_movel(data, is_servico, supplier_data):
    json_input = []
    preq_item = 10

    #auto_description = f"MesRef{data['mes_referencia']} NumConta{data['numero_conta']}"
    auto_description = "Fatura Vivo Movel"
    
    for nf in data["notas_fiscais"]:
        item_type = "S" if is_servico else "M"
        cnpj = standardize_cnpj(nf['cnpj'])
        supplier_code = supplier_data.get(cnpj)
        
        formatted_short_text = (
            f"[{item_type},{supplier_code}] {auto_description}"
            if supplier_code
            else f"[{item_type},{cnpj}] {auto_description}"
        )
        
        # Converter valor aqui
        formatted_value = format_number(nf["total"])
        
        json_input.append({
            "PREQ_ITEM": f"{preq_item:04}",
            "MATERIAL": "ZA040282",
            "SHORT_TEXT": formatted_short_text,
            "QUANTITY": "1",
            "PREQ_PRICE": formatted_value  # Usar valor convertido
        })
        preq_item += 10
    
    return json.dumps(json_input, indent=4)