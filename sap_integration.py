#sap_integration.py
import json
import re
import requests
import os
import uuid
import tkinter as tk
from tkinter import messagebox, ttk
from tkcalendar import DateEntry
from config_manager import ConfigManager
from datetime import datetime

class SAPIntegrationDialog:
    # Classe para a janela de integração com o SAP
    def __init__(self, parent, json_data, log_callback=None):
        # Configuração inicial da janela
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Envio para SAP")
        self.dialog.grab_set()
        
        # Ajustar tamanho e posição
        width = 800
        height = 600
        self.dialog.minsize(width, height)
        
        # Centralizar na tela
        screen_width = self.dialog.winfo_screenwidth()
        screen_height = self.dialog.winfo_screenheight()
        x = (screen_width - width) // 2
        y = (screen_height - height) // 2
        self.dialog.geometry(f"{width}x{height}+{x}+{y}")
        
        # Variáveis de classe
        self.response = None
        self.json_data = json_data
        self.log_callback = log_callback
        
        # Container principal
        self.main_frame = tk.Frame(self.dialog, bg='#f4f4f4')
        self.main_frame.pack(fill='both', expand=True, padx=20, pady=20)
        
        # Carregar configurações
        self.configs = ConfigManager.load_all_configs()
        self.load_configurations()
        
        # Configurar interface
        self.setup_ui()
        
        # Focar janela
        self.dialog.focus_force()

        self.last_payload = None
        self.result = False
    
    # Métodos auxiliares
    def log(self, message, level="info"):
        """Registra mensagens de log"""
        if self.log_callback:
            self.log_callback(message, level)
    
    # Carregamento de configurações
    def load_configurations(self):
        """Carrega todas as configurações necessárias"""
        try:
            self.params = self.configs['parametros']
            self.centros_contas = self.configs['centros_contas']
            self.creds = self.configs['credenciais']  
            self.log("Configurações carregadas com sucesso")
        except Exception as e:
            self.log(f"Erro ao carregar configurações: {str(e)}")
            raise
    
    # Configuração da interface
    def setup_ui(self):
        """Configura a interface do usuário"""
        # Frame de campos
        fields_frame = ttk.LabelFrame(self.main_frame, text="Dados para Envio", padding=10)
        fields_frame.pack(fill='x', padx=10, pady=5)
        
        # Grid configuration
        fields_frame.columnconfigure(1, weight=1)
        
        # Criar lista de valores para o combobox de conta razão com descrições
        contas_razao_values = []
        for codigo in self.centros_contas["contas_razao"]:
            descricao = self.centros_contas.get("contas_razao_descricao", {}).get(codigo, "")
            if descricao:
                contas_razao_values.append(f"{codigo} - {descricao}")
            else:
                contas_razao_values.append(codigo)
        
        # Campos usando grid
        fields = [
            ("Descrição:", ttk.Entry(fields_frame)),
            ("Data Entrega:", DateEntry(fields_frame, width=20, locale='pt_BR', 
                                    date_pattern='dd/mm/yyyy')),
            ("Categoria:", ttk.Combobox(fields_frame, values=["K", "F"], 
                                    state="readonly")),
            ("Centro de Custo:", ttk.Combobox(fields_frame, 
                                            values=self.centros_contas["centros_custo"], 
                                            state="readonly")),
            ("Conta Razão:", ttk.Combobox(fields_frame, 
                                        values=contas_razao_values,
                                        state="readonly"))
        ]
        
        # Criar campos com grid
        for i, (label_text, widget) in enumerate(fields):
            label = ttk.Label(fields_frame, text=label_text)
            label.grid(row=i, column=0, sticky='e', padx=5, pady=5)
            
            if isinstance(widget, ttk.Entry):
                widget.configure(width=50)
            elif isinstance(widget, ttk.Combobox):
                widget.configure(width=48)
            
            widget.grid(row=i, column=1, sticky='w', padx=5, pady=5)
            
            # Guardar referências
            if i == 0: self.text_line = widget
            elif i == 1: self.deliv_date = widget
            elif i == 2: self.acctasscat = widget
            elif i == 3: self.cost_center = widget
            elif i == 4: self.conta_razao = widget

        # Frame de botões (mesmo estilo da janela principal)
        buttons_frame = ttk.Frame(self.main_frame)
        buttons_frame.pack(fill='x', padx=10, pady=5)
        
        # Configurar grid para centralizar botões
        buttons_frame.columnconfigure(1, weight=1)
        
        # Botões usando ttk
        self.btn_preview = ttk.Button(
            buttons_frame,
            text="Atualizar Preview",
            command=self.update_preview,
            width=20
        )
        self.btn_preview.pack(side='left', padx=5)
        
        self.btn_send = ttk.Button(
            buttons_frame,
            text="Enviar",
            command=self.send_to_sap,
            width=20
        )
        self.btn_send.pack(side='left', padx=5)
        
        self.btn_cancel = ttk.Button(
            buttons_frame,
            text="Cancelar",
            command=self.dialog.destroy,
            width=20
        )
        self.btn_cancel.pack(side='left', padx=5)
        
        # Preview Frame
        preview_frame = ttk.LabelFrame(self.main_frame, text="Preview do JSON", padding=10)
        preview_frame.pack(fill='both', expand=True, padx=10, pady=5)
        
        # Text widget com scrollbars
        self.setup_preview_area(preview_frame)
        
        # Valor inicial categoria
        self.acctasscat.set("K")
        
        # Preview inicial
        self.update_preview()
    
    # Preview do JSON
    def setup_preview_area(self, parent):
        """Configura área de preview do JSON"""
        # Frame para o texto com scrollbars
        text_frame = ttk.Frame(parent)
        text_frame.pack(fill=tk.BOTH, expand=True)
        text_frame.columnconfigure(0, weight=1)
        text_frame.rowconfigure(0, weight=1)
        
        # Scrollbars
        y_scroll = ttk.Scrollbar(text_frame)
        x_scroll = ttk.Scrollbar(text_frame, orient="horizontal")
        
        # Text widget
        self.text_json = tk.Text(text_frame, wrap=tk.NONE,
                               yscrollcommand=y_scroll.set,
                               xscrollcommand=x_scroll.set)
        
        # Layout
        self.text_json.grid(row=0, column=0, sticky="nsew")
        y_scroll.grid(row=0, column=1, sticky="ns")
        x_scroll.grid(row=1, column=0, sticky="ew")
        
        # Configurar scrollbars
        y_scroll.config(command=self.text_json.yview)
        x_scroll.config(command=self.text_json.xview)
    
    # Métodos principais
    def update_preview(self):
        """Atualiza o preview do JSON"""
        try:
            payload = self.build_payload()
            self.text_json.delete("1.0", tk.END)
            self.text_json.insert("1.0", json.dumps(payload, indent=4, ensure_ascii=False))
            self.log("Preview atualizado com sucesso")
        except Exception as e:
            self.log(f"Erro ao atualizar preview: {str(e)}")

    # Construção do payload
    def build_payload(self):
        """Constrói o payload final para envio ao SAP"""
        try:
            date_obj = datetime.strptime(self.deliv_date.get(), '%d/%m/%Y')
            meses_pt = {
                'January': 'Janeiro',
                'February': 'Fevereiro',
                'March': 'Março',
                'April': 'Abril',
                'May': 'Maio',
                'June': 'Junho',
                'July': 'Julho',
                'August': 'Agosto',
                'September': 'Setembro',
                'October': 'Outubro',
                'November': 'Novembro',
                'December': 'Dezembro'
            }
            
            formatted_date_en = date_obj.strftime('%d %B %Y')
            mes = formatted_date_en.split()[1]
            formatted_date = formatted_date_en.replace(mes, meses_pt[mes])
            
            # Extrair apenas o código da conta razão (antes do " - ")
            conta_razao_full = self.conta_razao.get()
            conta_razao = conta_razao_full.split(" - ")[0] if " - " in conta_razao_full else conta_razao_full
            
            payload = {
                "ZSBR_MM_AZU_WEBSHOP_PREQ": {
                    "I_WEBSHOP": {
                        "TOPDESK_KEY": str(uuid.uuid4()),
                        "CR_NUMBER": f"CR-{datetime.now().strftime('%y%m')}-{str(uuid.uuid4())[:5]}",
                        "REQUESTER": {
                            "USER": str(uuid.uuid4()),
                            "NOME": os.getenv('USERNAME').title(),
                            "EMAIL": "fernandesj@Sysmex.com"
                        },
                        "TEXT_LINE": self.text_line.get(),
                        "DELIV_DATE": formatted_date,
                        "ACCTASSCAT": self.acctasscat.get(),
                        "COST_CENTER": self.cost_center.get(),
                        "ORDER": "",
                        "PLANT": "2201",
                        "CONTA_RAZAO": conta_razao,
                        "ITEMS": self.json_data
                    }
                }
            }
            
            return payload
                
        except Exception as e:
            self.log(f"Erro ao construir payload: {e}", "error")
            raise
    
    # Validação e envio
    def validate_fields(self):
        """Valida se todos os campos obrigatórios foram preenchidos"""
        fields = {
            "Descrição": self.text_line.get(),
            "Data de Entrega": self.deliv_date.get(),
            "Categoria": self.acctasscat.get(),
            "Centro de Custo": self.cost_center.get(),
            "Conta Razão": self.conta_razao.get()
        }
        
        empty_fields = [k for k, v in fields.items() if not v]
        if empty_fields:
            messagebox.showerror("Erro", 
                            f"Campos obrigatórios não preenchidos:\n{', '.join(empty_fields)}")
            return False
        return True
    
    # Envio para o SAP
    def send_to_sap(self):
            if not self.validate_fields():
                return
            
            try:
                payload = self.build_payload()
                self.last_payload = payload
                self.log("Enviando requisição...", "info")
                
                response = requests.post(
                    self.params["URL_API"],
                    json=payload,
                    auth=(self.creds['usuario'], self.creds['senha']),
                    headers={'Content-Type': 'application/json'},
                    timeout=30
                )
                self.response = response
                
                if response.status_code == 200:
                    self.result = True
                    messagebox.showinfo("Sucesso", "Envio realizado com sucesso!")
                    self.dialog.destroy()
                else:
                    messagebox.showerror("Erro", f"Erro no envio: {response.text}")
                    
            except Exception as e:
                self.response = None
                error_msg = f"Erro durante o envio: {str(e)}"
                self.log(error_msg, "error")
                messagebox.showerror("Erro", error_msg)

    # Centralização do diálogo
    def center_dialog(self, parent):
        """Centraliza o diálogo em relação à janela pai"""
        self.dialog.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() - self.dialog.winfo_width()) // 2
        y = parent.winfo_y() + (parent.winfo_height() - self.dialog.winfo_height()) // 2
        self.dialog.geometry(f"+{x}+{y}")
