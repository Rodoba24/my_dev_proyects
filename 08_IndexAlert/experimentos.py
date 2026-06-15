"""
Script para experimentar con diferentes combinaciones de parámetros
y comparar resultados visualmente
"""

import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime, timedelta

class TradingDetector:
    def __init__(self, ticker, period_days=60, interval='1h'):
        self.ticker = ticker
        self.period_days = period_days
        self.interval = interval
        self.data = None
        
    def descargar_datos(self):
        print(f"Descargando datos de {self.ticker}...")
        end_date = datetime.now()
        start_date = end_date - timedelta(days=self.period_days)
        
        self.data = yf.download(
            self.ticker,
            start=start_date,
            end=end_date,
            interval=self.interval,
            progress=False
        )
        
        if self.data.empty:
            raise ValueError("No se pudieron descargar datos.")
        
        if isinstance(self.data.columns, pd.MultiIndex):
            self.data.columns = self.data.columns.get_level_values(0)
        
        self.data = self.data.dropna()
        print(f"✓ Datos descargados: {len(self.data)} registros")
        return self.data
    
    def calcular_bandas_bollinger(self, window=20, num_std=2):
        if self.data is None:
            raise ValueError("Primero debes descargar los datos")
        
        self.data['SMA'] = self.data['Close'].rolling(window=window).mean()
        std = self.data['Close'].rolling(window=window).std()
        self.data['Banda_Superior'] = self.data['SMA'] + (std * num_std)
        self.data['Banda_Inferior'] = self.data['SMA'] - (std * num_std)
        
        return self.data
    
    def detectar_rupturas(self, umbral_ruptura=0.001):
        if 'Banda_Superior' not in self.data.columns:
            raise ValueError("Primero debes calcular las bandas")
        
        self.data['Ruptura_Techo'] = self.data['Close'] > self.data['Banda_Superior'] * (1 + umbral_ruptura)
        self.data['Ruptura_Piso'] = self.data['Close'] < self.data['Banda_Inferior'] * (1 - umbral_ruptura)
        
        return self.data
    
    def obtener_metricas(self):
        """Calcula métricas para comparación"""
        if self.data is None:
            return None
        
        metricas = {
            'total_registros': len(self.data),
            'rupturas_techo': self.data['Ruptura_Techo'].sum() if 'Ruptura_Techo' in self.data.columns else 0,
            'rupturas_piso': self.data['Ruptura_Piso'].sum() if 'Ruptura_Piso' in self.data.columns else 0,
            'total_rupturas': 0,
            'precio_promedio': self.data['Close'].mean(),
            'volatilidad': self.data['Close'].std()
        }
        metricas['total_rupturas'] = metricas['rupturas_techo'] + metricas['rupturas_piso']
        metricas['tasa_rupturas'] = (metricas['total_rupturas'] / metricas['total_registros']) * 100
        
        return metricas


class ExperimentadorParametros:
    """Clase para experimentar con diferentes combinaciones de parámetros"""
    
    def __init__(self, ticker='^GSPC', period_days=60, interval='1h'):
        self.ticker = ticker
        self.period_days = period_days
        self.interval = interval
        self.resultados = []
        
    def ejecutar_experimento(self, configuraciones):
        """
        Ejecuta múltiples experimentos con diferentes configuraciones
        
        Args:
            configuraciones: Lista de diccionarios con parámetros a probar
        """
        print("="*70)
        print("INICIANDO EXPERIMENTOS")
        print("="*70)
        print()
        
        for i, config in enumerate(configuraciones, 1):
            print(f"\n[Experimento {i}/{len(configuraciones)}]")
            print(f"  window={config['window']}, std={config['num_std']}, umbral={config['umbral']}")
            
            # Crear detector y ejecutar
            detector = TradingDetector(self.ticker, self.period_days, self.interval)
            detector.descargar_datos()
            detector.calcular_bandas_bollinger(
                window=config['window'], 
                num_std=config['num_std']
            )
            detector.detectar_rupturas(umbral_ruptura=config['umbral'])
            
            # Obtener métricas
            metricas = detector.obtener_metricas()
            
            # Guardar resultados
            resultado = {
                'nombre': config.get('nombre', f'Exp {i}'),
                'config': config,
                'metricas': metricas,
                'detector': detector
            }
            self.resultados.append(resultado)
            
            print(f"  ✓ Rupturas detectadas: {metricas['total_rupturas']} "
                  f"(Techo: {metricas['rupturas_techo']}, Piso: {metricas['rupturas_piso']})")
        
        print("\n" + "="*70)
        print("EXPERIMENTOS COMPLETADOS")
        print("="*70)
        
    def mostrar_resumen(self):
        """Muestra una tabla comparativa de resultados"""
        if not self.resultados:
            print("No hay resultados para mostrar")
            return
        
        print("\n" + "="*90)
        print("RESUMEN COMPARATIVO DE EXPERIMENTOS")
        print("="*90)
        print()
        
        # Encabezado
        print(f"{'Experimento':<20} {'Window':<8} {'Std':<6} {'Umbral':<8} "
              f"{'Techo':<7} {'Piso':<7} {'Total':<7} {'Tasa %':<8}")
        print("-" * 90)
        
        # Datos
        for res in self.resultados:
            config = res['config']
            metricas = res['metricas']
            print(f"{res['nombre']:<20} "
                  f"{config['window']:<8} "
                  f"{config['num_std']:<6} "
                  f"{config['umbral']:<8.4f} "
                  f"{metricas['rupturas_techo']:<7} "
                  f"{metricas['rupturas_piso']:<7} "
                  f"{metricas['total_rupturas']:<7} "
                  f"{metricas['tasa_rupturas']:<8.2f}")
        
        print("="*90)
        print("\n💡 Tasa % = (Total Rupturas / Total Registros) × 100")
        print("   - Tasa alta: Sistema sensible, más señales")
        print("   - Tasa baja: Sistema conservador, señales selectivas")
        
    def graficar_comparacion(self, ultimos_dias=14):
        """Genera gráficos comparativos de todos los experimentos"""
        if not self.resultados:
            print("No hay resultados para graficar")
            return
        
        num_experimentos = len(self.resultados)
        
        # Calcular dimensiones del grid
        cols = 2
        rows = (num_experimentos + 1) // 2
        
        fig, axes = plt.subplots(rows, cols, figsize=(18, 5*rows))
        fig.suptitle(f'Comparación de Experimentos - {self.ticker}', 
                     fontsize=16, fontweight='bold', y=0.995)
        
        # Aplanar axes si es necesario
        if num_experimentos == 1:
            axes = [axes]
        elif rows == 1:
            axes = axes
        else:
            axes = axes.flatten()
        
        for idx, resultado in enumerate(self.resultados):
            ax = axes[idx]
            detector = resultado['detector']
            config = resultado['config']
            metricas = resultado['metricas']
            
            # Filtrar datos recientes
            if self.interval == '1h':
                ultimos_registros = ultimos_dias * 24
            else:
                ultimos_registros = ultimos_dias
            
            data_reciente = detector.data.tail(ultimos_registros)
            
            # Graficar precio
            ax.plot(data_reciente.index, data_reciente['Close'], 
                   label='Precio', color='black', linewidth=1.5, zorder=3)
            
            # Graficar bandas
            ax.plot(data_reciente.index, data_reciente['Banda_Superior'], 
                   label='Techo', color='red', linestyle='--', alpha=0.7, zorder=2)
            ax.plot(data_reciente.index, data_reciente['Banda_Inferior'], 
                   label='Piso', color='green', linestyle='--', alpha=0.7, zorder=2)
            ax.plot(data_reciente.index, data_reciente['SMA'], 
                   label='Media', color='blue', linestyle=':', alpha=0.5, zorder=1)
            
            # Marcar rupturas
            rupturas_techo = data_reciente[data_reciente['Ruptura_Techo']]
            rupturas_piso = data_reciente[data_reciente['Ruptura_Piso']]
            
            ax.scatter(rupturas_techo.index, rupturas_techo['Close'], 
                      color='red', marker='v', s=80, label='Rup. Techo', zorder=5)
            ax.scatter(rupturas_piso.index, rupturas_piso['Close'], 
                      color='green', marker='^', s=80, label='Rup. Piso', zorder=5)
            
            # Título con configuración
            titulo = (f"{resultado['nombre']}\n"
                     f"W={config['window']}, σ={config['num_std']}, "
                     f"U={config['umbral']:.3f} | "
                     f"Rupturas: {metricas['total_rupturas']}")
            ax.set_title(titulo, fontsize=10, fontweight='bold')
            ax.set_xlabel('Fecha', fontsize=8)
            ax.set_ylabel('Precio', fontsize=8)
            ax.legend(loc='best', fontsize=7)
            ax.grid(True, alpha=0.3)
            ax.tick_params(axis='x', rotation=45, labelsize=7)
            ax.tick_params(axis='y', labelsize=8)
        
        # Ocultar subplots vacíos si los hay
        for idx in range(num_experimentos, len(axes)):
            axes[idx].set_visible(False)
        
        plt.tight_layout()
        plt.show()
    
    def recomendar_mejor_configuracion(self):
        """Analiza y recomienda la mejor configuración según criterios"""
        if not self.resultados:
            print("No hay resultados para analizar")
            return
        
        print("\n" + "="*70)
        print("ANÁLISIS Y RECOMENDACIONES")
        print("="*70)
        
        # Ordenar por diferentes criterios
        por_total = sorted(self.resultados, 
                          key=lambda x: x['metricas']['total_rupturas'], 
                          reverse=True)
        por_tasa = sorted(self.resultados, 
                         key=lambda x: x['metricas']['tasa_rupturas'], 
                         reverse=True)
        
        print("\n📊 Configuración MÁS SENSIBLE (más rupturas):")
        config_sensible = por_total[0]
        print(f"  {config_sensible['nombre']}: {config_sensible['metricas']['total_rupturas']} rupturas")
        print(f"  → window={config_sensible['config']['window']}, "
              f"std={config_sensible['config']['num_std']}, "
              f"umbral={config_sensible['config']['umbral']}")
        
        print("\n🎯 Configuración MÁS CONSERVADORA (menos rupturas):")
        config_conservadora = por_total[-1]
        print(f"  {config_conservadora['nombre']}: {config_conservadora['metricas']['total_rupturas']} rupturas")
        print(f"  → window={config_conservadora['config']['window']}, "
              f"std={config_conservadora['config']['num_std']}, "
              f"umbral={config_conservadora['config']['umbral']}")
        
        print("\n💡 RECOMENDACIÓN:")
        print("  - Si buscas muchas oportunidades (day trading): Usa la configuración sensible")
        print("  - Si buscas señales de alta calidad (swing trading): Usa la conservadora")
        print("  - Para empezar: Prueba una configuración intermedia")
        print("="*70)


# ============================================================================
# EXPERIMENTOS PREDEFINIDOS
# ============================================================================

if __name__ == "__main__":
    print("="*70)
    print("SISTEMA DE EXPERIMENTACIÓN DE PARÁMETROS")
    print("="*70)
    print()
    
    # Configurar experimentos
    experimentador = ExperimentadorParametros(
        ticker='^GSPC',
        period_days=60,
        interval='1h'
    )
    
    # Definir configuraciones a probar
    configuraciones = [
        # Experimento 1: Estándar (baseline)
        {
            'nombre': 'Estándar',
            'window': 20,
            'num_std': 2.0,
            'umbral': 0.001
        },
        # Experimento 2: Conservador
        {
            'nombre': 'Conservador',
            'window': 30,
            'num_std': 2.5,
            'umbral': 0.005
        },
        # Experimento 3: Agresivo
        {
            'nombre': 'Agresivo',
            'window': 10,
            'num_std': 1.5,
            'umbral': 0.0
        },
        # Experimento 4: Medio-Conservador
        {
            'nombre': 'Medio-Conservador',
            'window': 25,
            'num_std': 2.0,
            'umbral': 0.003
        },
        # Experimento 5: Bandas Estrechas
        {
            'nombre': 'Bandas Estrechas',
            'window': 20,
            'num_std': 1.5,
            'umbral': 0.001
        },
        # Experimento 6: Bandas Amplias
        {
            'nombre': 'Bandas Amplias',
            'window': 20,
            'num_std': 3.0,
            'umbral': 0.001
        }
    ]
    
    # Ejecutar experimentos
    experimentador.ejecutar_experimento(configuraciones)
    
    # Mostrar resultados
    experimentador.mostrar_resumen()
    
    # Recomendaciones
    experimentador.recomendar_mejor_configuracion()
    
    # Graficar comparación
    print("\nGenerando gráficos comparativos...")
    experimentador.graficar_comparacion(ultimos_dias=14)
    
    print("\n✓ Análisis completado")