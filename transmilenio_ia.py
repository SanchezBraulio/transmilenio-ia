import heapq
from typing import Dict, List, Tuple, Callable, Any, Optional

# Base de conocimiento (hechos y reglas)
# ------------------------------------------------------------
class Hecho:
    def __init__(self, predicado: str, *args):
        self.predicado = predicado
        self.args = args

    def __eq__(self, other):
        return self.predicado == other.predicado and self.args == other.args

    def __hash__(self):
        return hash((self.predicado, self.args))

    def __repr__(self):
        return f"{self.predicado}({', '.join(map(str, self.args))})"

class Regla:
    def __init__(self, nombre: str, premisas: List[Callable], accion: Callable):
        self.nombre = nombre
        self.premisas = premisas   # lista de funciones que devuelven bool
        self.accion = accion       # función que modifica el contexto

class BaseConocimiento:
    def __init__(self):
        self.hechos = set()
        self.reglas = []

    def agregar_hecho(self, hecho: Hecho):
        self.hechos.add(hecho)

    def agregar_regla(self, regla: Regla):
        self.reglas.append(regla)

    def aplicar_reglas(self, contexto: Dict[str, Any]) -> Dict[str, Any]:
        for regla in self.reglas:
            if all(premisa(contexto) for premisa in regla.premisas):
                resultado = regla.accion(contexto)
                if resultado:
                    contexto.update(resultado)
        return contexto

# Sistema de transporte específico para Bogotá
# ------------------------------------------------------------
class SistemaTransmilenio:
    def __init__(self, base_conocimiento: BaseConocimiento):
        self.bc = base_conocimiento
        self.grafo = {}  # nodo -> list of (vecino, tiempo_base, tipo, linea)
        # Atributo para controlar hora punta globalmente (ejemplo)
        self.hora_punta_global = False

    def agregar_conexion(self, estacion1: str, estacion2: str, linea: str,
                         tiempo_minutos: int, tipo: str = "troncal"):
        """Agrega una conexión bidireccional entre estaciones."""
        self.grafo.setdefault(estacion1, []).append((estacion2, tiempo_minutos, tipo, linea))
        self.grafo.setdefault(estacion2, []).append((estacion1, tiempo_minutos, tipo, linea))
        self.bc.agregar_hecho(Hecho("conexion", estacion1, estacion2, linea, tiempo_minutos, tipo))

    def calcular_costo(self, desde: str, hacia: str, tipo: str, linea: str,
                       tipo_anterior: Optional[str] = None, linea_anterior: Optional[str] = None) -> float:
        # Obtener tiempo base
        tiempo_base = None
        for (vecino, t, tp, l) in self.grafo.get(desde, []):
            if vecino == hacia and tp == tipo and l == linea:
                tiempo_base = t
                break
        if tiempo_base is None:
            return float('inf')

        contexto = {
            "desde": desde,
            "hacia": hacia,
            "tipo": tipo,
            "linea": linea,
            "tipo_anterior": tipo_anterior,
            "linea_anterior": linea_anterior,
            "tiempo_base": tiempo_base,
            "costo_extra": 0.0,
            "hora_punta": self.hora_punta_global  # control externo
        }
        self.bc.aplicar_reglas(contexto)
        return contexto["tiempo_base"] + contexto["costo_extra"]

    def mejor_ruta(self, origen: str, destino: str) -> Tuple[List[str], float]:
        # Estado: (estacion, tipo_servicio, linea)
        dist = {(origen, None, None): 0}
        prev = {}
        pq = [(0, origen, None, None, None)]  # (costo, estacion, tipo, linea, prev_estacion)

        while pq:
            costo_act, estacion, tipo_act, linea_act, _ = heapq.heappop(pq)
            estado_act = (estacion, tipo_act, linea_act)
            if estado_act not in dist or costo_act > dist[estado_act]:
                continue
            if estacion == destino:
                # Reconstruir ruta (solo estaciones)
                ruta = []
                estado = estado_act
                while estado:
                    ruta.append(estado[0])
                    estado = prev.get(estado)
                ruta.reverse()
                return ruta, costo_act

            for vecino, t_base, tipo_vec, linea_vec in self.grafo.get(estacion, []):
                costo_transicion = self.calcular_costo(estacion, vecino, tipo_vec, linea_vec,
                                                       tipo_act, linea_act)
                nuevo_costo = costo_act + costo_transicion
                estado_siguiente = (vecino, tipo_vec, linea_vec)
                if nuevo_costo < dist.get(estado_siguiente, float('inf')):
                    dist[estado_siguiente] = nuevo_costo
                    prev[estado_siguiente] = estado_act
                    heapq.heappush(pq, (nuevo_costo, vecino, tipo_vec, linea_vec, estacion))

        return [], float('inf')

# Reglas específicas para Bogotá (Capítulo 3)
# ------------------------------------------------------------
def regla_transbordo(contexto):
    """Penalización por cambiar de servicio (troncal↔alimentador) o de línea."""
    tipo_act = contexto.get("tipo")
    tipo_ant = contexto.get("tipo_anterior")
    linea_act = contexto.get("linea")
    linea_ant = contexto.get("linea_anterior")
    extra = 0
    if tipo_ant is not None:
        if tipo_act != tipo_ant:
            extra = 6  # minutos por cambio de troncal a alimentador o viceversa
        elif linea_act != linea_ant:
            extra = 4  # cambio dentro de la misma modalidad
    contexto["costo_extra"] = contexto.get("costo_extra", 0) + extra
    return {"costo_extra": contexto["costo_extra"]}

def regla_hora_punta_bogota(contexto):
    """Hora pico en Bogotá: incremento del 30% sobre tiempo base."""
    if contexto.get("hora_punta", False):
        contexto["costo_extra"] += 0.3 * contexto["tiempo_base"]
    return {"costo_extra": contexto["costo_extra"]}

def regla_espera_alimentador(contexto):
    """Tiempo de espera adicional en paradas alimentadoras."""
    if contexto.get("tipo") == "alimentador" and contexto.get("tipo_anterior") == "troncal":
        contexto["costo_extra"] += 3  # espera típica en portal
    return {"costo_extra": contexto["costo_extra"]}

# Construcción de la red de Bogotá (ejemplo realista)
# ------------------------------------------------------------
def construir_red_bogota():
    bc = BaseConocimiento()

    # Agregar reglas
    bc.agregar_regla(Regla("Transbordo", [lambda ctx: True], regla_transbordo))
    bc.agregar_regla(Regla("HoraPunta", [lambda ctx: ctx.get("hora_punta", False)], regla_hora_punta_bogota))
    bc.agregar_regla(Regla("EsperaAlimentador", [lambda ctx: True], regla_espera_alimentador))

    sistema = SistemaTransmilenio(bc)

    # ----- Líneas troncales (TransMilenio) -----
    # Línea A (Caracas - Norte)
    sistema.agregar_conexion("Portal Norte", "Calle 142", "A", 4, "troncal")
    sistema.agregar_conexion("Calle 142", "Calle 106", "A", 3, "troncal")
    sistema.agregar_conexion("Calle 106", "Calle 72", "A", 4, "troncal")
    sistema.agregar_conexion("Calle 72", "Calle 45", "A", 3, "troncal")
    sistema.agregar_conexion("Calle 45", "Calle 26", "A", 3, "troncal")
    sistema.agregar_conexion("Calle 26", "Tercer Milenio", "A", 2, "troncal")
    sistema.agregar_conexion("Tercer Milenio", "Universidad Nacional", "A", 2, "troncal")
    sistema.agregar_conexion("Universidad Nacional", "Calle 19", "A", 2, "troncal")
    sistema.agregar_conexion("Calle 19", "Avenida Jiménez", "A", 2, "troncal")
    sistema.agregar_conexion("Avenida Jiménez", "Museo Nacional", "A", 2, "troncal")
    sistema.agregar_conexion("Museo Nacional", "Tunal", "A", 10, "troncal")

    # Línea B (Suba - NQS)
    sistema.agregar_conexion("Portal Suba", "Suba Calle 100", "B", 5, "troncal")
    sistema.agregar_conexion("Suba Calle 100", "Suba Calle 72", "B", 4, "troncal")
    sistema.agregar_conexion("Suba Calle 72", "Rionegro", "B", 3, "troncal")
    sistema.agregar_conexion("Rionegro", "Avenida El Dorado", "B", 4, "troncal")
    sistema.agregar_conexion("Avenida El Dorado", "Avenida Jiménez", "B", 3, "troncal")

    # Línea C (Américas)
    sistema.agregar_conexion("Portal Américas", "Banderas", "C", 5, "troncal")
    sistema.agregar_conexion("Banderas", "Granja", "C", 4, "troncal")
    sistema.agregar_conexion("Granja", "Avenida Jiménez", "C", 6, "troncal")

    # ----- Alimentadores (ejemplo) -----
    sistema.agregar_conexion("Portal Norte", "La Estancia", "Alimentador N1", 8, "alimentador")
    sistema.agregar_conexion("La Estancia", "San José Norte", "Alimentador N1", 5, "alimentador")
    sistema.agregar_conexion("Portal Suba", "Suba Compartir", "Alimentador S1", 7, "alimentador")
    sistema.agregar_conexion("Portal Américas", "Patio Bonito", "Alimentador A1", 6, "alimentador")

    # ----- Rutas zonales SITP (ejemplo simplificado) -----
    sistema.agregar_conexion("Avenida Jiménez", "Centro", "SITP Z1", 3, "zonal")
    sistema.agregar_conexion("Centro", "La Macarena", "SITP Z1", 4, "zonal")
    sistema.agregar_conexion("Tunal", "Ciudad Bolívar", "SITP Z2", 12, "zonal")

    return sistema

# Función de consulta interactiva
# ------------------------------------------------------------
def consultar_ruta(sistema: SistemaTransmilenio, origen: str, destino: str, hora_punta: bool = False):
    print(f"\n🔍 Consulta en Bogotá: {origen} → {destino}")
    if hora_punta:
        print("   ⏱️  Modo: Hora punta activa (+30% tiempos)")
    sistema.hora_punta_global = hora_punta
    ruta, tiempo = sistema.mejor_ruta(origen, destino)
    if ruta:
        print(f"✅ Mejor ruta: {' → '.join(ruta)}")
        print(f"⏱️  Tiempo total: {tiempo:.1f} minutos")
    else:
        print("❌ No hay ruta disponible")
    return ruta, tiempo

# Ejecución principal y pruebas
# ------------------------------------------------------------
if __name__ == "__main__":
    sistema = construir_red_bogota()

    # Prueba 1: misma línea troncal
    consultar_ruta(sistema, "Portal Norte", "Universidad Nacional", hora_punta=False)

    # Prueba 2: transbordo entre líneas A y B (en Avenida Jiménez)
    consultar_ruta(sistema, "Portal Suba", "Calle 26", hora_punta=False)

    # Prueba 3: origen en alimentador
    consultar_ruta(sistema, "La Estancia", "Avenida Jiménez", hora_punta=False)

    # Prueba 4: hora punta activa
    consultar_ruta(sistema, "Portal Norte", "Universidad Nacional", hora_punta=True)

    # Prueba 5: ruta combinando troncal + alimentador + zonal
    consultar_ruta(sistema, "San José Norte", "Centro", hora_punta=False)