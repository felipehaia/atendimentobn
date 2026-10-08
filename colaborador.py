import customtkinter as ctk
import socket
import threading
import json
import os
import sys
from tkinter import messagebox
from PIL import Image, ImageDraw
import pystray
from pathlib import Path


def pasta_dados():
    caminho = Path(os.environ.get("LOCALAPPDATA", Path.home())) / "Alerta Atendimento"
    caminho.mkdir(parents=True, exist_ok=True)
    return caminho

ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")

CONFIG_FILE = pasta_dados() / "config_local.json"

def criar_icone_padrao():
    image = Image.new('RGB', (64, 64), color=(30, 144, 255))
    d = ImageDraw.Draw(image)
    d.rectangle([16, 16, 48, 48], fill=(255, 255, 255))
    return image

class AppColaborador(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Alerta de Atendimento - Colaborador")
        self.geometry("380x280")
        self.resizable(False, False)

        self.protocol("WM_DELETE_WINDOW", self.minimizar_para_tray)

        self.socket_cliente = None
        self.nome_usuario = ""
        self.tray_icon = None
        
        # Guarda as informações e janelas ativas dos chamados: {id_chamado: {"popup": window, "dados": dict, "lbl_chat": label}}
        self.chamados_ativos = {}

        self.config_local = self.carregar_config_local()

        if self.config_local.get("ultimo_ip") and self.config_local.get("ultimo_usuario"):
            if not self.tentar_autologin():
                self.criar_tela_login()
        else:
            self.criar_tela_login()

    def carregar_config_local(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                pass
        return {"ultimo_ip": "172.31.23.174", "ultimo_usuario": ""}

    def salvar_config_local(self, ip, usuario):
        dados = {"ultimo_ip": ip, "ultimo_usuario": usuario}
        try:
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(dados, f, ensure_ascii=False, indent=4)
        except Exception as e:
            print(f"[ERRO CONFIG] {e}")

    def criar_tela_login(self):
        if hasattr(self, 'frame_main') and self.frame_main:
            self.frame_main.pack_forget()

        self.frame_login = ctk.CTkFrame(self)
        self.frame_login.pack(padx=20, pady=20, fill="both", expand=True)

        ctk.CTkLabel(self.frame_login, text="Receptor de Alertas", font=("Arial", 18, "bold")).pack(pady=15)

        ctk.CTkLabel(self.frame_login, text="IP do Servidor:").pack(anchor="w", padx=20)
        self.ent_ip = ctk.CTkEntry(self.frame_login)
        self.ent_ip.insert(0, self.config_local.get("ultimo_ip", "172.31.23.174"))
        self.ent_ip.pack(fill="x", padx=20, pady=(0, 10))

        ctk.CTkLabel(self.frame_login, text="Seu Nome Cadastrado:").pack(anchor="w", padx=20)
        self.ent_nome = ctk.CTkEntry(self.frame_login, placeholder_text="Ex: João - Engenharia")
        ultimo_usr = self.config_local.get("ultimo_usuario", "")
        if ultimo_usr:
            self.ent_nome.insert(0, ultimo_usr)
        self.ent_nome.pack(fill="x", padx=20, pady=(0, 15))

        btn_conectar = ctk.CTkButton(self.frame_login, text="Iniciar Monitoramento", command=self.conectar)
        btn_conectar.pack(pady=10)

    def criar_tela_principal(self):
        if hasattr(self, 'frame_login') and self.frame_login:
            self.frame_login.pack_forget()

        self.frame_main = ctk.CTkFrame(self)
        self.frame_main.pack(padx=20, pady=20, fill="both", expand=True)

        ctk.CTkLabel(self.frame_main, text=f"Sessão: {self.nome_usuario}", font=("Arial", 14, "bold")).pack(pady=(15, 5))
        ctk.CTkLabel(self.frame_main, text="● Monitorando Alertas na Rede", text_color="green", font=("Arial", 12)).pack(pady=(0, 15))

        ctk.CTkLabel(self.frame_main, text="O aplicativo roda em segundo plano na barra de tarefas.", font=("Arial", 11), text_color="gray").pack(pady=10)

        frame_botoes = ctk.CTkFrame(self.frame_main, fg_color="transparent")
        frame_botoes.pack(pady=15)

        btn_minimizar = ctk.CTkButton(frame_botoes, text="Minimizar p/ Relógio", command=self.minimizar_para_tray, fg_color="gray30")
        btn_minimizar.pack(side="left", padx=5)

        btn_logout = ctk.CTkButton(frame_botoes, text="Trocar Conta", command=self.desconectar, fg_color="firebrick")
        btn_logout.pack(side="left", padx=5)

    def minimizar_para_tray(self):
        self.withdraw()
        if not self.tray_icon:
            icon_image = criar_icone_padrao()
            menu = pystray.Menu(
                pystray.MenuItem("Abrir Painel", self.restaurar_janela),
                pystray.MenuItem("Sair Definitivamente", self.encerrar_aplicacao)
            )
            self.tray_icon = pystray.Icon("AlertaRecepcao", icon_image, "Alerta de Atendimento", menu)
            threading.Thread(target=self.tray_icon.run, daemon=True).start()

    def restaurar_janela(self, icon=None, item=None):
        if self.tray_icon:
            self.tray_icon.stop()
            self.tray_icon = None
        self.after(0, self.deiconify)

    def encerrar_aplicacao(self, icon=None, item=None):
        if self.tray_icon:
            self.tray_icon.stop()
        if self.socket_cliente:
            try:
                self.socket_cliente.close()
            except:
                pass
        self.destroy()
        sys.exit()

    def tentar_autologin(self):
        ip = self.config_local.get("ultimo_ip")
        usuario = self.config_local.get("ultimo_usuario")
        return self.executar_conexao(ip, usuario, silencioso=True)

    def conectar(self):
        ip = self.ent_ip.get().strip()
        usuario = self.ent_nome.get().strip()
        if not ip or not usuario:
            messagebox.showerror("Erro", "Preencha o IP e o seu Nome!")
            return
        self.executar_conexao(ip, usuario, silencioso=False)

    def executar_conexao(self, ip, usuario, silencioso=False):
        try:
            self.socket_cliente = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket_cliente.settimeout(3.0)
            self.socket_cliente.connect((ip, 5000))

            registro = json.dumps({'tipo': 'REGISTRO', 'usuario': usuario})
            self.socket_cliente.sendall(registro.encode('utf-8'))

            data = self.socket_cliente.recv(2048)
            if data:
                resposta = json.loads(data.decode('utf-8'))
                if resposta.get('tipo') == 'ERRO_REGISTRO':
                    if not silencioso:
                        messagebox.showerror("Acesso Negado", resposta.get('mensagem'))
                    self.socket_cliente.close()
                    return False

            self.socket_cliente.settimeout(None)
            self.nome_usuario = usuario
            self.salvar_config_local(ip, usuario)

            thread_escuta = threading.Thread(target=self.receber_mensagens)
            thread_escuta.daemon = True
            thread_escuta.start()

            self.criar_tela_principal()
            return True

        except Exception as e:
            if not silencioso:
                messagebox.showerror("Erro de Conexão", f"Não foi possível conectar ao servidor: {e}")
            return False

    def desconectar(self):
        if self.socket_cliente:
            try:
                self.socket_cliente.close()
            except:
                pass
            self.socket_cliente = None
        self.criar_tela_login()

    def receber_mensagens(self):
        while True:
            try:
                data = self.socket_cliente.recv(4096)
                if not data:
                    break
                
                mensagem = json.loads(data.decode('utf-8'))
                tipo = mensagem.get('tipo')

                if tipo == 'NOVO_ALERTA':
                    dados_alerta = mensagem
                    self.after(0, lambda d=dados_alerta: self.disparar_popup_alerta(d))

                elif tipo == 'MENSAGEM_RECEPCAO_RECEBIDA':
                    id_c = mensagem.get('id_chamado')
                    texto = mensagem.get('texto')
                    self.after(0, lambda i=id_c, t=texto: self.tratar_mensagem_recepcao(i, t))

                elif tipo == 'CHAMADO_FINALIZADO_NOTIF':
                    id_c = mensagem.get('id_chamado')
                    self.after(0, lambda i=id_c: self.fechar_popup_chamado(i))

            except:
                break

    # --- LÓGICA DO POP-UP E REABERTURA ---
    def disparar_popup_alerta(self, dados, mensagem_recepcao=""):
        id_chamado = dados.get('id_chamado')
        visitante = dados.get('visitante')
        assunto = dados.get('assunto')
        local = dados.get('local', 'Recepção Principal')

        # Registra ou recupera os dados do chamado
        if id_chamado not in self.chamados_ativos:
            self.chamados_ativos[id_chamado] = {"dados": dados, "popup": None, "lbl_chat": None}
        else:
            self.chamados_ativos[id_chamado]["dados"] = dados

        # Se já existir uma janela aberta para esse chamado, apenas fecha antes de reabrir limpa
        old_popup = self.chamados_ativos[id_chamado].get("popup")
        if old_popup and old_popup.winfo_exists():
            old_popup.destroy()

        popup = ctk.CTkToplevel(self)
        popup.title("⚠️ ATENDIMENTO NA RECEPÇÃO")
        popup.geometry("500x350")
        popup.attributes("-topmost", True)
        popup.focus_force()
        popup.bell()

        self.chamados_ativos[id_chamado]["popup"] = popup

        ctk.CTkLabel(popup, text="NOVO VISITANTE AGUARDANDO", font=("Arial", 15, "bold"), text_color="firebrick").pack(pady=10)

        frame_info = ctk.CTkFrame(popup)
        frame_info.pack(fill="both", expand=True, padx=15, pady=5)

        ctk.CTkLabel(frame_info, text=f"👤 Visitante: {visitante}", font=("Arial", 13, "bold"), anchor="w").pack(fill="x", padx=10, pady=2)
        ctk.CTkLabel(frame_info, text=f"📍 Dirigir-se a: {local}", font=("Arial", 13, "bold"), text_color="dodgerblue", anchor="w").pack(fill="x", padx=10, pady=2)
        ctk.CTkLabel(frame_info, text=f"📝 Assunto: {assunto}", font=("Arial", 12), anchor="w").pack(fill="x", padx=10, pady=2)

        # Label dinâmico para a conversa/réplica da recepção
        lbl_chat = ctk.CTkLabel(frame_info, text="", font=("Arial", 11, "bold"), text_color="dodgerblue", anchor="w", justify="left")
        lbl_chat.pack(fill="x", padx=10, pady=5)
        self.chamados_ativos[id_chamado]["lbl_chat"] = lbl_chat

        if mensagem_recepcao:
            lbl_chat.configure(text=f"💬 Réplica da Recepção:\n\"{mensagem_recepcao}\"")

        frame_acoes = ctk.CTkFrame(popup, fg_color="transparent")
        frame_acoes.pack(pady=12)

        def responder(status, motivo=""):
            payload = json.dumps({
                'tipo': 'RESPOSTA_ALERTA',
                'id_chamado': id_chamado,
                'status': status,
                'motivo': motivo
            })
            self.socket_cliente.sendall(payload.encode('utf-8'))
            
            # FECHA O POPUP IMEDIATAMENTE (Seja "Indo Agora", "Prazo" ou "Não Posso")
            if popup and popup.winfo_exists():
                popup.destroy()
                self.chamados_ativos[id_chamado]["popup"] = None

        def abrir_janela_recusa():
            dialog = ctk.CTkInputDialog(text="Informe o motivo pelo qual não poderá ir:", title="Justificativa")
            motivo = dialog.get_input()
            if motivo and motivo.strip():
                responder("🔴 Não pode ir", motivo.strip())

        btn_agora = ctk.CTkButton(frame_acoes, text="🟢 Indo Agora", command=lambda: responder("🟢 Indo Agora"), fg_color="green", width=110)
        btn_agora.pack(side="left", padx=3)

        combo_min = ctk.CTkOptionMenu(frame_acoes, values=["5 min", "10 min", "15 min", "30 min"], width=85)
        combo_min.set("10 min")
        combo_min.pack(side="left", padx=3)

        btn_prazo = ctk.CTkButton(frame_acoes, text="⏱️ Irá em breve", command=lambda: responder(f"⏱️ Irá em {combo_min.get()}"), width=110)
        btn_prazo.pack(side="left", padx=3)

        btn_recusar = ctk.CTkButton(frame_acoes, text="🔴 Não posso ir", command=abrir_janela_recusa, fg_color="firebrick", hover_color="darkred", width=110)
        btn_recusar.pack(side="left", padx=3)

    def tratar_mensagem_recepcao(self, id_chamado, texto):
        if id_chamado in self.chamados_ativos:
            dados_chamado = self.chamados_ativos[id_chamado]["dados"]
            popup = self.chamados_ativos[id_chamado].get("popup")

            # Se a janela estivesse fechada, reabre estourando na tela com a nova mensagem
            if not popup or not popup.winfo_exists():
                self.disparar_popup_alerta(dados_chamado, mensagem_recepcao=texto)
            else:
                # Se estivesse aberta, foca nela e atualiza o texto
                popup.bell()
                popup.focus_force()
                lbl = self.chamados_ativos[id_chamado].get("lbl_chat")
                if lbl and lbl.winfo_exists():
                    lbl.configure(text=f"💬 Réplica da Recepção:\n\"{texto}\"")

    def fechar_popup_chamado(self, id_chamado):
        if id_chamado in self.chamados_ativos:
            popup = self.chamados_ativos[id_chamado].get("popup")
            if popup and popup.winfo_exists():
                popup.destroy()
            del self.chamados_ativos[id_chamado]

if __name__ == "__main__":
    app = AppColaborador()
    app.mainloop()