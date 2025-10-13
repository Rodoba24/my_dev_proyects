"""
Scraper mejorado para Tennis Explorer
Soluciona: rutas, tablas innecesarias, y celdas combinadas

Guarda como: src/scraping/improved_tennis_scraper.py
"""

import requests
import pandas as pd
import time
from bs4 import BeautifulSoup
from datetime import datetime
import os
import logging
from pathlib import Path
import sys

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ImprovedTennisExplorerScraper:
    """
    Scraper mejorado que resuelve los problemas identificados
    """
    
    def __init__(self, delay=3):
        # Configurar rutas correctas
        self.project_root = self.find_project_root()
        self.data_dir = self.project_root / 'data' / 'raw'
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        self.base_url = "https://www.tennisexplorer.com"
        self.delay = delay
        self.session = requests.Session()
        
        # Headers mejorados
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Referer': 'https://www.tennisexplorer.com/'
        })
        
        print(f"📁 Directorio de datos: {self.data_dir}")
    
    def find_project_root(self):
        """
        Encuentra la raíz del proyecto (donde está la carpeta 'data')
        """
        current_path = Path.cwd()
        
        # Buscar hacia arriba hasta encontrar la carpeta 'data'
        for path in [current_path] + list(current_path.parents):
            if (path / 'data').exists():
                print(f"✅ Proyecto encontrado en: {path}")
                return path
        
        # Si no encuentra, usar directorio actual y crear estructura
        print(f"⚠️  Usando directorio actual: {current_path}")
        return current_path
    
    def get_page_safe(self, url, description="página"):
        """
        Obtiene página con mejor manejo de errores
        """
        print(f"🌐 Obteniendo {description}: {url}")
        
        try:
            response = self.session.get(url, timeout=15)
            response.raise_for_status()
            
            print(f"✅ {description} obtenida (tamaño: {len(response.content):,} bytes)")
            time.sleep(self.delay)
            
            return response
            
        except requests.RequestException as e:
            print(f"❌ Error obteniendo {description}: {e}")
            return None
    
    def is_match_table(self, table):
        """
        Determina si una tabla contiene partidos de tenis
        """
        # Buscar indicadores de que es una tabla de partidos
        table_text = table.get_text().lower()
        
        # Palabras clave que indican partidos
        match_keywords = [
            'vs', 'result', 'score', 'set', 'winner', 'loser',
            'round', 'opponent', 'match', 'game'
        ]
        
        # Palabras que indican que NO es tabla de partidos
        exclude_keywords = [
            'calendar', 'upcoming', 'schedule', 'tournament list',
            'ranking', 'points', 'prize money', 'draw size'
        ]
        
        # Verificar estructura típica de tabla de partidos
        rows = table.find_all('tr')
        if len(rows) < 2:  # Muy pocas filas
            return False
        
        # Buscar scores típicos (números con guiones)
        has_scores = any('-' in cell.get_text() and any(c.isdigit() for c in cell.get_text()) 
                        for row in rows for cell in row.find_all(['td', 'th']))
        
        # Verificar palabras clave
        has_match_keywords = any(keyword in table_text for keyword in match_keywords)
        has_exclude_keywords = any(keyword in table_text for keyword in exclude_keywords)
        
        # Decisión final
        is_match = (has_scores or has_match_keywords) and not has_exclude_keywords
        
        return is_match
    
    def extract_match_tables(self, soup):
        """
        Extrae solo las tablas que contienen partidos
        """
        all_tables = soup.find_all('table')
        print(f"📊 Total de tablas encontradas: {len(all_tables)}")
        
        match_tables = []
        
        for i, table in enumerate(all_tables):
            if self.is_match_table(table):
                match_tables.append((i, table))
                print(f"✅ Tabla {i+1}: Identificada como tabla de partidos")
            else:
                print(f"❌ Tabla {i+1}: Descartada (no contiene partidos)")
        
        print(f"🎾 Tablas de partidos encontradas: {len(match_tables)}")
        return match_tables
    
    def handle_merged_cells(self, table):
        """
        Maneja celdas combinadas (rowspan/colspan)
        """
        rows = table.find_all('tr')
        processed_rows = []
        
        # Almacenar información de celdas que se extienden a múltiples filas
        carried_cells = {}  # {column_index: (content, remaining_rows)}
        
        for row_idx, row in enumerate(rows):
            cells = row.find_all(['td', 'th'])
            processed_cells = []
            
            col_idx = 0
            for cell in cells:
                # Verificar si hay celdas "arrastradas" de filas anteriores
                while col_idx in carried_cells:
                    content, remaining = carried_cells[col_idx]
                    processed_cells.append(content)
                    
                    if remaining > 1:
                        carried_cells[col_idx] = (content, remaining - 1)
                    else:
                        del carried_cells[col_idx]
                    
                    col_idx += 1
                
                # Procesar celda actual
                cell_text = cell.get_text(strip=True)
                processed_cells.append(cell_text)
                
                # Verificar si la celda se extiende a múltiples filas
                rowspan = int(cell.get('rowspan', 1))
                if rowspan > 1:
                    carried_cells[col_idx] = (cell_text, rowspan - 1)
                
                col_idx += 1
            
            processed_rows.append(processed_cells)
        
        return processed_rows
    
    def extract_matches_from_table(self, table, table_index):
        """
        Extrae partidos de una tabla específica manejando celdas combinadas
        """
        print(f"🔍 Procesando tabla {table_index + 1}...")
        
        processed_rows = self.handle_merged_cells(table)
        matches = []
        
        for row_idx, cells in enumerate(processed_rows[1:], 1):  # Saltar header
            if len(cells) >= 3 and any(cell for cell in cells):  # Al menos 3 columnas con contenido
                
                match_data = {
                    'table_index': table_index,
                    'row_index': row_idx,
                    'scraped_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }
                
                # Asignar celdas a columnas específicas
                for i, cell in enumerate(cells[:10]):  # Máximo 10 columnas
                    match_data[f'col_{i}'] = cell
                
                # Intentar identificar información específica
                match_data.update(self.parse_match_info(cells))
                
                matches.append(match_data)
        
        print(f"   Extraídos: {len(matches)} partidos potenciales")
        return matches
    
    def parse_match_info(self, cells):
        """
        Intenta identificar información específica del partido
        """
        parsed = {
            'time': '',
            'player1': '',
            'player2': '',
            'score': '',
            'tournament': '',
            'round': ''
        }
        
        # Buscar patrones específicos en las celdas
        for cell in cells:
            cell_lower = cell.lower()
            
            # Buscar hora (formato HH:MM)
            if ':' in cell and len(cell) <= 8 and any(c.isdigit() for c in cell):
                if not parsed['time']:  # Solo tomar la primera hora encontrada
                    parsed['time'] = cell
            
            # Buscar score (contiene números y guiones)
            elif '-' in cell and len(cell.split('-')) >= 2:
                numbers = [part for part in cell.split() if any(c.isdigit() for c in part)]
                if len(numbers) >= 2:
                    parsed['score'] = cell
            
            # Buscar nombres de jugadores (texto largo sin números)
            elif len(cell) > 5 and not any(c.isdigit() for c in cell) and cell != '':
                if not parsed['player1']:
                    parsed['player1'] = cell
                elif not parsed['player2'] and cell != parsed['player1']:
                    parsed['player2'] = cell
            
            # Buscar round (palabras típicas)
            elif any(keyword in cell_lower for keyword in ['r1', 'r2', 'r3', 'qf', 'sf', 'final', 'round']):
                parsed['round'] = cell
        
        return parsed
    
    def scrape_tennis_matches(self):
        """
        Proceso principal de scraping mejorado
        """
        print("🚀 INICIANDO SCRAPING MEJORADO")
        print("=" * 60)
        
        # Probar diferentes URLs de Tennis Explorer
        test_urls = [
            f"{self.base_url}/results/",
            f"{self.base_url}/atp-men/",
            f"{self.base_url}/live-scores/"
        ]
        
        all_matches = []
        
        for url in test_urls:
            print(f"\n🌐 Probando URL: {url}")
            
            response = self.get_page_safe(url, f"página de {url.split('/')[-2]}")
            if not response:
                continue
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Extraer solo tablas de partidos
            match_tables = self.extract_match_tables(soup)
            
            if not match_tables:
                print("⚠️  No se encontraron tablas de partidos en esta URL")
                continue
            
            # Procesar cada tabla de partidos
            for table_idx, table in match_tables:
                matches = self.extract_matches_from_table(table, table_idx)
                
                # Agregar información de la fuente
                for match in matches:
                    match['source_url'] = url
                    match['source_page'] = url.split('/')[-2] or 'main'
                
                all_matches.extend(matches)
            
            if all_matches:
                break  # Si encontramos datos, no necesitamos probar más URLs
        
        return all_matches
    
    def save_improved_data(self, matches, filename='tennis_matches_improved.csv'):
        """
        Guarda los datos en la ubicación correcta
        """
        if not matches:
            print("⚠️  No hay datos para guardar")
            return None
        
        df = pd.DataFrame(matches)
        
        # Usar la ruta correcta del proyecto
        filepath = self.data_dir / filename
        
        # Guardar CSV
        df.to_csv(filepath, index=False, encoding='utf-8')
        
        print(f"\n💾 ✅ Datos guardados correctamente en: {filepath}")
        print(f"📊 Total de registros: {len(df)}")
        
        return df
    
    def analyze_improved_data(self, df):
        """
        Análisis mejorado de los datos extraídos
        """
        print("\n" + "=" * 60)
        print("📊 ANÁLISIS DE DATOS MEJORADOS")
        print("=" * 60)
        
        print(f"\n📈 INFORMACIÓN GENERAL:")
        print(f"- Total registros: {len(df)}")
        print(f"- Páginas analizadas: {df['source_page'].nunique()}")
        print(f"- Tablas procesadas: {df['table_index'].nunique()}")
        
        # Análizar calidad de la extracción
        print(f"\n🎾 CALIDAD DE EXTRACCIÓN:")
        quality_metrics = {
            'Con hora': df['time'].notna().sum(),
            'Con jugadores': (df['player1'].notna() & df['player2'].notna()).sum(),
            'Con score': df['score'].notna().sum(),
            'Con round': df['round'].notna().sum()
        }
        
        for metric, count in quality_metrics.items():
            percentage = count / len(df) * 100
            print(f"- {metric:<15}: {count:4d} registros ({percentage:5.1f}%)")
        
        # Mostrar mejores ejemplos
        print(f"\n🏆 MEJORES EJEMPLOS EXTRAÍDOS:")
        
        # Buscar registros con más información completa
        complete_matches = df[
            df['player1'].notna() & 
            df['player2'].notna() & 
            (df['score'].notna() | df['time'].notna())
        ]
        
        if len(complete_matches) > 0:
            for i, (_, row) in enumerate(complete_matches.head(5).iterrows(), 1):
                time_str = row['time'] if pd.notna(row['time']) else 'Sin hora'
                score_str = row['score'] if pd.notna(row['score']) else 'Sin score'
                
                print(f"{i}. {time_str} | {row['player1']} vs {row['player2']} | {score_str}")
        else:
            print("   No se encontraron partidos completos")
        
        return quality_metrics

def main():
    """
    Función principal mejorada
    """
    print("🎾 TENNIS EXPLORER SCRAPER - VERSIÓN MEJORADA")
    print("=" * 70)
    
    # Crear scraper mejorado
    scraper = ImprovedTennisExplorerScraper(delay=3)
    
    # Ejecutar scraping
    matches = scraper.scrape_tennis_matches()
    
    if matches:
        # Guardar datos
        df = scraper.save_improved_data(matches)
        
        # Analizar resultados
        if df is not None:
            quality_metrics = scraper.analyze_improved_data(df)
            
            print(f"\n🎉 ¡SCRAPING COMPLETADO!")
            print(f"\n📋 ARCHIVOS CREADOS:")
            print(f"- {scraper.data_dir}/tennis_matches_improved.csv")
            
            print(f"\n💡 PRÓXIMOS PASOS:")
            if quality_metrics['Con jugadores'] > 0:
                print("✅ 1. Datos de jugadores extraídos - Continuar con análisis")
                print("✅ 2. Crear features para machine learning")
                print("✅ 3. Comenzar análisis exploratorio")
            else:
                print("⚠️  1. Ajustar selectores para mejor extracción")
                print("⚠️  2. Probar con URLs más específicas")
                print("⚠️  3. Investigar estructura del sitio")
    
    else:
        print("\n❌ No se obtuvieron datos")
        print("💡 SUGERENCIAS:")
        print("- Verificar conectividad")
        print("- Tennis Explorer podría haber cambiado su estructura")
        print("- Considerar usar APIs alternativas")

if __name__ == "__main__":
    main()