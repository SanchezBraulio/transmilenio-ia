import heapq
import matplotlib.pyplot as plt
import networkx as nx
from typing import Dict, List, Tuple, Callable, Any, Optional

# Base de conocimiento, hechos y reglas---------------------------------------------

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
        self.premisas = premisas
        self.accion = accion

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

# Sistema de transporte - Bogotá--------------------------------------------------

class SistemaTransmilenio:
    def __init__(self, base_conocimiento: BaseConocimiento):
        self.bc = base_conocimiento
        self.grafo = {}  # nodo -> list of (vecino, tiempo, tipo, linea)
        self.hora_punta_global = False

    def agregar_conexion(self, estacion1: str, estacion2: str, linea: str,
                         tiempo_minutos: int, tipo: str = "troncal"):
        self.grafo.setdefault(estacion1, []).append((estacion2, tiempo_minutos, tipo, linea))
        self.grafo.setdefault(estacion2, []).append((estacion1, tiempo_minutos, tipo, linea))
        self.bc.agregar_hecho(Hecho("conexion", estacion1, estacion2, linea, tiempo_minutos, tipo))

    def calcular_costo(self, desde: str, hacia: str, tipo: str, linea: str,
                       tipo_anterior: Optional[str] = None, linea_anterior: Optional[str] = None) -> float:
        tiempo_base = None
        for (vecino, t, tp, l) in self.grafo.get(desde, []):
            if vecino == hacia and tp == tipo and l == linea:
                tiempo_base = t
                break
        if tiempo_base is None:
            return float('inf')
        contexto = {
            "desde": desde, "hacia": hacia, "tipo": tipo, "linea": linea,
            "tipo_anterior": tipo_anterior, "linea_anterior": linea_anterior,
            "tiempo_base": tiempo_base, "costo_extra": 0.0,
            "hora_punta": self.hora_punta_global
        }
        self.bc.aplicar_reglas(contexto)
        return contexto["tiempo_base"] + contexto["costo_extra"]

    def mejor_ruta(self, origen: str, destino: str) -> Tuple[List[str], float]:
        dist = {(origen, None, None): 0.0}
        prev = {}
        pq = [(0.0, origen, None, None, "")]
        while pq:
            costo_act, estacion, tipo_act, linea_act, _ = heapq.heappop(pq)
            estado_act = (estacion, tipo_act, linea_act)
            if estado_act not in dist or costo_act > dist[estado_act]:
                continue
            if estacion == destino:
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

# Reglas específicas (Bogotá)-----------------------------------------------------

def regla_transbordo(contexto):
    tipo_act, tipo_ant = contexto.get("tipo"), contexto.get("tipo_anterior")
    linea_act, linea_ant = contexto.get("linea"), contexto.get("linea_anterior")
    extra = 0
    if tipo_ant is not None:
        if tipo_act != tipo_ant:
            extra = 6
        elif linea_act != linea_ant:
            extra = 4
    contexto["costo_extra"] = contexto.get("costo_extra", 0) + extra
    return {"costo_extra": contexto["costo_extra"]}

def regla_hora_punta_bogota(contexto):
    if contexto.get("hora_punta", False):
        contexto["costo_extra"] += 0.3 * contexto["tiempo_base"]
    return {"costo_extra": contexto["costo_extra"]}

def regla_espera_alimentador(contexto):
    if contexto.get("tipo") == "alimentador" and contexto.get("tipo_anterior") == "troncal":
        contexto["costo_extra"] += 3
    return {"costo_extra": contexto["costo_extra"]}

# Construcción de la red de Bogotá-------------------------------------------------

def construir_red_bogota():
    bc = BaseConocimiento()
    bc.agregar_regla(Regla("Transbordo", [lambda ctx: True], regla_transbordo))
    bc.agregar_regla(Regla("HoraPunta", [lambda ctx: ctx.get("hora_punta", False)], regla_hora_punta_bogota))
    bc.agregar_regla(Regla("EsperaAlimentador", [lambda ctx: True], regla_espera_alimentador))
    sistema = SistemaTransmilenio(bc)

    # Línea A -----------------------
    sistema.agregar_conexion("Portal Norte", "Calle 142", "A", 4)
    sistema.agregar_conexion("Calle 142", "Calle 106", "A", 3)
    sistema.agregar_conexion("Calle 106", "Calle 72", "A", 4)
    sistema.agregar_conexion("Calle 72", "Calle 45", "A", 3)
    sistema.agregar_conexion("Calle 45", "Calle 26", "A", 3)
    sistema.agregar_conexion("Calle 26", "Tercer Milenio", "A", 2)
    sistema.agregar_conexion("Tercer Milenio", "Universidad Nacional", "A", 2)
    sistema.agregar_conexion("Universidad Nacional", "Calle 19", "A", 2)
    sistema.agregar_conexion("Calle 19", "Avenida Jiménez", "A", 2)
    sistema.agregar_conexion("Avenida Jiménez", "Museo Nacional", "A", 2)
    sistema.agregar_conexion("Museo Nacional", "Tunal", "A", 10)
    # Línea B -----------------------
    sistema.agregar_conexion("Portal Suba", "Suba Calle 100", "B", 5)
    sistema.agregar_conexion("Suba Calle 100", "Suba Calle 72", "B", 4)
    sistema.agregar_conexion("Suba Calle 72", "Rionegro", "B", 3)
    sistema.agregar_conexion("Rionegro", "Avenida El Dorado", "B", 4)
    sistema.agregar_conexion("Avenida El Dorado", "Avenida Jiménez", "B", 3)
    # Línea C -----------------------
    sistema.agregar_conexion("Portal Américas", "Banderas", "C", 5)
    sistema.agregar_conexion("Banderas", "Granja", "C", 4)
    sistema.agregar_conexion("Granja", "Avenida Jiménez", "C", 6)
    # Alimentadores -----------------
    sistema.agregar_conexion("Portal Norte", "La Estancia", "Alimentador N1", 8, "alimentador")
    sistema.agregar_conexion("La Estancia", "San José Norte", "Alimentador N1", 5, "alimentador")
    sistema.agregar_conexion("Portal Suba", "Suba Compartir", "Alimentador S1", 7, "alimentador")
    sistema.agregar_conexion("Portal Américas", "Patio Bonito", "Alimentador A1", 6, "alimentador")
    # Zonales SITP ------------------
    sistema.agregar_conexion("Avenida Jiménez", "Centro", "SITP Z1", 3, "zonal")
    sistema.agregar_conexion("Centro", "La Macarena", "SITP Z1", 4, "zonal")
    sistema.agregar_conexion("Tunal", "Ciudad Bolívar", "SITP Z2", 12, "zonal")
    return sistema

# Visualización gráfica de la ruta--------------------------------------------------

def visualizar_ruta(sistema: SistemaTransmilenio, ruta: List[str], titulo: str):
    """Dibuja el grafo de estaciones y resalta la ruta encontrada."""
    G = nx.Graph()
    # Agregar todas las conexiones del grafo
    for estacion, vecinos in sistema.grafo.items():
        for vecino, _, _, _ in vecinos:
            G.add_edge(estacion, vecino)
    
    pos = nx.spring_layout(G, k=0.5, seed=42)  # layout para visualización
    plt.figure(figsize=(14, 10))
    
    # Dibujar todos los nodos y aristas
    nx.draw_networkx_nodes(G, pos, node_color='lightblue', node_size=800)
    nx.draw_networkx_edges(G, pos, edge_color='gray', width=1, alpha=0.5)
    
    # Resaltar la ruta
    if len(ruta) > 1:
        edges_ruta = [(ruta[i], ruta[i+1]) for i in range(len(ruta)-1)]
        nx.draw_networkx_edges(G, pos, edgelist=edges_ruta, edge_color='red', width=3)
        nx.draw_networkx_nodes(G, pos, nodelist=ruta, node_color='orange', node_size=900)
        # Nodo origen y destino especiales
        nx.draw_networkx_nodes(G, pos, nodelist=[ruta[0]], node_color='green', node_size=1000)
        nx.draw_networkx_nodes(G, pos, nodelist=[ruta[-1]], node_color='red', node_size=1000)
    
    nx.draw_networkx_labels(G, pos, font_size=8)
    plt.title(titulo, fontsize=14)
    plt.axis('off')
    plt.tight_layout()
    plt.show()

# Función de consulta con visualización-------------------------------------------------

def consultar_y_visualizar(sistema: SistemaTransmilenio, origen: str, destino: str, hora_punta: bool = False):
    print(f"\n🔍 Consulta: {origen} → {destino}" + (" (Hora punta activa)" if hora_punta else ""))
    sistema.hora_punta_global = hora_punta
    ruta, tiempo = sistema.mejor_ruta(origen, destino)
    if ruta:
        print(f"✅ Ruta: {' → '.join(ruta)}")
        print(f"⏱️ Tiempo: {tiempo:.1f} minutos")
        visualizar_ruta(sistema, ruta, f"Ruta de {origen} a {destino} (Tiempo: {tiempo:.1f} min)")
    else:
        print("❌ No hay ruta disponible")
    return ruta, tiempo

# Ejecución principal con ejemplos-------------------------------------------------------

if __name__ == "__main__":
    sistema = construir_red_bogota()
    
# Probar ruta----------------------------------------------------------------------------
    consultar_y_visualizar(sistema, "La Estancia", "Patio Bonito", hora_punta=False)
"""
Lista completa de estaciones (Selecciona un punto A y un punto B):
1. Portal Norte
2. Calle 142
3. Calle 106
4. Calle 72
5. Calle 45
6. Calle 26
7. Tercer Milenio
8. Universidad Nacional
9. Calle 19
10. Avenida Jiménez
11. Museo Nacional
12. Tunal
13. Portal Suba
14. Suba Calle 100
15. Suba Calle 72
16. Rionegro
17. Avenida El Dorado
18. Portal Américas
19. Banderas
20. Granja
21. La Estancia
22. San José Norte
23. Suba Compartir
24. Patio Bonito
25. Centro
26. La Macarena
27. Ciudad Bolívar
"""