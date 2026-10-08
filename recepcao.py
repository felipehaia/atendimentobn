import customtkinter as ctk
import socket
import threading
import json
import os
from tkinter import messagebox, simpledialog
from pathlib import Path

def pasta_dados():
    caminho = Path(os.environ.get("LOCALAPPDATA", Path.home())) / "Alerta Atendimento"
    caminho.mkdir(parents=True, exist_ok=True)
    return caminho

ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")

CONFIG_FILE = pasta_dados() / "config_recepcao.json"

class PainelRecepcao(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Painel de Chamadas e Atendimento - Recepção")
        self.geometry("920x600")
        self.resizable(False, False)

        self.socket_cliente = None
        self.cadastrados = []
        self.locais = []
        self.onlines = []
        self.chamados = {}  # {id_chamado: {"card": frame, "lbl_status": label, "lbl_motivo": label, "destino": str}}

        self.config_local = self.carregar_config_local()
        self.criar_tela_login()

    def carregar_config_local(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                pass
        return {"ultimo_ip": "172.31.23.174"}

    def salvar_config_local(self, ip):
        try:
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump({"ultimo_ip": ip}, f, ensure_ascii=False, indent=4)
        except Exception as e:
            print(f"[ERRO CONFIG] {e}")

    def criar_tela_login(self):
        if hasattr(self, 'frame_main') and self.frame_main:
            self.frame_main.pack_forget()

        self.frame_login = ctk.CTkFrame(self)
        self.frame_login.pack(padx=20, pady=20, fill="both", expand=True)

        ctk.CTkLabel(self.frame_login, text="Acesso ao Painel da Recepção", font=("Arial", 18, "bold")).pack(pady=30)

        ctk.CTkLabel(self.frame_login, text="IP do Servidor:").pack(anchor="w", padx=40)
        self.ent_ip = ctk.CTkEntry(self.frame_login)
        self.ent_ip.insert(0, self.config_local.get("ultimo_ip", "172.31.23.174"))
        self.ent_ip.pack(fill="x", padx=40, pady=(0, 20))

        btn_conectar = ctk.CTkButton(self.frame_login, text="Conectar ao Servidor", command=self.conectar)
        btn_conectar.pack(pady=10)

    def criar_tela_principal(self):
        if hasattr(self, 'frame_login') and self.frame_login:
            self.frame_login.pack_forget()

        self.frame_main = ctk.CTkFrame(self)
        self.frame_main.pack(padx=15, pady=15, fill="both", expand=True)

        self.frame_main.columnconfigure(0, weight=1)
        self.frame_main.columnconfigure(1, weight=2)
        self.frame_main.rowconfigure(0, weight=1)

        # ESQUERDA: Form Disparo
        frame_esq = ctk.CTkFrame(self.frame_main)
        frame_esq.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")

        ctk.CTkLabel(frame_esq, text="Novo Chamado", font=("Arial", 16, "bold")).pack(pady=(15, 10))

        ctk.CTkLabel(frame_esq, text="Funcionário:").pack(anchor="w", padx=10)
        self.combo_destinatarios = ctk.CTkOptionMenu(frame_esq, values=["Carregando..."])
        self.combo_destinatarios.pack(fill="x", padx=10, pady=(0, 10))

        ctk.CTkLabel(frame_esq, text="Local de Atendimento:").pack(anchor="w", padx=10)
        self.combo_locais = ctk.CTkOptionMenu(frame_esq, values=["Carregando..."])
        self.combo_locais.pack(fill="x", padx=10, pady=(0, 10))

        ctk.CTkLabel(frame_esq, text="Visitante:").pack(anchor="w", padx=10)
        self.ent_visitante = ctk.CTkEntry(frame_esq, placeholder_text="Ex: João da Silva")
        self.ent_visitante.pack(fill="x", padx=10, pady=(0, 10))

        ctk.CTkLabel(frame_esq, text="Assunto:").pack(anchor="w", padx=10)
        self.ent_assunto = ctk.CTkEntry(frame_esq, placeholder_text="Ex: Reunião / Assinatura")
        self.ent_assunto.pack(fill="x", padx=10, pady=(0, 15))

        btn_chamar = ctk.CTkButton(frame_esq, text="🔔 Enviar Notificação", command=self.enviar_alerta, fg_color="firebrick", hover_color="darkred", height=38)
        btn_chamar.pack(fill="x", padx=10, pady=(0, 15))

        btn_gestao = ctk.CTkButton(frame_esq, text="⚙️ Configurações e Cadastros", command=self.abrir_janela_gestao, fg_color="gray30", hover_color="gray20")
        btn_gestao.pack(fill="x", padx=10)

        # DIREITA: Acompanhamento
        frame_dir = ctk.CTkFrame(self.frame_main)
        frame_dir.grid(row=0, column=1, padx=10, pady=10, sticky="nsew")

        ctk.CTkLabel(frame_dir, text="Acompanhamento em Tempo Real", font=("Arial", 16, "bold")).pack(pady=(15, 10))

        self.scroll_chamados = ctk.CTkScrollableFrame(frame_dir)
        self.scroll_chamados.pack(fill="both", expand=True, padx=10, pady=10)

    def conectar(self):
        ip = self.ent_ip.get().strip()
        if not ip:
            messagebox.showerror("Erro", "Preencha o IP!")
            return

        try:
            self.socket_cliente = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket_cliente.connect((ip, 5000))

            registro = json.dumps({'tipo': 'REGISTRO', 'usuario': 'Recepção'})
            self.socket_cliente.sendall(registro.encode('utf-8'))

            data = self.socket_cliente.recv(2048)
            self.salvar_config_local(ip)

            thread_escuta = threading.Thread(target=self.receber_mensagens)
            thread_escuta.daemon = True
            thread_escuta.start()

            self.criar_tela_principal()

        except Exception as e:
            messagebox.showerror("Erro de Conexão", f"Não foi possível conectar ao servidor: {e}")

    def receber_mensagens(self):
        while True:
            try:
                data = self.socket_cliente.recv(4096)
                if not data:
                    break
                
                mensagem = json.loads(data.decode('utf-8'))
                tipo = mensagem.get('tipo')

                if tipo == 'ESTADO_REDE':
                    self.cadastrados = mensagem.get('cadastrados', [])
                    self.locais = mensagem.get('locais', [])
                    self.onlines = mensagem.get('onlines', [])
                    self.after(0, self.atualizar_interface)

                elif tipo == 'REGISTRO_CHAMADO':
                    self.after(0, lambda d=mensagem: self.adicionar_card_chamado(d))

                elif tipo == 'STATUS_ATUALIZADO':
                    id_c = mensagem.get('id_chamado')
                    status = mensagem.get('status')
                    motivo = mensagem.get('motivo', '')
                    self.after(0, lambda i=id_c, s=status, m=motivo: self.atualizar_status_card(i, s, m))

            except:
                break

    def atualizar_interface(self):
        opcoes_usr = []
        for u in self.cadastrados:
            if u != "Recepção":
                status = "🟢 Online" if u in self.onlines else "🔴 Offline"
                opcoes_usr.append(f"{u} ({status})")

        if opcoes_usr:
            self.combo_destinatarios.configure(values=opcoes_usr)
            self.combo_destinatarios.set(opcoes_usr[0])
        else:
            self.combo_destinatarios.configure(values=["Nenhum funcionário cadastrado"])

        if self.locais:
            self.combo_locais.configure(values=self.locais)
            self.combo_locais.set(self.locais[0])

    def enviar_alerta(self):
        selecionado = self.combo_destinatarios.get()
        local = self.combo_locais.get()
        visitante = self.ent_visitante.get().strip()
        assunto = self.ent_assunto.get().strip()

        if "Nenhum funcionário" in selecionado:
            return

        if "Offline" in selecionado:
            if not messagebox.askyesno("Aviso", "Este funcionário está Offline. Enviar mesmo assim?"):
                return

        destino = selecionado.split(" (")[0]

        if not visitante or not assunto:
            messagebox.showwarning("Aviso", "Preencha o visitante e o assunto!")
            return

        payload = json.dumps({
            'tipo': 'ALERTA',
            'destino': destino,
            'local': local,
            'visitante': visitante,
            'assunto': assunto
        })
        self.socket_cliente.sendall(payload.encode('utf-8'))
        
        self.ent_visitante.delete(0, 'end')
        self.ent_assunto.delete(0, 'end')

    def adicionar_card_chamado(self, dados):
        id_c = dados.get('id_chamado')
        destino = dados.get('destino')

        # Card container mais enxuto
        card = ctk.CTkFrame(self.scroll_chamados)
        card.pack(fill="x", pady=2, padx=3)

        # Cabeçalho: Info + Botões alinhados na mesma linha/seção superior
        frame_top = ctk.CTkFrame(card, fg_color="transparent")
        frame_top.pack(fill="x", padx=8, pady=(4, 0))

        lbl_info = ctk.CTkLabel(
            frame_top, 
            text=f"[{dados.get('horario')}] {dados.get('visitante')} ➔ {destino}\n📍 {dados.get('local')} | {dados.get('assunto')}", 
            anchor="w", 
            justify="left",
            font=("Arial", 11)
        )
        lbl_info.pack(side="left", fill="x", expand=True)

        # Container dos botões
        frame_botoes = ctk.CTkFrame(frame_top, fg_color="transparent")
        frame_botoes.pack(side="right", anchor="ne")

        btn_msg = ctk.CTkButton(
            frame_botoes, 
            text="💬 Responder", 
            width=85, 
            height=22, 
            font=("Arial", 10),
            fg_color="dodgerblue", 
            command=lambda: self.enviar_resposta_colaborador(id_c, destino)
        )
        btn_msg.pack(side="left", padx=2)

        btn_fim = ctk.CTkButton(
            frame_botoes, 
            text="✅ Finalizar", 
            width=75, 
            height=22, 
            font=("Arial", 10),
            fg_color="green", 
            command=lambda: self.finalizar_chamado(id_c, destino)
        )
        btn_fim.pack(side="left", padx=2)

        # Linha inferior: Status + Justificativa (se houver)
        lbl_status = ctk.CTkLabel(
            card, 
            text=dados.get('status'), 
            font=("Arial", 10, "bold"), 
            text_color="goldenrod",
            anchor="w"
        )
        lbl_status.pack(anchor="w", padx=8, pady=(0, 2))

        lbl_motivo = ctk.CTkLabel(
            card, 
            text="", 
            font=("Arial", 9, "italic"), 
            text_color="tomato", 
            anchor="w"
        )
        lbl_motivo.pack(anchor="w", padx=8, pady=(0, 4))

        self.chamados[id_c] = {
            "card": card,
            "lbl_status": lbl_status,
            "lbl_motivo": lbl_motivo,
            "destino": destino
        }

    def atualizar_status_card(self, id_chamado, novo_status, motivo=""):
        if id_chamado in self.chamados:
            item = self.chamados[id_chamado]
            lbl_s = item["lbl_status"]
            lbl_m = item["lbl_motivo"]

            lbl_s.configure(text=novo_status)
            if "Indo Agora" in novo_status:
                lbl_s.configure(text_color="green")
            elif "Não pode ir" in novo_status:
                lbl_s.configure(text_color="red")
            else:
                lbl_s.configure(text_color="goldenrod")

            if motivo:
                lbl_m.configure(text=f"💬 Justificativa: {motivo}")

    def enviar_resposta_colaborador(self, id_chamado, destino):
        dialog = ctk.CTkInputDialog(text=f"Nova mensagem para {destino}:", title="Responder Colaborador")
        resposta = dialog.get_input()
        if resposta and resposta.strip():
            payload = json.dumps({
                'tipo': 'MENSAGEM_RECEPCAO',
                'id_chamado': id_chamado,
                'destino': destino,
                'texto': resposta.strip()
            })
            self.socket_cliente.sendall(payload.encode('utf-8'))
            messagebox.showinfo("Enviado", "Mensagem enviada com sucesso!")

    def finalizar_chamado(self, id_chamado, destino):
        if id_chamado in self.chamados:
            payload = json.dumps({
                'tipo': 'FINALIZAR_CHAMADO',
                'id_chamado': id_chamado,
                'destino': destino
            })
            self.socket_cliente.sendall(payload.encode('utf-8'))

            card = self.chamados[id_chamado]["card"]
            card.destroy()
            del self.chamados[id_chamado]

    # --- CONFIGURAÇÕES ---
    def abrir_janela_gestao(self):
        janela = ctk.CTkToplevel(self)
        janela.title("Configurações do Sistema")
        janela.geometry("450x500")
        janela.attributes("-topmost", True)

        tabview = ctk.CTkTabview(janela)
        tabview.pack(fill="both", expand=True, padx=10, pady=10)

        tab_usr = tabview.add("Funcionários")
        tab_loc = tabview.add("Locais de Atendimento")

        # TAB 1
        ent_usr = ctk.CTkEntry(tab_usr, placeholder_text="Nome - Setor")
        ent_usr.pack(side="top", fill="x", padx=10, pady=5)

        scroll_usr = ctk.CTkScrollableFrame(tab_usr)
        scroll_usr.pack(fill="both", expand=True, padx=10, pady=5)

        def render_usr():
            for w in scroll_usr.winfo_children(): w.destroy()
            for u in self.cadastrados:
                if u != "Recepção":
                    f = ctk.CTkFrame(scroll_usr)
                    f.pack(fill="x", pady=2)
                    ctk.CTkLabel(f, text=u).pack(side="left", padx=10)
                    ctk.CTkButton(f, text="X", width=30, fg_color="red", command=lambda x=u: self.remover_usr(x)).pack(side="right", padx=5)

        def add_usr():
            n = ent_usr.get().strip()
            if n and n not in self.cadastrados:
                self.cadastrados.append(n)
                self.salvar_cadastros_rede()
                ent_usr.delete(0, 'end')
                render_usr()

        ctk.CTkButton(tab_usr, text="Adicionar Funcionário", command=add_usr).pack(fill="x", padx=10, pady=5)

        # TAB 2
        ent_loc = ctk.CTkEntry(tab_loc, placeholder_text="Ex: Guichê 02 / Sala 03")
        ent_loc.pack(side="top", fill="x", padx=10, pady=5)

        scroll_loc = ctk.CTkScrollableFrame(tab_loc)
        scroll_loc.pack(fill="both", expand=True, padx=10, pady=5)

        def render_loc():
            for w in scroll_loc.winfo_children(): w.destroy()
            for l in self.locais:
                f = ctk.CTkFrame(scroll_loc)
                f.pack(fill="x", pady=2)
                ctk.CTkLabel(f, text=l).pack(side="left", padx=10)
                ctk.CTkButton(f, text="X", width=30, fg_color="red", command=lambda x=l: self.remover_loc(x)).pack(side="right", padx=5)

        def add_loc():
            l = ent_loc.get().strip()
            if l and l not in self.locais:
                self.locais.append(l)
                self.salvar_cadastros_rede()
                ent_loc.delete(0, 'end')
                render_loc()

        ctk.CTkButton(tab_loc, text="Adicionar Local", command=add_loc).pack(fill="x", padx=10, pady=5)

        self.render_usr_func = render_usr
        self.render_loc_func = render_loc
        render_usr()
        render_loc()

    def remover_usr(self, nome):
        if nome in self.cadastrados:
            self.cadastrados.remove(nome)
            self.salvar_cadastros_rede()
            self.render_usr_func()

    def remover_loc(self, local):
        if local in self.locais:
            self.locais.remove(local)
            self.salvar_cadastros_rede()
            self.render_loc_func()

    def salvar_cadastros_rede(self):
        payload = json.dumps({
            'tipo': 'ATUALIZAR_CADASTRO',
            'usuarios': self.cadastrados,
            'locais': self.locais
        })
        self.socket_cliente.sendall(payload.encode('utf-8'))

if __name__ == "__main__":
    app = PainelRecepcao()
    app.mainloop()