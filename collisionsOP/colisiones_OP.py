# -*- coding: utf-8 -*-
"""
===============================================================================
  CONSERVACIÓN DEL MOMENTUM LINEAL  -  Simulador / videojuego de colisiones
===============================================================================
Asteroides y planetas chocan en 2D. En tiempo real se puede comprobar que

        Σ p = Σ m_i v_i   (vector)

se conserva en TODO choque (sistema aislado), mientras que la energía cinética
solo se conserva en el choque elástico.

REQUISITOS : Python 3 + pygame            ->   pip install pygame
             (en la consola de Spyder:        %pip install pygame)
EJECUCIÓN  : abrir este archivo en Spyder y pulsar F5 (Run file).
             Si la ventana queda detrás de Spyder, búscala en la barra de tareas.

FÍSICA IMPLEMENTADA
  * Cuerpos circulares con masa m = DENSIDAD * r^3  (unidades SI: m, kg, s).
  * Choque entre dos cuerpos (sin fricción) con coeficiente de restitución e:
        impulso   J = (1 + e) * (v1 - v2)·n / (1/m1 + 1/m2)
        v1' = v1 - (J/m1) n          v2' = v2 + (J/m2) n
    Las fuerzas de contacto son iguales y opuestas -> Σp se conserva EXACTO
    (hasta el error de redondeo, que se muestra en pantalla).
        e = 1  -> elástico (K se conserva)
        0<e<1  -> inelástico (K disminuye)
        fusión -> perfectamente inelástico: los cuerpos se pegan y
                  v_final = Σp / M   (pérdida máxima de K en el marco CM)
  * Gravedad mutua opcional (tecla G): es una fuerza INTERNA (3ª ley de
    Newton), así que Σp tampoco cambia.
  * Paredes opcionales (tecla B): son una fuerza EXTERNA; ahí Σp sí cambia y
    el programa muestra el impulso que entregan las paredes (teorema
    impulso-momentum).
===============================================================================
"""

import math
import random
from collections import deque
import pygame

# =============================  PARÁMETROS  ==================================
ANCHO, ALTO = 1240, 720          # tamaño de la ventana (px)
ANCHO_SIM = 860                  # ancho de la zona de simulación (px)
FPS = 60
SUBPASOS = 8                     # subpasos de física por fotograma

ESCALA = 10.0                    # px por metro
DENSIDAD = 1.0                   # kg/m^3  (densidad "de juguete")
FACTOR_ARRASTRE = 0.2            # (m/s) por px arrastrados con el ratón
V_MAX = 80.0                     # velocidad máxima de lanzamiento (m/s)
G_GRAV = 20.0                    # constante gravitacional de juguete (m^3/kg/s^2)
SUAVIZADO = 0.8                  # suavizado gravitacional (m)
VN_MIN_REGISTRO = 0.5            # m/s: choques más suaves no se anotan en el panel
LONG_TRAZA = 160                 # puntos de la estela
MUESTRAS_HIST = 720              # muestras en las gráficas (12 s a 60 FPS)
RADIO_MIN, RADIO_MAX = 0.6, 6.0  # m
RADIO_ASTEROIDE = 2.0            # m: por debajo se etiqueta "A", si no "P"

LARGO_M = ANCHO_SIM / ESCALA     # tamaño del "universo" visible (m)
ALTO_M = ALTO / ESCALA
CX0_PX, CY0_PX = ANCHO_SIM / 2, ALTO / 2   # centro de la zona de simulación (px)
CXM, CYM = LARGO_M / 2, ALTO_M / 2          # mismo punto en metros

ELASTICO, INELASTICO, FUSION = 0, 1, 2

# Colores
FONDO = (6, 8, 20)
PANEL = (14, 17, 34)
BLANCO = (235, 238, 245)
GRIS = (130, 138, 160)
GRIS_OSC = (60, 66, 96)
VERDE = (110, 220, 140)
AMARILLO = (240, 210, 90)
NARANJA = (255, 150, 70)
ROJO = (235, 90, 90)
CIAN = (90, 200, 240)
ROSA = (240, 120, 200)
PALETA_PLANETA = [(86, 140, 214), (214, 120, 70), (120, 190, 130),
                  (200, 170, 100), (170, 120, 200), (220, 100, 110),
                  (100, 190, 200)]
PALETA_ASTEROIDE = [(150, 140, 130), (125, 118, 110), (170, 160, 150),
                    (140, 130, 125)]


# ===========================  FÍSICA (sin pygame)  ===========================
class Cuerpo:
    """Disco rígido: posición y radio en m, velocidad en m/s, masa en kg."""
    contador = 0

    def __init__(self, x, y, vx, vy, radio, color=None):
        Cuerpo.contador += 1
        self.id = Cuerpo.contador
        self.x, self.y = float(x), float(y)
        self.vx, self.vy = float(vx), float(vy)
        self.r = float(radio)
        self.m = DENSIDAD * self.r ** 3
        if color is None:
            paleta = PALETA_ASTEROIDE if self.r < RADIO_ASTEROIDE else PALETA_PLANETA
            color = random.choice(paleta)
        self.color = color
        self.traza = deque(maxlen=LONG_TRAZA)

    @property
    def nombre(self):
        return ("A" if self.r < RADIO_ASTEROIDE else "P") + str(self.id)

    @property
    def px(self):
        return self.m * self.vx

    @property
    def py(self):
        return self.m * self.vy

    @property
    def energia(self):
        return 0.5 * self.m * (self.vx ** 2 + self.vy ** 2)


class Mundo:
    """Contiene los cuerpos, integra el movimiento y resuelve las colisiones."""

    def __init__(self):
        self.modo = ELASTICO
        self.e = 0.5                 # coeficiente de restitución (modo INELASTICO)
        self.gravedad = False
        self.paredes = False
        self.eventos = deque(maxlen=300)    # instantes de los choques (para las gráficas)
        self.hist = deque(maxlen=MUESTRAS_HIST)
        self.destellos = []                 # [x, y, edad] anillos visuales de choque
        self.reiniciar()

    # ------------------------------------------------------------------ estado
    def reiniciar(self):
        Cuerpo.contador = 0
        self.cuerpos = []
        self.t = 0.0
        self.k_disipada = 0.0        # energía cinética perdida en choques (J)
        self.ultimo = None           # datos del último choque
        self.eventos.clear()
        self.hist.clear()
        self.destellos = []
        self.P_ref = (0.0, 0.0)      # Σp "esperado" (cambia solo por acciones externas)
        self.J_ext = [0.0, 0.0]      # impulso externo acumulado (paredes)

    def fijar_referencia(self):
        """Tras una acción externa (lanzar, borrar) se toma el Σp actual como referencia."""
        self.P_ref = self.momento_total()
        self.J_ext = [0.0, 0.0]

    def agregar(self, cuerpo):
        self.cuerpos.append(cuerpo)
        self.fijar_referencia()

    def quitar(self, cuerpo):
        if cuerpo in self.cuerpos:
            self.cuerpos.remove(cuerpo)
        self.fijar_referencia()

    # ------------------------------------------------------------ magnitudes
    def momento_total(self):
        return (sum(c.px for c in self.cuerpos), sum(c.py for c in self.cuerpos))

    def energia_total(self):
        return sum(c.energia for c in self.cuerpos)

    def masa_total(self):
        return sum(c.m for c in self.cuerpos)

    def centro_masa(self):
        """(x, y, vx, vy) del centro de masa, o None si no hay cuerpos."""
        M = self.masa_total()
        if M <= 0:
            return None
        cs = self.cuerpos
        return (sum(c.m * c.x for c in cs) / M, sum(c.m * c.y for c in cs) / M,
                sum(c.m * c.vx for c in cs) / M, sum(c.m * c.vy for c in cs) / M)

    def desviacion_momento(self):
        """|Σp - (Σp_ref + impulso externo)|: debe ser ~1e-13 (solo redondeo)."""
        P = self.momento_total()
        return math.hypot(P[0] - self.P_ref[0] - self.J_ext[0],
                          P[1] - self.P_ref[1] - self.J_ext[1])

    # ------------------------------------------------------------ dinámica
    def paso(self, dt):
        if self.gravedad:
            self._gravedad(dt)
        for c in self.cuerpos:
            c.x += c.vx * dt
            c.y += c.vy * dt
        if self.paredes:
            self._paredes()
        self._colisiones()
        self.t += dt

    def _gravedad(self, dt):
        """Atracción mutua. Impulsos iguales y opuestos -> Σp se conserva."""
        cs = self.cuerpos
        n = len(cs)
        for i in range(n):
            a = cs[i]
            for j in range(i + 1, n):
                b = cs[j]
                dx, dy = b.x - a.x, b.y - a.y
                r2 = dx * dx + dy * dy + SUAVIZADO ** 2
                k = G_GRAV * dt / (r2 * math.sqrt(r2))
                a.vx += k * b.m * dx
                a.vy += k * b.m * dy
                b.vx -= k * a.m * dx
                b.vy -= k * a.m * dy

    def _paredes(self):
        """Paredes elásticas (fuerza externa). Se acumula el impulso que reciben."""
        for c in self.cuerpos:
            if c.x - c.r < 0 and c.vx < 0:
                self.J_ext[0] += -2 * c.m * c.vx
                c.vx = -c.vx
                c.x = c.r
            elif c.x + c.r > LARGO_M and c.vx > 0:
                self.J_ext[0] += -2 * c.m * c.vx
                c.vx = -c.vx
                c.x = LARGO_M - c.r
            if c.y - c.r < 0 and c.vy < 0:
                self.J_ext[1] += -2 * c.m * c.vy
                c.vy = -c.vy
                c.y = c.r
            elif c.y + c.r > ALTO_M and c.vy > 0:
                self.J_ext[1] += -2 * c.m * c.vy
                c.vy = -c.vy
                c.y = ALTO_M - c.r

    def _colisiones(self):
        cs = self.cuerpos
        n = len(cs)
        usados = set()
        fusiones = []
        for i in range(n):
            a = cs[i]
            for j in range(i + 1, n):
                b = cs[j]
                dx, dy = b.x - a.x, b.y - a.y
                rs = a.r + b.r
                d2 = dx * dx + dy * dy
                if d2 >= rs * rs:
                    continue
                if self.modo == FUSION:
                    if a.id not in usados and b.id not in usados:
                        usados.update((a.id, b.id))
                        fusiones.append((a, b))
                else:
                    self._rebote(a, b, dx, dy, d2, rs)
        for a, b in fusiones:
            self._fusionar(a, b)

    def _rebote(self, a, b, dx, dy, d2, rs):
        d = math.sqrt(d2)
        if d < 1e-12:                       # centros coincidentes: dirección arbitraria
            nx, ny = 1.0, 0.0
        else:
            nx, ny = dx / d, dy / d         # normal de a hacia b
        ma, mb = a.m, b.m
        mt = ma + mb

        # 1) separar el solapamiento sin mover el centro de masa
        sol = rs - d
        a.x -= nx * sol * mb / mt
        a.y -= ny * sol * mb / mt
        b.x += nx * sol * ma / mt
        b.y += ny * sol * ma / mt

        # 2) impulso a lo largo de la normal (si se están acercando)
        vn = (a.vx - b.vx) * nx + (a.vy - b.vy) * ny
        if vn <= 1e-9:
            return
        e = 1.0 if self.modo == ELASTICO else self.e
        pa = (ma * a.vx + mb * b.vx, ma * a.vy + mb * b.vy)
        ka = a.energia + b.energia

        J = (1.0 + e) * vn / (1.0 / ma + 1.0 / mb)
        a.vx -= J * nx / ma
        a.vy -= J * ny / ma
        b.vx += J * nx / mb
        b.vy += J * ny / mb

        pd = (ma * a.vx + mb * b.vx, ma * a.vy + mb * b.vy)
        kd = a.energia + b.energia
        self.k_disipada += ka - kd
        if vn > VN_MIN_REGISTRO:
            tipo = "elástico" if self.modo == ELASTICO else f"inelástico e={e:.2f}"
            self._anotar(a.nombre, b.nombre, tipo, pa, pd, ka, kd,
                         a.x + nx * a.r, a.y + ny * a.r)

    def _fusionar(self, a, b):
        """Choque perfectamente inelástico: un solo cuerpo con v = Σp / M."""
        if a not in self.cuerpos or b not in self.cuerpos:
            return
        m = a.m + b.m
        pa = (a.m * a.vx + b.m * b.vx, a.m * a.vy + b.m * b.vy)
        ka = a.energia + b.energia
        x = (a.m * a.x + b.m * b.x) / m
        y = (a.m * a.y + b.m * b.y) / m
        radio = (a.r ** 3 + b.r ** 3) ** (1.0 / 3.0)
        color = a.color if a.m >= b.m else b.color
        nuevo = Cuerpo(x, y, pa[0] / m, pa[1] / m, radio, color)
        nuevo.m = m                          # evita errores de redondeo en la masa
        pd = (nuevo.m * nuevo.vx, nuevo.m * nuevo.vy)
        kd = nuevo.energia
        self.k_disipada += ka - kd
        self._anotar(a.nombre, b.nombre, "fusión", pa, pd, ka, kd, x, y)
        self.cuerpos.remove(a)
        self.cuerpos.remove(b)
        self.cuerpos.append(nuevo)

    def _anotar(self, na, nb, tipo, pa, pd, ka, kd, xc, yc):
        self.ultimo = dict(t=self.t, a=na, b=nb, tipo=tipo, pa=pa, pd=pd, ka=ka, kd=kd)
        self.eventos.append(self.t)
        self.destellos.append([xc, yc, 0])

    # ------------------------------------------------------------ registro
    def registrar(self):
        """Se llama una vez por fotograma: gráficas, estelas y destellos."""
        px, py = self.momento_total()
        self.hist.append((self.t, px, py, self.energia_total()))
        cm = self.centro_masa()
        for c in self.cuerpos:
            c.traza.append((c.x, c.y, cm[0], cm[1]))
        for d in self.destellos:
            d[2] += 1
        self.destellos = [d for d in self.destellos if d[2] < 30]


# ===============================  CÁMARA  ====================================
class Camara:
    """Convierte metros <-> píxeles. Puede seguir al centro de masa."""

    def __init__(self):
        self.x, self.y = CXM, CYM
        self.seguir = False
        self.trans = 0

    def alternar(self):
        self.seguir = not self.seguir
        self.trans = 25

    def actualizar(self, mundo):
        cm = mundo.centro_masa()
        objetivo = (cm[0], cm[1]) if (self.seguir and cm) else (CXM, CYM)
        if self.trans > 0 or not self.seguir:
            k = 1.0 - 0.8 * self.trans / 25.0 if self.seguir else 0.2
            self.x += (objetivo[0] - self.x) * k
            self.y += (objetivo[1] - self.y) * k
            self.trans = max(0, self.trans - 1)
        else:
            self.x, self.y = objetivo

    def a_pantalla(self, x, y):
        return ((x - self.x) * ESCALA + CX0_PX, (y - self.y) * ESCALA + CY0_PX)

    def a_mundo(self, sx, sy):
        return ((sx - CX0_PX) / ESCALA + self.x, (sy - CY0_PX) / ESCALA + self.y)


# ===============================  ESCENARIOS  ================================
ESCENARIOS = {
    0: ("Espacio vacío",
        ["Lanza tus propios cuerpos: clic y arrastra (la flecha fija la velocidad).",
         "Prueba distintos tipos de choque con la tecla M."]),
    1: ("1) Choque frontal, masas iguales (elástico)",
        ["Con masas iguales los cuerpos INTERCAMBIAN sus velocidades.",
         "Σp y la energía cinética K se conservan."]),
    2: ("2) Asteroide contra planeta en reposo (elástico, 1D)",
        ["El asteroide rebota; el planeta, enorme, adquiere poca velocidad pero",
         "SÍ adquiere momentum: Σp y K se conservan."]),
    3: ("3) Choque oblicuo 2D (billar elástico)",
        ["Masas iguales y uno en reposo: salen a 90° entre sí.",
         "Se conservan px y py por separado (y K)."]),
    4: ("4) Choque inelástico parcial (e = 0.5)",
        ["Σp se conserva pero K disminuye. Cambia e con las flechas ↑/↓ y",
         "pulsa R para repetir el experimento."]),
    5: ("5) Fusión: asteroide + planeta (perfectamente inelástico)",
        ["Los cuerpos se pegan: v_final = Σp / M. Se conserva Σp (vectorial),",
         "pero se pierde la máxima energía cinética posible."]),
    6: ("6) Cúmulo gravitacional con Σp = 0 (acreción)",
        ["La gravedad mutua es una fuerza interna: Σp se mantiene en 0 mientras",
         "los cuerpos se atraen y se fusionan. Prueba M y G."]),
}


# ================================  JUEGO  ====================================
class Juego:
    def __init__(self):
        pygame.init()
        pygame.display.set_caption(
            "Conservación del momentum lineal - colisiones de asteroides y planetas")
        self.pantalla = pygame.display.set_mode((ANCHO, ALTO))
        self.reloj = pygame.time.Clock()
        mono = "consolas,dejavusansmono,couriernew,monospace"
        self.f_tit = pygame.font.SysFont(mono, 19, bold=True)
        self.f_n = pygame.font.SysFont(mono, 13)
        self.f_p = pygame.font.SysFont(mono, 12)

        self.mundo = Mundo()
        self.cam = Camara()
        self.corriendo = True
        self.pausa = False
        self.factores = [1.0, 0.5, 0.25]
        self.idx_t = 0
        self.ver_v = False
        self.ver_p = True
        self.ver_traza = True
        self.ver_ayuda = True
        self.radio_nuevo = 2.0
        self.arrastre = None
        self.escenario = 1

        # fondo estrellado (se dibuja una sola vez)
        rnd = random.Random(3)
        self.fondo = pygame.Surface((ANCHO_SIM, ALTO))
        self.fondo.fill(FONDO)
        for _ in range(170):
            x, y = rnd.randrange(ANCHO_SIM), rnd.randrange(ALTO)
            b = rnd.randrange(70, 190)
            pygame.draw.circle(self.fondo, (b, b, min(255, b + 30)), (x, y), rnd.choice((1, 1, 1, 2)))

        self.cargar_escenario(1)

    # ------------------------------------------------------------ escenarios
    def cargar_escenario(self, n):
        self.escenario = n
        m = self.mundo
        m.reiniciar()
        m.gravedad = False
        m.paredes = False
        cy = CYM
        if n == 1:
            m.modo = ELASTICO
            m.agregar(Cuerpo(17, cy, 24, 0, 2.6))
            m.agregar(Cuerpo(69, cy, -12, 0, 2.6))
        elif n == 2:
            m.modo = ELASTICO
            m.agregar(Cuerpo(11, cy, 35, 0, 1.4))
            m.agregar(Cuerpo(56, cy, 0, 0, 5.0))
        elif n == 3:
            m.modo = ELASTICO
            m.agregar(Cuerpo(14, cy - 3, 26, 0, 2.2))
            m.agregar(Cuerpo(56, cy, 0, 0, 2.2))
        elif n == 4:
            m.modo = INELASTICO
            m.e = 0.5
            m.agregar(Cuerpo(20, cy, 10, 0, 3.4))
            m.agregar(Cuerpo(68, cy, -22, 0, 2.0))
        elif n == 5:
            m.modo = FUSION
            m.agregar(Cuerpo(56, cy + 2, -4, 0, 3.8))
            m.agregar(Cuerpo(13, cy - 7, 26, 3, 1.8))
        elif n == 6:
            m.modo = FUSION
            m.gravedad = True
            self._cumulo(16)
        m.fijar_referencia()
        m.registrar()

    def _cumulo(self, n):
        """Nube de cuerpos con rotación suave y momentum total nulo."""
        cuerpos = []
        intentos = 0
        while len(cuerpos) < n and intentos < 5000:
            intentos += 1
            ang = random.uniform(0, 2 * math.pi)
            rad = 26 * math.sqrt(random.random())
            x, y = CXM + rad * math.cos(ang), CYM + rad * math.sin(ang)
            r = random.uniform(0.7, 2.0)
            if any(math.hypot(x - c.x, y - c.y) < r + c.r + 0.5 for c in cuerpos):
                continue
            w = 0.25                                 # rad/s de rotación global
            vx = -w * (y - CYM) + random.gauss(0, 0.6)
            vy = w * (x - CXM) + random.gauss(0, 0.6)
            cuerpos.append(Cuerpo(x, y, vx, vy, r))
        M = sum(c.m for c in cuerpos)
        vcx = sum(c.m * c.vx for c in cuerpos) / M
        vcy = sum(c.m * c.vy for c in cuerpos) / M
        for c in cuerpos:                            # marco del centro de masa: Σp = 0
            c.vx -= vcx
            c.vy -= vcy
            self.mundo.agregar(c)

    # ------------------------------------------------------------- entradas
    def vref(self):
        """Velocidad del marco de la vista (0 en el marco del laboratorio)."""
        cm = self.mundo.centro_masa()
        if self.cam.seguir and cm:
            return (cm[2], cm[3])
        return (0.0, 0.0)

    def cambiar_radio(self, d):
        self.radio_nuevo = min(RADIO_MAX, max(RADIO_MIN, round(self.radio_nuevo + d, 2)))

    def lanzar(self, p0, p1):
        wx, wy = self.cam.a_mundo(*p0)
        vx = (p1[0] - p0[0]) * FACTOR_ARRASTRE
        vy = (p1[1] - p0[1]) * FACTOR_ARRASTRE
        v = math.hypot(vx, vy)
        if v > V_MAX:
            vx, vy = vx * V_MAX / v, vy * V_MAX / v
        vr = self.vref()
        self.mundo.agregar(Cuerpo(wx, wy, vx + vr[0], vy + vr[1], self.radio_nuevo))

    def eliminar_en(self, pos):
        wx, wy = self.cam.a_mundo(*pos)
        for c in reversed(self.mundo.cuerpos):
            if math.hypot(c.x - wx, c.y - wy) <= c.r:
                self.mundo.quitar(c)
                return

    def tecla(self, ev):
        k, m = ev.key, self.mundo
        if k == pygame.K_ESCAPE:
            self.corriendo = False
        elif k == pygame.K_SPACE:
            self.pausa = not self.pausa
        elif k == pygame.K_r:
            self.cargar_escenario(self.escenario)
        elif pygame.K_0 <= k <= pygame.K_6:
            self.cargar_escenario(k - pygame.K_0)
        elif k == pygame.K_m:
            m.modo = (m.modo + 1) % 3
        elif k == pygame.K_UP:
            m.modo = INELASTICO
            m.e = min(1.0, round(m.e + 0.05, 2))
        elif k == pygame.K_DOWN:
            m.modo = INELASTICO
            m.e = max(0.0, round(m.e - 0.05, 2))
        elif k == pygame.K_g:
            m.gravedad = not m.gravedad
        elif k == pygame.K_b:
            m.paredes = not m.paredes
            m.fijar_referencia()
        elif k == pygame.K_s:
            self.idx_t = (self.idx_t + 1) % len(self.factores)
        elif k == pygame.K_v:
            self.ver_v = not self.ver_v
        elif k == pygame.K_p:
            self.ver_p = not self.ver_p
        elif k == pygame.K_t:
            self.ver_traza = not self.ver_traza
        elif k == pygame.K_c:
            self.cam.alternar()
        elif k == pygame.K_h:
            self.ver_ayuda = not self.ver_ayuda
        elif ev.unicode == "+":
            self.cambiar_radio(0.2)
        elif ev.unicode == "-":
            self.cambiar_radio(-0.2)

    def procesar_eventos(self):
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                self.corriendo = False
            elif ev.type == pygame.KEYDOWN:
                self.tecla(ev)
            elif ev.type == pygame.MOUSEBUTTONDOWN:
                if ev.button == 1 and ev.pos[0] < ANCHO_SIM:
                    self.arrastre = ev.pos
                elif ev.button == 3 and ev.pos[0] < ANCHO_SIM:
                    self.eliminar_en(ev.pos)
                elif ev.button == 4:
                    self.cambiar_radio(0.2)
                elif ev.button == 5:
                    self.cambiar_radio(-0.2)
            elif ev.type == pygame.MOUSEBUTTONUP:
                if ev.button == 1 and self.arrastre is not None:
                    self.lanzar(self.arrastre, ev.pos)
                    self.arrastre = None

    # ------------------------------------------------------------ actualizar
    def actualizar(self):
        if not self.pausa:
            dt = (1.0 / FPS) * self.factores[self.idx_t] / SUBPASOS
            for _ in range(SUBPASOS):
                self.mundo.paso(dt)
            self.mundo.registrar()
        self.cam.actualizar(self.mundo)

    # --------------------------------------------------------------- dibujo
    def texto(self, s, x, y, fuente=None, color=BLANCO):
        self.pantalla.blit((fuente or self.f_n).render(s, True, color), (x, y))

    def flecha(self, color, p0, p1, grosor=2):
        if math.hypot(p1[0] - p0[0], p1[1] - p0[1]) < 4:
            return
        pygame.draw.line(self.pantalla, color, p0, p1, grosor)
        ang = math.atan2(p1[1] - p0[1], p1[0] - p0[0])
        for da in (math.pi - 0.45, math.pi + 0.45):
            q = (p1[0] + 10 * math.cos(ang + da), p1[1] + 10 * math.sin(ang + da))
            pygame.draw.line(self.pantalla, color, p1, q, grosor)

    def dibujar_cuerpo(self, c, sx, sy):
        r = max(2, int(c.r * ESCALA))
        sx, sy = int(sx), int(sy)
        oscuro = tuple(int(v * 0.45) for v in c.color)
        claro = tuple(min(255, int(v * 1.3) + 25) for v in c.color)
        medio = tuple((a + b) // 2 for a, b in zip(c.color, claro))
        p = self.pantalla
        pygame.draw.circle(p, oscuro, (sx, sy), r)
        pygame.draw.circle(p, c.color, (sx - int(r * 0.07), sy - int(r * 0.07)), max(1, int(r * 0.9)))
        pygame.draw.circle(p, medio, (sx - int(r * 0.28), sy - int(r * 0.28)), max(1, int(r * 0.38)))

    def dibujar_mundo(self):
        p, m, cam = self.pantalla, self.mundo, self.cam

        # paredes (si están activas)
        if m.paredes:
            x0, y0 = cam.a_pantalla(0, 0)
            x1, y1 = cam.a_pantalla(LARGO_M, ALTO_M)
            pygame.draw.rect(p, ROJO, (int(x0), int(y0), int(x1 - x0), int(y1 - y0)), 3)

        # estelas
        if self.ver_traza:
            for c in m.cuerpos:
                pts = []
                for (x, y, cx, cy) in c.traza:
                    if cam.seguir:       # trayectoria relativa al CM
                        pts.append(((x - cx) * ESCALA + CX0_PX, (y - cy) * ESCALA + CY0_PX))
                    else:
                        pts.append(cam.a_pantalla(x, y))
                n = len(pts)
                for k in range(1, n):
                    f = 0.15 + 0.6 * k / n
                    col = tuple(int(v * f) for v in c.color)
                    pygame.draw.line(p, col, pts[k - 1], pts[k], 1)

        # cuerpos
        vr = self.vref()
        pos = {}
        for c in m.cuerpos:
            sx, sy = cam.a_pantalla(c.x, c.y)
            pos[c.id] = (sx, sy)
            self.dibujar_cuerpo(c, sx, sy)
            nombre = self.f_p.render(c.nombre, True, BLANCO)
            p.blit(nombre, (int(sx - nombre.get_width() / 2), int(sy - c.r * ESCALA - 14)))

        # flechas de velocidad
        if self.ver_v:
            for c in m.cuerpos:
                sx, sy = pos[c.id]
                vx, vy = c.vx - vr[0], c.vy - vr[1]
                self.flecha(VERDE, (sx, sy), (sx + vx * 3.5, sy + vy * 3.5), 2)

        # flechas de momentum (misma escala para todas -> se pueden comparar)
        cm = m.centro_masa()
        if self.ver_p and cm:
            px_i = [(c.m * (c.vx - vr[0]), c.m * (c.vy - vr[1])) for c in m.cuerpos]
            Ptx = sum(q[0] for q in px_i)
            Pty = sum(q[1] for q in px_i)
            mx = max([math.hypot(*q) for q in px_i] + [math.hypot(Ptx, Pty), 1e-9])
            k = 80.0 / mx
            for c, q in zip(m.cuerpos, px_i):
                sx, sy = pos[c.id]
                self.flecha(NARANJA, (sx, sy), (sx + q[0] * k, sy + q[1] * k), 2)
            csx, csy = cam.a_pantalla(cm[0], cm[1])
            if math.hypot(Ptx, Pty) > 1e-6:
                self.flecha(BLANCO, (csx, csy), (csx + Ptx * k, csy + Pty * k), 4)
            else:
                self.texto("Σp = 0", int(csx) + 10, int(csy) + 10, self.f_p, BLANCO)

        # centro de masa
        if cm:
            csx, csy = cam.a_pantalla(cm[0], cm[1])
            csx, csy = int(csx), int(csy)
            pygame.draw.line(p, BLANCO, (csx - 7, csy), (csx + 7, csy), 1)
            pygame.draw.line(p, BLANCO, (csx, csy - 7), (csx, csy + 7), 1)
            pygame.draw.circle(p, BLANCO, (csx, csy), 9, 1)
            self.texto("CM", csx + 11, csy - 20, self.f_p, GRIS)

        # destellos de choque
        for x, y, edad in m.destellos:
            sx, sy = cam.a_pantalla(x, y)
            f = 1.0 - edad / 30.0
            col = (int(255 * f), int(200 * f), int(120 * f))
            pygame.draw.circle(p, col, (int(sx), int(sy)), int(8 + edad * 2.5), 2)

        # indicadores de cuerpos fuera de pantalla
        for c in m.cuerpos:
            sx, sy = pos[c.id]
            r = c.r * ESCALA
            if not (-r <= sx <= ANCHO_SIM + r and -r <= sy <= ALTO + r):
                ix = min(max(sx, 12), ANCHO_SIM - 12)
                iy = min(max(sy, 12), ALTO - 12)
                pygame.draw.circle(p, c.color, (int(ix), int(iy)), 6)
                pygame.draw.circle(p, BLANCO, (int(ix), int(iy)), 6, 1)

        self.dibujar_cursor()

    def dibujar_cursor(self):
        """Vista previa del próximo cuerpo y de la flecha de lanzamiento."""
        p = self.pantalla
        mx, my = pygame.mouse.get_pos()
        r_px = int(self.radio_nuevo * ESCALA)
        masa = DENSIDAD * self.radio_nuevo ** 3
        if self.arrastre is not None:
            x0, y0 = self.arrastre
            pygame.draw.circle(p, BLANCO, (int(x0), int(y0)), r_px, 1)
            self.flecha(BLANCO, (x0, y0), (mx, my), 2)
            v = min(V_MAX, math.hypot(mx - x0, my - y0) * FACTOR_ARRASTRE)
            self.texto(f"v = {v:.1f} m/s   m = {masa:.1f} kg", int(mx) + 12, int(my) + 8,
                       self.f_p, BLANCO)
        elif mx < ANCHO_SIM:
            pygame.draw.circle(p, GRIS, (mx, my), r_px, 1)
            self.texto(f"m = {masa:.1f} kg", mx + r_px + 6, my - 6, self.f_p, GRIS)

    def dibujar_superposiciones(self):
        """Títulos, avisos y ayuda sobre la zona de simulación."""
        p = self.pantalla
        titulo, notas = ESCENARIOS[self.escenario]
        self.texto(titulo, 12, 8, self.f_tit, BLANCO)
        for i, linea in enumerate(notas):
            self.texto(linea, 12, 34 + i * 16, self.f_n, GRIS)
        y = 34 + len(notas) * 16 + 4
        if self.cam.seguir:
            self.texto("VISTA: marco del centro de masa (flechas relativas al CM)",
                       12, y, self.f_n, CIAN)
            y += 16
        if self.pausa:
            self.texto("|| PAUSA", ANCHO_SIM - 110, 10, self.f_tit, AMARILLO)

        if self.ver_ayuda:
            lineas = [
                "CONTROLES",
                "Clic + arrastrar : lanzar un cuerpo (la flecha = velocidad)",
                "Clic derecho     : eliminar cuerpo",
                "Rueda  /  + -    : tamaño (masa) del próximo cuerpo",
                "0-6 escenarios   R reiniciar    ESPACIO pausa    S cámara lenta",
                "M tipo de choque (elástico / inelástico / fusión)",
                "Flechas ARRIBA/ABAJO : coeficiente de restitución e",
                "V velocidades  P momentos  T estelas  C marco del CM",
                "G gravedad (fuerza interna)   B paredes (fuerza externa)",
                "H ocultar ayuda   ESC salir",
            ]
            h = len(lineas) * 15 + 12
            panel = pygame.Surface((470, h), pygame.SRCALPHA)
            panel.fill((10, 12, 28, 200))
            p.blit(panel, (8, ALTO - h - 8))
            for i, s in enumerate(lineas):
                self.texto(s, 16, ALTO - h + 2 + i * 15, self.f_p,
                           AMARILLO if i == 0 else BLANCO)

    def dibujar_grafica(self, rect, titulo, curvas, modo):
        """curvas = [(valores, color, etiqueta)]; modo 'sim' (±R) o 'pos' (0..R)."""
        p, m = self.pantalla, self.mundo
        x, y, w, h = rect
        pygame.draw.rect(p, (9, 11, 24), rect)
        pygame.draw.rect(p, (50, 56, 84), rect, 1)
        self.texto(titulo, x + 5, y + 3, self.f_p, GRIS)
        # leyenda (de derecha a izquierda)
        cx = x + w - 6
        for _, color, etiqueta in reversed(curvas):
            s = self.f_p.render(etiqueta, True, color)
            cx -= s.get_width() + 8
            p.blit(s, (cx, y + 3))
        hist = m.hist
        if len(hist) < 2:
            return
        t0, t1 = hist[0][0], hist[-1][0]
        dur = max(t1 - t0, 1e-9)
        top, alto = y + 18, h - 22
        maxabs = max(1.0, max(abs(v) for datos, _, _ in curvas for v in datos)) * 1.15
        if modo == "sim":
            ymid = top + alto / 2
            def ypix(v): return ymid - v / maxabs * (alto / 2)
            pygame.draw.line(p, GRIS_OSC, (x + 1, ymid), (x + w - 2, ymid), 1)
        else:
            base = top + alto
            def ypix(v): return base - v / maxabs * alto
            pygame.draw.line(p, GRIS_OSC, (x + 1, base), (x + w - 2, base), 1)
        for tc in m.eventos:                       # marcas de choque
            if t0 <= tc <= t1:
                xc = x + 1 + (tc - t0) / dur * (w - 2)
                pygame.draw.line(p, (150, 70, 40), (xc, top), (xc, top + alto), 1)
        tiempos = [hh[0] for hh in hist]
        for datos, color, _ in curvas:
            pts = [(x + 1 + (t - t0) / dur * (w - 2), ypix(v)) for t, v in zip(tiempos, datos)]
            pygame.draw.lines(p, color, False, pts, 2)

    def dibujar_panel(self):
        p, m = self.pantalla, self.mundo
        x0 = ANCHO_SIM + 14
        pygame.draw.rect(p, PANEL, (ANCHO_SIM, 0, ANCHO - ANCHO_SIM, ALTO))
        pygame.draw.line(p, GRIS_OSC, (ANCHO_SIM, 0), (ANCHO_SIM, ALTO), 2)
        y = 8
        self.texto("MOMENTUM LINEAL   p = m v", x0, y, self.f_tit, BLANCO)
        y += 28

        if m.modo == ELASTICO:
            txt, col = "Choque: ELÁSTICO (e = 1.00)", VERDE
        elif m.modo == INELASTICO:
            txt, col = f"Choque: INELÁSTICO (e = {m.e:.2f})", AMARILLO
        else:
            txt, col = "Choque: PERFECTAMENTE INELÁSTICO (fusión)", NARANJA
        self.texto(txt, x0, y, self.f_n, col)
        y += 17
        self.texto(f"Gravedad: {'ON' if m.gravedad else 'off'}   "
                   f"Paredes: {'ON' if m.paredes else 'off'}   "
                   f"Tiempo: x{self.factores[self.idx_t]:g}", x0, y, self.f_n, GRIS)
        y += 17
        if m.paredes:
            self.texto("Paredes = fuerza EXTERNA: Σp cambia", x0, y, self.f_n, ROJO)
        y += 19

        # tabla de cuerpos
        self.texto(f"{'Cuerpo':<6}{'m[kg]':>6}{'vx':>7}{'vy':>7}{'px':>8}{'py':>8}",
                   x0, y, self.f_n, CIAN)
        y += 16
        pygame.draw.line(p, GRIS_OSC, (x0, y), (ANCHO - 14, y), 1)
        y += 3
        for c in m.cuerpos[:8]:
            self.texto(f"{c.nombre:<6}{c.m:6.1f}{c.vx:7.1f}{c.vy:7.1f}{c.px:8.1f}{c.py:8.1f}",
                       x0, y, self.f_n, BLANCO)
            y += 15
        if len(m.cuerpos) > 8:
            self.texto(f"... (+{len(m.cuerpos) - 8} cuerpos más)", x0, y, self.f_n, GRIS)
        y = 8 + 28 + 17 + 17 + 19 + 16 + 3 + 8 * 15 + 18   # posición fija de los totales

        # totales
        P = m.momento_total()
        pygame.draw.line(p, GRIS_OSC, (x0, y - 3), (ANCHO - 14, y - 3), 1)
        self.texto(f"Σm    = {m.masa_total():10.2f} kg", x0, y, self.f_n, BLANCO)
        y += 16
        self.texto(f"Σpx   = {P[0]:+10.3f} kg m/s", x0, y, self.f_n, NARANJA)
        y += 16
        self.texto(f"Σpy   = {P[1]:+10.3f} kg m/s", x0, y, self.f_n, NARANJA)
        y += 16
        self.texto(f"|Σp|  = {math.hypot(*P):10.3f} kg m/s", x0, y, self.f_n, NARANJA)
        y += 16
        self.texto(f"K tot = {m.energia_total():10.2f} J", x0, y, self.f_n, VERDE)
        y += 16
        self.texto(f"K disipada en choques = {m.k_disipada:9.2f} J", x0, y, self.f_n, AMARILLO)
        y += 16
        self.texto(f"|Σp - Σp esperado| = {m.desviacion_momento():.1e}", x0, y, self.f_n, CIAN)
        y += 22

        # último choque
        u = m.ultimo
        if u is None:
            self.texto("Último choque: (todavía ninguno)", x0, y, self.f_n, GRIS)
        else:
            self.texto(f"ÚLTIMO CHOQUE  t={u['t']:.2f}s  {u['a']}+{u['b']} [{u['tipo']}]",
                       x0, y, self.f_n, AMARILLO)
            y += 16
            self.texto(f"p antes  = ({u['pa'][0]:+9.3f}, {u['pa'][1]:+9.3f})", x0, y, self.f_n)
            y += 16
            self.texto(f"p después= ({u['pd'][0]:+9.3f}, {u['pd'][1]:+9.3f})", x0, y, self.f_n)
            y += 16
            dpx, dpy = u['pd'][0] - u['pa'][0], u['pd'][1] - u['pa'][1]
            self.texto(f"Δp = ({dpx:+.1e}, {dpy:+.1e})  -> conservado", x0, y, self.f_n, VERDE)
            y += 16
            self.texto(f"K antes = {u['ka']:8.2f} J   K después = {u['kd']:8.2f} J",
                       x0, y, self.f_n)
            y += 16
            dk = u['kd'] - u['ka']
            pct = dk / u['ka'] * 100 if u['ka'] > 0 else 0.0
            conservada = abs(dk) < 1e-9 * max(1.0, u['ka'])
            self.texto(f"ΔK = {0.0 if conservada else dk:+.2f} J ({0.0 if conservada else pct:+.1f} %)"
                       + ("  -> conservada" if conservada else "  -> disipada"),
                       x0, y, self.f_n, VERDE if conservada else NARANJA)

        # gráficas
        hist = m.hist
        gw = ANCHO - ANCHO_SIM - 28
        g2 = (x0, ALTO - 108, gw, 98)
        g1 = (x0, ALTO - 216, gw, 98)
        self.dibujar_grafica(
            g1, "Σp(t)  [kg m/s]",
            [([h[1] for h in hist], CIAN, "Σpx"),
             ([h[2] for h in hist], ROSA, "Σpy"),
             ([math.hypot(h[1], h[2]) for h in hist], BLANCO, "|Σp|")], "sim")
        self.dibujar_grafica(
            g2, "K(t)  [J]    (líneas naranjas = choques)",
            [([h[3] for h in hist], VERDE, "K")], "pos")

    def dibujar(self):
        p = self.pantalla
        p.set_clip(pygame.Rect(0, 0, ANCHO_SIM, ALTO))
        p.blit(self.fondo, (0, 0))
        self.dibujar_mundo()
        self.dibujar_superposiciones()
        p.set_clip(None)
        self.dibujar_panel()

    # ------------------------------------------------------------ bucle
    def ejecutar(self):
        try:
            while self.corriendo:
                self.procesar_eventos()
                self.actualizar()
                self.dibujar()
                pygame.display.flip()
                self.reloj.tick(FPS)
        finally:
            pygame.quit() # imprescindible en Spyder para poder re-ejecutar


def main():
    Juego().ejecutar()


if __name__ == "__main__":
    main()
