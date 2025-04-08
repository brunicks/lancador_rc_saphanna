import os
import json
from tkinter import messagebox

class ConfigManager:
    CONFIG_DIR = "config_files"
    
    @staticmethod
    def load_json_file(filename):
        """Carrega um arquivo JSON da pasta config_files"""
        try:
            filepath = os.path.join(ConfigManager.CONFIG_DIR, filename)
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            messagebox.showerror("Erro", f"Arquivo não encontrado: {filename}")
            return {}
        except json.JSONDecodeError:
            messagebox.showerror("Erro", f"Erro ao decodificar: {filename}")
            return {}
    
    @classmethod
    def load_all_configs(cls):
        """Carrega todas as configurações necessárias"""
        return {
            'parametros': cls.load_json_file('parametros.json'),
            'credenciais': cls.load_json_file('credenciais.json'),
            'centros_contas': cls.load_json_file('centros_contas.json'),
            'fornecedores': cls.load_json_file('fornecedores.json')
        }
    
    @classmethod
    def get_supplier_data(cls):
        """Carrega e processa dados dos fornecedores"""
        return cls.load_json_file('fornecedores.json')