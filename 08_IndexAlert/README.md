## OBJETIVOS DEL PROYECTO

**Objetivo General:**
Desarrollar un sistema automatizado de análisis técnico que detecte rupturas y rebotes en niveles de soporte/resistencia de índices bursátiles.

**Objetivos Específicos por Etapa:**
1. **Etapa 1 (Actual):** Sistema de alertas simuladas que detecte patrones de ruptura-rebote usando datos históricos
2. **Etapa 2:** Implementar alertas en tiempo real
3. **Etapa 3:** Sistema de trading automatizado (paper trading primero)
4. **Etapa 4:** Integración de modelos de ML para optimización

## PLAN DE ETAPAS

### **ETAPA 1: Simulación y Detección de Patrones (Inicio)**

**Fase 1.1 - Obtención de Datos (2-3 semanas)**
- Investigar APIs gratuitas de datos bursátiles (Yahoo Finance, Alpha Vantage)
- Aprender a usar librerías: `yfinance`, `pandas`, `numpy`
- Descargar datos históricos del índice que te interese
- Crear un dataset limpio con precios OHLC (Open, High, Low, Close)

**Fase 1.2 - Cálculo de Indicadores (1-2 semanas)**
- Implementar el cálculo del indicador que define tu techo/piso (¿Bandas de Bollinger? ¿Soportes/resistencias? ¿Otro?)
- Usar librerías como `ta-lib` o `pandas-ta` para indicadores técnicos
- Visualizar los datos con `matplotlib` o `plotly`

**Fase 1.3 - Detección de Patrones (2-3 semanas)**
- Programar la lógica para detectar:
  - Ruptura del techo → caída → rebote al alza
  - Ruptura del piso → subida → rebote a la baja
- Definir parámetros (% de ruptura, timeframe del rebote, etc.)
- Validar con casos históricos conocidos

**Fase 1.4 - Sistema de Alertas Simuladas (1 semana)**
- Crear logs/reportes cuando se detecte el patrón
- Implementar backtesting básico
- Medir efectividad del sistema

## CÓMO EMPEZAR (PASOS CONCRETOS)

**Semana 1-2: Fundamentos**
1. Instala el entorno: Python 3.9+, Jupyter Notebook
2. Instala librerías básicas:
   ```
   pip install yfinance pandas numpy matplotlib
   ```
3. Practica descargando datos de un índice (ej: S&P 500, NASDAQ)
4. Crea gráficas básicas de precios

**Primera tarea práctica:**
Hacer un script que descargue los últimos 2 años del índice que elijas y grafique el precio de cierre.

## PREGUNTAS PARA AFINAR EL PLAN

1. **¿Qué índice específico te interesa?** (S&P 500, NASDAQ, algún índice mexicano como el IPC?)
2. **¿Qué indicador técnico defines como "techo/piso"?** (Bandas de Bollinger, niveles de Fibonacci, promedios móviles, resistencias/soportes manuales?)
3. **¿Qué timeframe prefieres analizar?** (datos diarios, por hora, 15 minutos?)
4. **¿Cuánto tiempo semanal puedes dedicar al proyecto?**

Sobre tu duda de **análisis de imagen vs datos directos**: definitivamente es mejor usar datos directos mediante APIs. Analizar imágenes sería innecesariamente complejo y menos preciso. Las APIs te dan los datos numéricos exactos que necesitas.

¿Te parece bien esta estructura? ¿Quieres que profundicemos en alguna fase específica o prefieres que te ayude con el código inicial para descargar datos?