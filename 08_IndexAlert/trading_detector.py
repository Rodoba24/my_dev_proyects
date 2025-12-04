"""
Sistema de Detección de Rupturas y Rebotes en Índices Bursátiles
Fase 1: Obtención de datos y cálculo de indicadores
"""

import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime, timedelta

class TradingDetector:
    def __init__(self, ticker, period_days=60, interval='1h'):
        """
        Inicializa el detector de patrones
        
        Args:
            ticker: Símbolo del índice (ej: '^GSPC' para S&P 500)
            period_days: Días de datos históricos a obtener
            interval: Intervalo de tiempo ('1h', '1d', '5m', etc.)
        """
        self.ticker = ticker
        self.period_days = period_days
        self.interval = interval
        self.data = None
        
    def descargar_datos(self):
        """Descarga datos históricos del índice"""
        print(f"Descargando datos de {self.ticker}...")
        
        # Calcular fecha de inicio
        end_date = datetime.now()
        start_date = end_date - timedelta(days=self.period_days)
        
        # Descargar datos
        self.data = yf.download(
            self.ticker,
            start=start_date,
            end=end_date,
            interval=self.interval,
            progress=False
        )
        
        if self.data.empty:
            raise ValueError("No se pudieron descargar datos. Verifica el ticker y el intervalo.")
        
        # Aplanar columnas multi-nivel si es necesario
        if isinstance(self.data.columns, pd.MultiIndex):
            self.data.columns = self.data.columns.get_level_values(0)
        
        # Eliminar filas con valores NaN
        self.data = self.data.dropna()
        
        print(f"✓ Datos descargados: {len(self.data)} registros")
        print(f"  Rango: {self.data.index[0]} a {self.data.index[-1]}")
        return self.data
    
    def calcular_bandas_bollinger(self, window=20, num_std=2):
        """
        Calcula las Bandas de Bollinger
        
        Args:
            window: Períodos para la media móvil
            num_std: Número de desviaciones estándar
        """
        if self.data is None:
            raise ValueError("Primero debes descargar los datos")
        
        # Media móvil simple
        self.data['SMA'] = self.data['Close'].rolling(window=window).mean()
        
        # Desviación estándar
        std = self.data['Close'].rolling(window=window).std()
        
        # Banda superior (techo) e inferior (piso)
        self.data['Banda_Superior'] = self.data['SMA'] + (std * num_std)
        self.data['Banda_Inferior'] = self.data['SMA'] - (std * num_std)
        
        print(f"✓ Bandas de Bollinger calculadas (ventana={window}, std={num_std})")
        return self.data
    
    def detectar_rupturas(self, umbral_ruptura=0.001):
        """
        Detecta rupturas del techo y piso
        
        Args:
            umbral_ruptura: Porcentaje mínimo para considerar una ruptura (0.001 = 0.1%)
        """
        if 'Banda_Superior' not in self.data.columns:
            raise ValueError("Primero debes calcular las bandas")
        
        # Detectar ruptura del techo (precio > banda superior)
        self.data['Ruptura_Techo'] = self.data['Close'] > self.data['Banda_Superior'] * (1 + umbral_ruptura)
        
        # Detectar ruptura del piso (precio < banda inferior)
        self.data['Ruptura_Piso'] = self.data['Close'] < self.data['Banda_Inferior'] * (1 - umbral_ruptura)
        
        num_rupturas_techo = self.data['Ruptura_Techo'].sum()
        num_rupturas_piso = self.data['Ruptura_Piso'].sum()
        
        print(f"✓ Rupturas detectadas:")
        print(f"  - Techo: {num_rupturas_techo}")
        print(f"  - Piso: {num_rupturas_piso}")
        
        return self.data
    
    def graficar(self, ultimos_dias=14):
        """
        Genera gráfico con precio, bandas y rupturas
        
        Args:
            ultimos_dias: Número de días a mostrar en el gráfico
        """
        if self.data is None:
            raise ValueError("No hay datos para graficar")
        
        # Filtrar últimos días
        if self.interval == '1h':
            ultimos_registros = ultimos_dias * 24  # Aproximadamente
        else:
            ultimos_registros = ultimos_dias
        
        data_reciente = self.data.tail(ultimos_registros)
        
        # Crear figura
        plt.figure(figsize=(15, 8))
        
        # Graficar precio
        plt.plot(data_reciente.index, data_reciente['Close'], 
                label='Precio', color='black', linewidth=1.5)
        
        # Graficar bandas
        if 'Banda_Superior' in data_reciente.columns:
            plt.plot(data_reciente.index, data_reciente['Banda_Superior'], 
                    label='Techo (Banda Superior)', color='red', 
                    linestyle='--', alpha=0.7)
            plt.plot(data_reciente.index, data_reciente['Banda_Inferior'], 
                    label='Piso (Banda Inferior)', color='green', 
                    linestyle='--', alpha=0.7)
            plt.plot(data_reciente.index, data_reciente['SMA'], 
                    label='Media Móvil', color='blue', 
                    linestyle=':', alpha=0.5)
        
        # Marcar rupturas
        if 'Ruptura_Techo' in data_reciente.columns:
            rupturas_techo = data_reciente[data_reciente['Ruptura_Techo']]
            rupturas_piso = data_reciente[data_reciente['Ruptura_Piso']]
            
            plt.scatter(rupturas_techo.index, rupturas_techo['Close'], 
                       color='red', marker='v', s=100, 
                       label='Ruptura Techo', zorder=5)
            plt.scatter(rupturas_piso.index, rupturas_piso['Close'], 
                       color='green', marker='^', s=100, 
                       label='Ruptura Piso', zorder=5)
        
        plt.title(f'{self.ticker} - Detección de Rupturas (Últimos {ultimos_dias} días)', 
                 fontsize=14, fontweight='bold')
        plt.xlabel('Fecha')
        plt.ylabel('Precio')
        plt.legend(loc='best')
        plt.grid(True, alpha=0.3)
        plt.tight_layout()
        plt.xticks(rotation=45)
        plt.show()
    
    def mostrar_resumen(self):
        """Muestra un resumen estadístico de los datos"""
        if self.data is None:
            return
        
        print("\n" + "="*60)
        print("RESUMEN DE DATOS")
        print("="*60)
        print(f"\nÍndice: {self.ticker}")
        print(f"Registros totales: {len(self.data)}")
        print(f"\nEstadísticas del precio de cierre:")
        print(self.data['Close'].describe())
        
        if 'Ruptura_Techo' in self.data.columns:
            print(f"\nRupturas detectadas:")
            print(f"  Techo: {self.data['Ruptura_Techo'].sum()}")
            print(f"  Piso: {self.data['Ruptura_Piso'].sum()}")


# ============================================================================
# EJEMPLO DE USO
# ============================================================================

if __name__ == "__main__":
    print("="*60)
    print("SISTEMA DE DETECCIÓN DE RUPTURAS Y REBOTES")
    print("="*60)
    print()
    
    # 1. Crear el detector
    # Índices disponibles: '^GSPC' (S&P 500), '^IXIC' (NASDAQ), '^DJI' (Dow Jones)
    # Para índices mexicanos: '^MXX' (IPC México)
    detector = TradingDetector(
        ticker='^GSPC',      # S&P 500
        period_days=60,      # Últimos 60 días
        interval='1h'        # Datos por hora
    )
    
    # 2. Descargar datos
    detector.descargar_datos()
    
    # 3. Calcular Bandas de Bollinger
    detector.calcular_bandas_bollinger(window=20, num_std=2)
    
    # 4. Detectar rupturas
    detector.detectar_rupturas(umbral_ruptura=0.001)
    
    # 5. Mostrar resumen
    detector.mostrar_resumen()
    
    # 6. Graficar
    detector.graficar(ultimos_dias=14)
    
    print("\n✓ Proceso completado exitosamente")