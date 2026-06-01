import cv2
import mediapipe as mp
import pyautogui
import time
import numpy as np
import tkinter as tk
import threading
import math

# --------------------------------------------------
# CONFIGURAÇÕES INICIAIS
# --------------------------------------------------

pyautogui.FAILSAFE = False

largura_tela, altura_tela = pyautogui.size()

mp_rosto = mp.solutions.face_mesh

rastreador_rosto = mp_rosto.FaceMesh(refine_landmarks=True)

camera = cv2.VideoCapture(0)

# --------------------------------------------------
# VARIÁVEIS
# --------------------------------------------------

rodando = False
status = None

mouse_x_anterior = largura_tela / 2
mouse_y_anterior = altura_tela / 2

suavizacao = 0.20

olho_esquerdo_antes = False
olho_direito_antes = False

inicio_olhos_fechados = None
pausa_acionada = False

# --------------------------------------------------
# FUNÇÕES
# --------------------------------------------------

def distancia(p1, p2):
    return math.hypot(p1.x - p2.x, p1.y - p2.y)

def olho_fechado(cima1, cima2, baixo1, baixo2, lado1, lado2):

    vertical = distancia(cima1, baixo1) + distancia(cima2, baixo2)
    horizontal = distancia(lado1, lado2)

    razao = vertical / horizontal

    return razao < 0.18

# --------------------------------------------------
# CALIBRAÇÃO
# --------------------------------------------------

def coletar_amostras(segundos, nome):

    print("Olhe para", nome)

    dados = []
    inicio = time.time()

    while time.time() - inicio < segundos:

        ret, frame = camera.read()

        if not ret:
            continue

        frame = cv2.flip(frame, 1)

        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        resultado = rastreador_rosto.process(rgb)

        if resultado.multi_face_landmarks:

            iris = resultado.multi_face_landmarks[0].landmark[468]
            dados.append((iris.x, iris.y))

    return dados

def mediana_x(lista):
    return np.median([p[0] for p in lista])

def mediana_y(lista):
    return np.median([p[1] for p in lista])

#--------------------------------------
#CALIBRAÇÂO
#--------------------------------------
print("=== CALIBRAÇÃO ===")

input("CENTRO + ENTER")
centro = coletar_amostras(2, "CENTRO")

input("ESQUERDA + ENTER")
esquerda = coletar_amostras(2, "ESQUERDA")

input("DIREITA + ENTER")
direita = coletar_amostras(2, "DIREITA")

input("CIMA + ENTER")
cima = coletar_amostras(2, "CIMA")

input("BAIXO + ENTER")
baixo = coletar_amostras(2, "BAIXO")

minimo_x = mediana_x(esquerda)
maximo_x = mediana_x(direita)

minimo_y = mediana_y(cima)
maximo_y = mediana_y(baixo)

print("Calibrado!")

# --------------------------------------------------
# INTERFACE
# --------------------------------------------------

def iniciar():
    global rodando
    rodando = True
    status.set("Rodando")


def parar():
    global rodando
    rodando = False
    status.set("Parado")


janela = tk.Tk()
janela.title("Eye Tracker")
janela.geometry("320x220")
janela.attributes("-topmost", True)

status = tk.StringVar()
status.set("Parado")

tk.Label(
    janela,
    textvariable=status,
    font=("Arial", 12)
).pack(pady=10)

tk.Button(
    janela,
    text="Iniciar",
    width=24,
    command=iniciar
).pack(pady=5)

tk.Button(
    janela,
    text="Parar",
    width=24,
    command=parar
).pack(pady=5)

# --------------------------------------------------
# LOOP PRINCIPAL
# --------------------------------------------------

def loop_camera():

    global rodando
    global mouse_x_anterior, mouse_y_anterior
    global olho_esquerdo_antes, olho_direito_antes
    global inicio_olhos_fechados, pausa_acionada

    while True:

        ret, frame = camera.read()

        if not ret:
            continue

        frame = cv2.flip(frame, 1)

        altura_camera, largura_camera, _ = frame.shape

        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        resultado = rastreador_rosto.process(rgb)

        if resultado.multi_face_landmarks:

            rosto = resultado.multi_face_landmarks[0].landmark

            # ----------------------------------
            # DETECTAR BOCA
            # ----------------------------------

            abertura = distancia(rosto[13], rosto[14])

            # boca aberta = trava mouse
            boca_aberta = (abertura * largura_camera) > 14

            # ----------------------------------
            # MOVER MOUSE
            # ----------------------------------

            if rodando and not boca_aberta:

                iris = rosto[468]

                normal_x = (iris.x - minimo_x) / (maximo_x - minimo_x)
                normal_y = (iris.y - minimo_y) / (maximo_y - minimo_y)

                normal_x = max(0, min(1, normal_x))
                normal_y = max(0, min(1, normal_y))

                alvo_x = normal_x * largura_tela
                alvo_y = normal_y * altura_tela

                atual_x = mouse_x_anterior + (alvo_x - mouse_x_anterior) * suavizacao
                atual_y = mouse_y_anterior + (alvo_y - mouse_y_anterior) * suavizacao

                pyautogui.moveTo(atual_x, atual_y)

                mouse_x_anterior = atual_x
                mouse_y_anterior = atual_y

            # ----------------------------------
            # DETECTAR OLHOS
            # ----------------------------------

            olho_esquerdo = olho_fechado(
                rosto[159], rosto[160],
                rosto[145], rosto[144],
                rosto[33], rosto[133]
            )

            olho_direito = olho_fechado(
                rosto[386], rosto[387],
                rosto[374], rosto[373],
                rosto[362], rosto[263]
            )

            # ----------------------------------
            # CLIQUES
            # ----------------------------------

            # só clica quando boca aberta
            if boca_aberta:

                if olho_esquerdo and not olho_esquerdo_antes:
                    pyautogui.click(button="left")
                    status.set("Clique esquerdo")

                if olho_direito and not olho_direito_antes:
                    pyautogui.click(button="right")
                    status.set("Clique direito")

            # ----------------------------------
            # FECHAR DOIS OLHOS = PAUSAR SISTEMA
            # ----------------------------------

            agora = time.time()

            if olho_esquerdo and olho_direito:

                if inicio_olhos_fechados is None:
                    inicio_olhos_fechados = agora

                if agora - inicio_olhos_fechados >= 1.5 and not pausa_acionada:

                    rodando = not rodando

                    if rodando:
                        status.set("Rodando")
                    else:
                        status.set("Pausado")

                    pausa_acionada = True

            else:
                inicio_olhos_fechados = None
                pausa_acionada = False

            olho_esquerdo_antes = olho_esquerdo
            olho_direito_antes = olho_direito

        cv2.imshow("Acessibilidade", frame)

        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

    camera.release()
    cv2.destroyAllWindows()


# --------------------------------------------------
# INICIAR THREAD
# --------------------------------------------------

threading.Thread(target=loop_camera, daemon=True).start()

janela.mainloop()