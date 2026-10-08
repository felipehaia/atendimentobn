import socket
import threading
import json
import os
import sys
import uuid
from datetime import datetime
from pathlib import Path

# --- REDIRECIONAMENTO DE LOGS (Para rodar sem janela no Windows) ---
PASTA_DADOS = Path(os.environ.get("PROGRAMDATA", "C:/ProgramData")) / "Alerta Atendimento"
PASTA_LOGS = PASTA_DADOS / "logs"
PASTA_LOGS.mkdir(parents=True, exist_ok=True)

# Redireciona prints e erros para arquivos de log quando rodar sem console
if getattr(sys, 'frozen', False):
    sys.stdout = open(PASTA_LOGS / "servidor.log", "a", encoding="utf-8")
    sys.stderr = open(PASTA_LOGS / "servidor_error.log", "a", encoding="utf-8")

ARQUIVO_USUARIOS = PASTA_DADOS / "usuarios.json"
ARQUIVO_LOCAIS = PASTA_DADOS / "locais.json"

HOST = '0.0.0.0'
PORT = 5000

clientes_conectados = {}

def carregar_dados(arquivo, padrao):
    if not os.path.exists(arquivo):
        salvar_dados(arquivo, padrao)
        return padrao
    try:
        with open(arquivo, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return padrao

def salvar_dados(arquivo, lista):
    with open(arquivo, 'w', encoding='utf-8') as f:
        json.dump(lista, f, ensure_ascii=False, indent=4)

def tratar_cliente(conn, addr):
    nome_usuario = None
    try:
        while True:
            data = conn.recv(4096)
            if not data:
                break
            
            mensagem = json.loads(data.decode('utf-8'))
            tipo = mensagem.get('tipo')

            if tipo == 'REGISTRO':
                nome_tentativo = mensagem.get('usuario')
                cadastrados = carregar_dados(ARQUIVO_USUARIOS, ["Felipe - Arquiteto"])

                if nome_tentativo != 'Recepção' and nome_tentativo not in cadastrados:
                    resposta = json.dumps({
                        'tipo': 'ERRO_REGISTRO',
                        'mensagem': f"O utilizador '{nome_tentativo}' não está cadastrado!"
                    })
                    conn.sendall(resposta.encode('utf-8'))
                    break

                nome_usuario = nome_tentativo
                clientes_conectados[nome_usuario] = conn
                print(f"[ONLINE] {nome_usuario} ({addr})")

                conn.sendall(json.dumps({'tipo': 'REGISTRO_OK'}).encode('utf-8'))
                notificar_estado_rede()

            elif tipo == 'ALERTA':
                destino = mensagem.get('destino')
                id_chamado = str(uuid.uuid4())[:8]
                horario = datetime.now().strftime("%H:%M")
                local = mensagem.get('local', 'Recepção Principal')

                payload_colaborador = json.dumps({
                    'tipo': 'NOVO_ALERTA',
                    'id_chamado': id_chamado,
                    'visitante': mensagem.get('visitante'),
                    'assunto': mensagem.get('assunto'),
                    'local': local,
                    'horario': horario
                })

                if destino in clientes_conectados:
                    clientes_conectados[destino].sendall(payload_colaborador.encode('utf-8'))
                    status_inicial = "🟡 Aguardando resposta..."
                else:
                    status_inicial = "🔴 Indisponível (Offline)"

                if 'Recepção' in clientes_conectados:
                    payload_recepcao = json.dumps({
                        'tipo': 'REGISTRO_CHAMADO',
                        'id_chamado': id_chamado,
                        'destino': destino,
                        'visitante': mensagem.get('visitante'),
                        'assunto': mensagem.get('assunto'),
                        'local': local,
                        'horario': horario,
                        'status': status_inicial
                    })
                    clientes_conectados['Recepção'].sendall(payload_recepcao.encode('utf-8'))

            elif tipo == 'RESPOSTA_ALERTA':
                if 'Recepção' in clientes_conectados:
                    payload_resposta = json.dumps({
                        'tipo': 'STATUS_ATUALIZADO',
                        'id_chamado': mensagem.get('id_chamado'),
                        'status': mensagem.get('status'),
                        'motivo': mensagem.get('motivo', '')
                    })
                    clientes_conectados['Recepção'].sendall(payload_resposta.encode('utf-8'))

            elif tipo == 'MENSAGEM_RECEPCAO':
                destino = mensagem.get('destino')
                if destino in clientes_conectados:
                    payload_msg = json.dumps({
                        'tipo': 'MENSAGEM_RECEPCAO_RECEBIDA',
                        'id_chamado': mensagem.get('id_chamado'),
                        'texto': mensagem.get('texto')
                    })
                    clientes_conectados[destino].sendall(payload_msg.encode('utf-8'))

            elif tipo == 'FINALIZAR_CHAMADO':
                destino = mensagem.get('destino')
                if destino in clientes_conectados:
                    payload_fin = json.dumps({
                        'tipo': 'CHAMADO_FINALIZADO_NOTIF',
                        'id_chamado': mensagem.get('id_chamado')
                    })
                    clientes_conectados[destino].sendall(payload_fin.encode('utf-8'))

            elif tipo == 'ATUALIZAR_CADASTRO':
                if 'usuarios' in mensagem:
                    salvar_dados(ARQUIVO_USUARIOS, mensagem.get('usuarios'))
                if 'locais' in mensagem:
                    salvar_dados(ARQUIVO_LOCAIS, mensagem.get('locais'))
                notificar_estado_rede()

    except Exception as e:
        print(f"[ERRO] {addr}: {e}")
    finally:
        if nome_usuario and nome_usuario in clientes_conectados:
            del clientes_conectados[nome_usuario]
            print(f"[OFFLINE] {nome_usuario}")
            notificar_estado_rede()
        conn.close()

def notificar_estado_rede():
    cadastrados = carregar_dados(ARQUIVO_USUARIOS, ["Felipe - Arquiteto"])
    locais = carregar_dados(ARQUIVO_LOCAIS, ["Recepção Principal", "Sala de Reuniões 01", "Sala de Reuniões 02"])
    onlines = list(clientes_conectados.keys())
    
    payload = json.dumps({
        'tipo': 'ESTADO_REDE',
        'cadastrados': cadastrados,
        'locais': locais,
        'onlines': onlines
    })
    for conn in list(clientes_conectados.values()):
        try:
            conn.sendall(payload.encode('utf-8'))
        except:
            pass

def iniciar_servidor():
    carregar_dados(ARQUIVO_USUARIOS, ["Felipe - Arquiteto"])
    carregar_dados(ARQUIVO_LOCAIS, ["Recepção Principal", "Sala de Reuniões 01", "Sala de Reuniões 02"])
    
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((HOST, PORT))
    server.listen()
    print(f"Servidor de Atendimento rodando na porta {PORT}...")

    while True:
        conn, addr = server.accept()
        thread = threading.Thread(target=tratar_cliente, args=(conn, addr))
        thread.daemon = True
        thread.start()

if __name__ == "__main__":
    iniciar_servidor()