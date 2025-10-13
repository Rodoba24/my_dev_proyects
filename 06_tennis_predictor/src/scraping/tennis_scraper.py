"""
Scraper de prueba para Tennis Explorer
Guarda este archivo como: src/scraping/tennis_scraper.py
"""

import requests
import pandas as pd
import time
from bs4 import BeautifulSoup
from datetime import datetime
import os
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class TennisExplorerScraper:
    """
    Scraper básico para Tennis Explorer - Versión de prueba
    """
    
    def __init__(self, delay=3):
        self.base_url = "https://www.tennisexplorer.com"
        self.delay = delay
        self.session = requests.Session()
        
        # Headers para parecer un navegador real
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive'
        })
    
    def test_connection(self):
        """
        Prueba la conexión básica
        """
        print("🔗 Probando conexión con Tennis Explorer...")
        
        try:
            response = self.session.get(self.base_url, timeout=10)
            if response.status_code == 200:
                print("✅ Conexión exitosa!")
                return True
            else:
                print(f"❌ Error de conexión: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Error de conexión: {e}")
            return False
    
    def get_atp_results_page(self):
        """
        Obtiene la página principal de resultados ATP
        """
        print("📊 Obteniendo página de resultados ATP...")
        
        # URL de resultados ATP recientes
        url = f"{self.base_url}/results/"
        
        try:
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            
            print(f"✅ Página obtenida (tamaño: {len(response.content)} bytes)")
            time.sleep(self.delay)
            
            return response
            
        except Exception as e:
            print(f"❌ Error obteniendo página: {e}")
            return None
    
    def extract_basic_data(self, html_content):
        """
        Extrae datos básicos de cualquier tabla que encuentre
        """
        print("🔍 Analizando contenido de la página...")
        
        soup = BeautifulSoup(html_content, 'html.parser')
        all_data = []
        
        # Buscar todas las tablas
        tables = soup.find_all('table')
        print(f"📋 Encontradas {len(tables)} tablas")
        
        for i, table in enumerate(tables):
            print(f"\n🔍 Analizando tabla {i+1}...")
            
            rows = table.find_all('tr')
            print(f"   Filas encontradas: {len(rows)}")
            
            table_data = []
            
            for j, row in enumerate(rows[:20]):  # Limitar a 20 filas por tabla
                cells = row.find_all(['td', 'th'])
                
                if len(cells) >= 3:  # Al menos 3 columnas
                    cell_texts = [cell.get_text(strip=True) for cell in cells]
                    
                    # Filtrar filas vacías
                    if any(text for text in cell_texts):
                        row_data = {
                            'table_index': i,
                            'row_index': j,
                            'cell_count': len(cells),
                            'raw_row': ' | '.join(cell_texts),
                            'scraped_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                        }
                        
                        # Agregar celdas individuales como columnas
                        for k, text in enumerate(cell_texts[:8]):  # Máximo 8 columnas
                            row_data[f'cell_{k}'] = text
                        
                        table_data.append(row_data)
            
            print(f"   Datos extraídos: {len(table_data)} filas")
            all_data.extend(table_data)
        
        print(f"\n✅ Total de datos extraídos: {len(all_data)} filas")
        return all_data
    
    def save_test_data(self, data, filename='tennis_test_data.csv'):
        """
        Guarda los datos de prueba
        """
        if not data:
            print("⚠️  No hay datos para guardar")
            return None
        
        df = pd.DataFrame(data)
        
        # Asegurar que existe el directorio
        os.makedirs('data/raw', exist_ok=True)
        filepath = f'data/raw/{filename}'
        
        # Guardar CSV
        df.to_csv(filepath, index=False, encoding='utf-8')
        
        print(f"\n💾 Datos guardados en: {filepath}")
        print(f"📊 Registros guardados: {len(df)}")
        
        return df
    
    def analyze_scraped_data(self, df):
        """
        Análisis rápido de los datos extraídos
        """
        print("\n" + "="*60)
        print("📊 ANÁLISIS DE DATOS EXTRAÍDOS")
        print("="*60)
        
        print(f"\n📈 INFORMACIÓN GENERAL:")
        print(f"- Total registros: {len(df)}")
        print(f"- Columnas: {len(df.columns)}")
        print(f"- Tablas analizadas: {df['table_index'].nunique()}")
        
        print(f"\n📋 COLUMNAS DISPONIBLES:")
        for col in df.columns:
            non_null = df[col].notna().sum()
            print(f"- {col:<15}: {non_null:4d} valores válidos ({non_null/len(df)*100:.1f}%)")
        
        print(f"\n🔍 MUESTRA DE DATOS RAW:")
        sample_rows = df[df['raw_row'].str.len() > 20].head(5)  # Filas con contenido
        
        for i, row in sample_rows.iterrows():
            print(f"{i+1:2d}. Tabla {row['table_index']} | {row['raw_row'][:80]}...")
        
        print(f"\n🎾 BUSCAR PATRONES DE PARTIDOS:")
        # Buscar filas que podrían ser partidos de tenis
        potential_matches = df[
            df['raw_row'].str.contains('-', na=False) &  # Scores tienen '-'
            (df['cell_count'] >= 4) &  # Al menos 4 columnas
            (df['raw_row'].str.len() > 15)  # Contenido mínimo
        ]
        
        print(f"- Filas que podrían ser partidos: {len(potential_matches)}")
        
        if len(potential_matches) > 0:
            print(f"\n🏆 EJEMPLOS DE POSIBLES PARTIDOS:")
            for i, row in potential_matches.head(3).iterrows():
                print(f"{i+1}. {row['raw_row']}")
    
    def run_test_scraping(self):
        """
        Ejecuta una prueba completa de scraping
        """
        print("🚀 INICIANDO PRUEBA DE SCRAPING")
        print("="*50)
        
        # 1. Probar conexión
        if not self.test_connection():
            return None
        
        # 2. Obtener página
        response = self.get_atp_results_page()
        if not response:
            return None
        
        # 3. Extraer datos
        data = self.extract_basic_data(response.content)
        if not data:
            print("❌ No se extrajeron datos")
            return None
        
        # 4. Guardar datos
        df = self.save_test_data(data)
        
        # 5. Analizar resultados
        if df is not None:
            self.analyze_scraped_data(df)
        
        return df

def main():
    """
    Función principal para probar el scraper
    """
    print("🎾 TENNIS EXPLORER SCRAPER - PRUEBA INICIAL")
    print("="*60)
    
    # Crear scraper
    scraper = TennisExplorerScraper(delay=3)
    
    # Ejecutar prueba
    result_df = scraper.run_test_scraping()
    
    if result_df is not None:
        print("\n🎉 ¡PRUEBA COMPLETADA EXITOSAMENTE!")
        print("\n📋 PRÓXIMOS PASOS:")
        print("1. Revisa el archivo: data/raw/tennis_test_data.csv")
        print("2. Identifica qué datos parecen partidos de tenis")
        print("3. Ajustaremos el scraper para extraer mejor información")
        
        print(f"\n📁 ARCHIVOS CREADOS:")
        print(f"- data/raw/tennis_test_data.csv ({len(result_df)} registros)")
        
    else:
        print("\n❌ La prueba no fue exitosa")
        print("💡 POSIBLES SOLUCIONES:")
        print("- Verificar conexión a internet")
        print("- Tennis Explorer podría estar bloqueando requests")
        print("- Probar con delay más largo")

if __name__ == "__main__":
    main()