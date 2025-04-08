from datetime import datetime
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import json
import fitz
from pdf_reader import extract_text_from_pdf, extrair_dados_vivo_movel
from json_generator import generate_json_input, generate_json_input_vivo_movel
from sap_integration import SAPIntegrationDialog
from config_manager import ConfigManager

# Classe para a janela de seleção de valores caso encontre mais de um valor no PDF
class ValueSelectorDialog:
    def __init__(self, parent, values):
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Selecionar Valor")
        self.dialog.grab_set()
        # Configuração da janela
        self.dialog.geometry("300x400")
        self.dialog.resizable(False, False)
        # Valor selecionado
        self.selected_value = None
        self.values = values
        
        # Container principal
        container = ttk.Frame(self.dialog)
        container.pack(fill='both', expand=True, padx=10, pady=5)
        
        # Label com contagem de valores
        ttk.Label(container, text=f"Selecione o valor correto ({len(values)} valores encontrados):").pack(pady=5)
        
        # Frame para a lista
        list_frame = ttk.Frame(container)
        list_frame.pack(fill='both', expand=True, pady=5)
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(list_frame)
        scrollbar.pack(side='right', fill='y')
        
        # Listbox virtualizada
        self.listbox = tk.Listbox(
            list_frame,
            yscrollcommand=scrollbar.set,
            selectmode='browse',  # Modo mais leve que 'single'
            exportselection=False,
            height=15,
            activestyle='none',  # Remove highlighting
            borderwidth=1,
            highlightthickness=0,
            relief='solid'
        )
        self.listbox.pack(side='left', fill='both', expand=True)
        scrollbar.config(command=self.listbox.yview)
        
        # Otimização de eventos
        self.listbox.bind('<Double-Button-1>', self.on_double_click)
        self.listbox.bind('<<ListboxSelect>>', lambda e: None)  # Desativa callback padrão
        
        # Botão de seleção
        ttk.Button(
            container,
            text="Selecionar",
            command=self.on_select,
            style='Accent.TButton'  # Estilo destacado
        ).pack(pady=10)
        
        # Inserção em lotes
        self.batch_insert_values()
        
        # Posicionamento
        self.center_window(parent)
        self.dialog.focus_force()
        self.dialog.wait_window()
    
    # Insere valores em lotes para melhor performance
    def batch_insert_values(self, batch_size=100):
        self.listbox.delete(0, tk.END)
        for i in range(0, len(self.values), batch_size):
            batch = self.values[i:i + batch_size]
            self.listbox.insert(tk.END, *[f"R$ {v}" for v in batch])
            self.dialog.update_idletasks()  # Atualiza UI periodicamente
    
    # Centraliza a janela em relação ao pai
    def center_window(self, parent):
        parent_x = parent.winfo_x()
        parent_y = parent.winfo_y()
        parent_width = parent.winfo_width()
        parent_height = parent.winfo_height()
        x = parent_x + (parent_width - 300) // 2
        y = parent_y + (parent_height - 400) // 2
        self.dialog.geometry(f"+{x}+{y}")
    
    # Handlers otimizados para double click 
    def on_double_click(self, event):
        if self.listbox.curselection():
            self.on_select()
    
    # Handler para otimizado seleção
    def on_select(self):
        if sel := self.listbox.curselection():
            self.selected_value = self.listbox.get(sel[0]).replace("R$ ", "")
            self.dialog.destroy()

# Carrega os dados dos fornecedores do arquivo fornecedores.json
def load_supplier_data():
    return ConfigManager.get_supplier_data()

# Classe principal da aplicação
class PDFtoJSONApp:
    
    # Inicialização da aplicação
    def __init__(self, root):
        
        # Inicialização de variáveis primeiro
        self.pdf_text = ""
        self.total_value = ""
        self.current_pdf_path = ""
        self.accumulated_json = []
        
        # Configuração da janela principal
        self.root = root
        self.root.title("Um dia da bom")
        self.root.minsize(600, 550)
        self.root.geometry("650x600") 
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(4, weight=1)
        
        # Estilo da interface
        style = ttk.Style()
        style.theme_use("xpnative")
        self.root.configure(bg='#f4f4f4')
        
        # Carrega os dados dos fornecedores
        self.supplier_data = load_supplier_data()
        
        # 1. Criar notebook e frames primeiro
        self.notebook = ttk.Notebook(root)
        self.json_frame = ttk.Frame(self.notebook, padding=(5, 5))
        self.log_frame = ttk.Frame(self.notebook, padding=(5, 5))
        self.history_frame = ttk.Frame(self.notebook, padding=(5, 5))
        
        # Configurar grid weights dos frames
        for frame in (self.json_frame, self.log_frame, self.history_frame):
            frame.columnconfigure(0, weight=1)
            frame.rowconfigure(0, weight=1)
        
        # Adicionar abas ao notebook
        self.notebook.add(self.json_frame, text="JSON Output")
        self.notebook.add(self.log_frame, text="Log")
        self.notebook.add(self.history_frame, text="Histórico")
        
        # 2. Configurar widgets do histórico
        history_y_scroll = ttk.Scrollbar(self.history_frame, orient="vertical")
        history_x_scroll = ttk.Scrollbar(self.history_frame, orient="horizontal")
        self.text_history = tk.Text(
            self.history_frame,
            yscrollcommand=history_y_scroll.set,
            xscrollcommand=history_x_scroll.set,
            wrap=tk.NONE,
            state=tk.DISABLED  # Começa em modo somente leitura
        )
        
        # Layout do histórico
        self.text_history.grid(row=0, column=0, sticky="nsew")
        history_y_scroll.grid(row=0, column=1, sticky="ns")
        history_x_scroll.grid(row=1, column=0, sticky="ew")
        history_y_scroll.config(command=self.text_history.yview)
        history_x_scroll.config(command=self.text_history.xview)
        
        # 3. Configurar widgets do JSON
        json_y_scroll = ttk.Scrollbar(self.json_frame, orient="vertical")
        json_x_scroll = ttk.Scrollbar(self.json_frame, orient="horizontal")
        self.text_json_input = tk.Text(
            self.json_frame, 
            yscrollcommand=json_y_scroll.set,
            xscrollcommand=json_x_scroll.set,
            wrap=tk.NONE
        )
        
        # Layout do JSON
        self.text_json_input.grid(row=0, column=0, sticky="nsew")
        json_y_scroll.grid(row=0, column=1, sticky="ns")
        json_x_scroll.grid(row=1, column=0, sticky="ew")
        json_y_scroll.config(command=self.text_json_input.yview)
        json_x_scroll.config(command=self.text_json_input.xview)
        
        # 4. Configurar widgets do log
        log_y_scroll = ttk.Scrollbar(self.log_frame, orient="vertical")
        self.text_log = tk.Text(
            self.log_frame,
            yscrollcommand=log_y_scroll.set,
            wrap=tk.WORD,
            bg="#f5f5f5",
            state=tk.NORMAL
        )
        
        # Layout do log
        self.text_log.grid(row=0, column=0, sticky="nsew")
        log_y_scroll.grid(row=0, column=1, sticky="ns")
        log_y_scroll.config(command=self.text_log.yview)
        
        # Configurar tags para diferentes níveis de log
        self.text_log.tag_configure("info", foreground="black")
        self.text_log.tag_configure("success", foreground="green")
        self.text_log.tag_configure("error", foreground="red")
        self.text_log.tag_configure("warning", foreground="orange")
        
        # 5. Frame para exibição do PDF carregado
        self.pdf_info_frame = ttk.LabelFrame(root, text="PDF Atual", padding=(10, 5))
        self.pdf_info_frame.grid(row=0, column=0, sticky="nsew", padx=10, pady=5)
        self.pdf_info_frame.columnconfigure(0, weight=1)
        self.current_pdf_label = ttk.Label(self.pdf_info_frame, text="Nenhum PDF carregado")
        self.current_pdf_label.grid(row=0, column=0, sticky="ew")
        
        # 6. Frame de botões do PDF
        self.button_frame = ttk.Frame(root)
        self.button_frame.grid(row=1, column=0, sticky="ew", pady=5, padx=10)
        self.button_frame.columnconfigure(1, weight=1)
        self.btn_load_pdf = ttk.Button(self.button_frame, text="Carregar PDF", command=self.load_pdf)
        self.btn_load_pdf.grid(row=0, column=0, padx=5)
        self.btn_clear_pdf = ttk.Button(self.button_frame, text="Limpar PDF Atual", command=self.clear_current_pdf)
        self.btn_clear_pdf.grid(row=0, column=2, padx=5)
        
        # 7. Frame de opções
        options_frame = ttk.Frame(root)
        options_frame.grid(row=2, column=0, sticky="ew", padx=10, pady=5)
        options_frame.columnconfigure(1, weight=1)
        self.is_servico_var = tk.BooleanVar()
        self.checkbox_servico = ttk.Checkbutton(options_frame, text="É serviço?", variable=self.is_servico_var)
        self.checkbox_servico.grid(row=0, column=0, sticky="w")
        self.is_vivo_movel_var = tk.BooleanVar()
        self.checkbox_vivo_movel = ttk.Checkbutton(options_frame, text="Vivo Móvel", variable=self.is_vivo_movel_var, command=self.toggle_supplier_selection)
        self.checkbox_vivo_movel.grid(row=0, column=1, sticky="w")
        
        # 8. Frame de entrada
        input_frame = ttk.Frame(root)
        input_frame.grid(row=3, column=0, sticky="ew", padx=10, pady=5)
        input_frame.columnconfigure(1, weight=1)
        
        self.label_short_text = ttk.Label(input_frame, text="Descrição:")
        self.label_short_text.grid(row=0, column=0, sticky="w", pady=2)
        self.entry_short_text = ttk.Entry(input_frame)
        self.entry_short_text.grid(row=0, column=1, sticky="ew", padx=5)
        
        self.label_supplier_code = ttk.Label(input_frame, text="Fornecedor:")
        self.label_supplier_code.grid(row=1, column=0, sticky="w", pady=2)
        self.supplier_code_var = tk.StringVar()
        self.supplier_code_dropdown = ttk.Combobox(input_frame, textvariable=self.supplier_code_var, values=self.get_supplier_options(), state="readonly")
        self.supplier_code_dropdown.grid(row=1, column=1, sticky="ew", padx=5)
        self.supplier_code_var.set("Selecione o fornecedor")
        
        # 9. Posicionar notebook
        self.notebook.grid(row=4, column=0, sticky="nsew", padx=10, pady=5)
        
        # 10. Frame de botões do JSON
        self.json_button_frame = ttk.Frame(root)
        self.json_button_frame.grid(row=5, column=0, sticky="ew", padx=10, pady=5)
        self.json_button_frame.columnconfigure(1, weight=1)
        self.btn_generate_json = ttk.Button(self.json_button_frame, text="Adicionar ao JSON", command=self.generate_json)
        self.btn_generate_json.grid(row=0, column=0, padx=5)
        self.btn_clear_json = ttk.Button(self.json_button_frame, text="Limpar JSON", command=self.clear_json)
        self.btn_clear_json.grid(row=0, column=2, padx=5)
        
        # 11. Frame de botão SAP
        self.sap_button_frame = ttk.Frame(root)
        self.sap_button_frame.grid(row=6, column=0, sticky="ew", padx=10, pady=5)
        self.sap_button_frame.columnconfigure(0, weight=1)
        self.btn_enviar_sap = ttk.Button(self.sap_button_frame, text="Enviar para SAP", command=self.enviar_para_sap)
        self.btn_enviar_sap.grid(row=0, column=0, padx=5)
        
        # 12. Frame de resposta SAP
        self.sap_response_frame = ttk.LabelFrame(root, text="Resposta do SAP", padding=(10, 5))
        self.sap_response_frame.grid(row=7, column=0, sticky="ew", padx=10, pady=5)
        self.sap_response_frame.columnconfigure(0, weight=1)
        self.sap_response_label = ttk.Label(self.sap_response_frame, text="Nenhuma requisição enviada ainda")
        self.sap_response_label.grid(row=0, column=0, sticky="ew")
        
        # Log inicial
        self.add_log("Aplicação iniciada", "info")
    
    # Função para atualizar a resposta do SAP
    def update_sap_response(self, response):
        """Exibe apenas a resposta da API no label do SAP."""
        try:
            status = response.status_code if hasattr(response, 'status_code') else "N/A"
            text = response.text if hasattr(response, 'text') else str(response)
            msg = f"Status: {status}\n{text}"
            
            self.sap_response_label.config(text=msg) 

        except Exception as e:
            self.add_log(f"Erro ao atualizar resposta SAP: {e}", "error")

    # Função para adicionar entrada ao histórico
    def add_to_history(self, payload, response):
        """Registra o payload enviado e a resposta do SAP no histórico."""
        try:
            self.text_history.config(state=tk.NORMAL)  
            
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            status_code = response.status_code if hasattr(response, 'status_code') else "N/A"
            response_text = response.text if hasattr(response, 'text') else str(response)
            
            entry = f"""
    {'='*80}
    DATA/HORA: {timestamp}
    STATUS: {status_code}

    PAYLOAD ENVIADO:
    {json.dumps(payload, indent=2, ensure_ascii=False)}

    RESPOSTA RECEBIDA:
    {response_text}
    {'='*80}
    """

            self.text_history.insert("1.0", entry)
            self.text_history.see("1.0")  

        finally:
            self.text_history.config(state=tk.DISABLED)  

    # Função para adicionar entradas ao log
    def add_log(self, message, level="info"):
        """Adiciona apenas mensagens e a resposta do SAP ao log, sem incluir payloads grandes."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.text_log.insert(tk.END, f"[{timestamp}] ", "info")
        self.text_log.insert(tk.END, f"{message}\n", level)
        self.text_log.see(tk.END)  
        self.root.update_idletasks() 

    # Retorna as opções de fornecedores para o dropdown 
    def get_supplier_options(self):
        return [f"{cnpj} - {code}" for cnpj, code in self.supplier_data.items()]
    
    # Mostra ou esconde os campos de seleção de fornecedor dependendo da seleção do checkbox da Vivo Móvel
    def toggle_supplier_selection(self):
        if self.is_vivo_movel_var.get():
            self.label_supplier_code.grid_remove()
            self.supplier_code_dropdown.grid_remove()
            self.label_short_text.grid_remove()
            self.entry_short_text.grid_remove()
            self.add_log("Modo Vivo Móvel ativado", "info")
        else:
            self.label_supplier_code.grid()
            self.supplier_code_dropdown.grid()
            self.label_short_text.grid()
            self.entry_short_text.grid()
            self.add_log("Modo Vivo Móvel desativado", "info")
    
    # Limpa o PDF atual
    def clear_current_pdf(self):
        self.pdf_text = ""
        self.total_value = ""
        self.current_pdf_path = ""
        self.current_pdf_label.config(text="Nenhum PDF carregado")
        self.add_log("PDF atual limpo", "info")
    
    # Limpa o JSON acumulado
    def clear_json(self):
        """Limpa o JSON acumulado"""
        if self.accumulated_json:
            if messagebox.askyesno("Confirmar", "Deseja realmente limpar o JSON?"):
                self.accumulated_json = []
                self.text_json_input.delete("1.0", tk.END)
                self.add_log("JSON limpo", "info")
        else:
            self.add_log("Nenhum JSON para limpar", "warning")
    
    # Carrega um PDF
    def load_pdf(self):
        filepath = filedialog.askopenfilename(filetypes=[("PDF Files", "*.pdf")])
        if not filepath:
            return
        try:
            filename = filepath.split("/")[-1]
            self.add_log(f"Carregando PDF: {filename}", "info")

            # Verificação para Vivo Móvel pelo nome do arquivo
            if "VIVO" in filename.upper() and "MOVEL" in filename.upper():
                # Para Vivo Móvel, apenas extrair o texto sem processamento de valores
                doc = fitz.open(filepath)
                self.pdf_text = ""
                for page in doc:
                    page_text = page.get_text("text")
                    page_text = " ".join(page_text.splitlines())
                    self.pdf_text += page_text + "\n"
                doc.close()

                self.is_vivo_movel_var.set(True)
                self.toggle_supplier_selection()
                self.current_pdf_path = filepath
                self.current_pdf_label.config(text=f"PDF Atual: {filename}\nFatura Vivo Móvel Detectada")
                self.add_log("Fatura Vivo Móvel detectada e carregada com sucesso", "success")
                messagebox.showinfo("Sucesso", "Fatura Vivo Móvel Detectada e Carregada!")
                return

            # Para outros tipos de PDF, mantém o processamento normal
            self.pdf_text, values = extract_text_from_pdf(filepath)
            if values and len(values) > 1:
                self.add_log(f"Múltiplos valores encontrados: {len(values)}", "warning")
                dialog = ValueSelectorDialog(self.root, values)
                if dialog.selected_value:
                    self.total_value = dialog.selected_value
                    self.add_log(f"Valor selecionado: R$ {self.total_value}", "info")
                else:
                    self.total_value = values[0]
                    self.add_log(f"Nenhum valor selecionado. Usando o primeiro: R$ {self.total_value}", "warning")
            elif values:
                self.total_value = values[0]
                self.add_log(f"Valor encontrado: R$ {self.total_value}", "info")
            else:
                self.add_log("Valor total não encontrado no PDF", "error")
                messagebox.showwarning("Aviso", "Valor total não encontrado no PDF.")
                return

            self.current_pdf_path = filepath
            self.current_pdf_label.config(text=f"PDF Atual: {filename}\nValor total: R$ {self.total_value}")
            self.add_log(f"PDF carregado com sucesso: {filename}", "success")
            messagebox.showinfo("Sucesso", f"PDF carregado com sucesso! Valor total: {self.total_value}")

        except Exception as e:
            self.add_log(f"Erro ao ler o PDF: {e}", "error")
            messagebox.showerror("Erro", f"Erro ao ler o PDF: {e}")

    # Gera o JSON baseado no PDF carregado
    def generate_json(self):
        if not self.pdf_text:
            self.add_log("Tentativa de gerar JSON sem PDF carregado", "error")
            messagebox.showerror("Erro", "Nenhum PDF carregado!")
            return
        is_servico = self.is_servico_var.get()
        is_vivo_movel = self.is_vivo_movel_var.get()
        
        try:
            # Verifica se o fornecedor foi selecionado corretamente
            if not is_vivo_movel and self.supplier_code_var.get() == "Selecione o fornecedor":
                self.add_log("Tentativa de gerar JSON sem selecionar fornecedor", "error")
                messagebox.showerror("Erro", "Selecione um fornecedor válido!")
                return
            
            # Calcular próximo PREQ_ITEM baseado no JSON acumulado
            next_preq_item = 10
            if self.accumulated_json:
                last_preq_item = int(self.accumulated_json[-1]["PREQ_ITEM"])
                next_preq_item = last_preq_item + 10
            
            self.add_log(f"Gerando JSON, próximo PREQ_ITEM: {next_preq_item}", "info")
            
            # Extrair dados da fatura da Vivo Móvel
            if is_vivo_movel:
                self.add_log("Processando fatura Vivo Móvel", "info")
                data = extrair_dados_vivo_movel(self.pdf_text)
                if not data["notas_fiscais"]:
                    self.add_log("Nenhuma nota fiscal encontrada na fatura Vivo Móvel", "error")
                    messagebox.showerror("Erro", "Nenhuma nota fiscal encontrada na fatura.")
                    return
                
                # Gerar JSON base
                self.add_log(f"Notas fiscais encontradas: {len(data['notas_fiscais'])}", "info")
                new_json = json.loads(generate_json_input_vivo_movel(data, is_servico, self.supplier_data))
                
                # Atualizar PREQ_ITEM para cada item
                for item in new_json:
                    item["PREQ_ITEM"] = f"{next_preq_item:04}"
                    next_preq_item += 10
                
                self.accumulated_json.extend(new_json)
                self.add_log(f"Adicionados {len(new_json)} itens ao JSON", "success")
            else:
                short_text = self.entry_short_text.get()
                if not short_text:
                    self.add_log("Tentativa de gerar JSON sem descrição", "error")
                    messagebox.showerror("Erro", "Digite uma descrição!")
                    return
                
                supplier_code = self.supplier_code_var.get().split(" - ")[1]
                self.add_log(f"Processando PDF com fornecedor: {supplier_code}", "info")
                
                # Gerar JSON base
                new_json = json.loads(generate_json_input(self.pdf_text, short_text, is_servico, supplier_code, self.total_value))
                
                # Atualizar PREQ_ITEM
                for item in new_json:
                    item["PREQ_ITEM"] = f"{next_preq_item:04}"
                    next_preq_item += 10
                
                self.accumulated_json.extend(new_json)
                self.add_log(f"Adicionados {len(new_json)} itens ao JSON", "success")
            
            # Atualizar display com JSON acumulado
            self.text_json_input.delete("1.0", tk.END)
            self.text_json_input.insert(tk.END, json.dumps(self.accumulated_json, indent=4))
            
            # Limpar PDF atual após adicionar ao JSON
            self.clear_current_pdf()
            
        except Exception as e:
            self.add_log(f"Erro ao gerar o JSON: {e}", "error")
            messagebox.showerror("Erro", f"Erro ao gerar o JSON: {e}")

    # Envia o JSON acumulado para o SAP
    def enviar_para_sap(self):
        """Envia o JSON acumulado para o SAP"""
        if not self.accumulated_json:
            self.add_log("Tentativa de enviar ao SAP sem JSON", "error")
            messagebox.showerror("Erro", "Nenhum JSON para enviar!")
            return
                
        try:
            dialog = SAPIntegrationDialog(
                parent=self.root, 
                json_data=self.accumulated_json,
                log_callback=self.add_log
            )
            
            # Esperar o diálogo fechar
            self.root.wait_window(dialog.dialog)
            
            # Processar resultado após o diálogo fechar
            if dialog.response:
                # Atualizar histórico
                self.add_to_history(dialog.last_payload, dialog.response)
                
                # Atualizar label de resposta
                self.update_sap_response(dialog.response)
                
                # Se sucesso, limpar JSON
                if dialog.result:
                    self.accumulated_json = []
                    self.text_json_input.delete("1.0", tk.END)
                    self.add_log("JSON limpo após envio bem-sucedido", "success")
                
                # Mudar para aba de histórico
                self.notebook.select(2)
                        
        except Exception as e:
            self.add_log(f"Erro ao enviar para SAP: {e}", "error")
            messagebox.showerror("Erro", f"Erro ao enviar para SAP: {e}")

if __name__ == "__main__":
    root = tk.Tk()
    app = PDFtoJSONApp(root)
    root.mainloop()