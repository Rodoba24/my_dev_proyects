"""
Scraper Final para Tennis Explorer
Incorpora todos los ajustes identificados

Guarda como: src/scraping/final_tennis_scraper.py
"""

import requests
import pandas as pd
import time
from bs4 import BeautifulSoup
from datetime import datetime
import os
import logging
from pathlib import Path
import re

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class FinalTennisExplorerScraper:
    """
    Scraper final optimizado con todos los ajustes
    """
    
    def __init__(self, delay=3):
        # Configurar rutas
        self.project_root = self.find_project_root()
        self.data_dir = self.project_root / 'data' / 'raw'
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        self.base_url = "https://www.tennisexplorer.com"
        self.delay = delay
        self.session = requests.Session()
        
        # Headers optimizados
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Referer': 'https://www.tennisexplorer.com/'
        })
        
        print(f"📁 Guardando datos en: {self.data_dir}")
    
    def find_project_root(self):
        """Encuentra la raíz del proyecto"""
        current_path = Path.cwd()
        
        for path in [current_path] + list(current_path.parents):
            if (path / 'data').exists():
                return path
        
        return current_path
    
    def get_page_safe(self, url, description="página"):
        """Obtiene página con manejo de errores"""
        print(f"🌐 Obteniendo {description}...")
        
        try:
            response = self.session.get(url, timeout=15)
            response.raise_for_status()
            
            print(f"✅ {description} obtenida ({len(response.content):,} bytes)")
            time.sleep(self.delay)
            return response
            
        except Exception as e:
            print(f"❌ Error: {e}")
            return None
    
    def is_main_matches_table(self, table):
        """
        Identifica específicamente la tabla PRINCIPAL de partidos
        (no listas de torneos ni otras tablas)
        """
        table_text = table.get_text().lower()
        
        # Indicadores de tabla principal de partidos
        strong_match_indicators = [
            'vs', 'result', 'score', 'finished', 'live', 'US Open'
        ]
        
        # Indicadores de tablas que NO queremos
        exclude_indicators = [
            'tournament list', 'upcoming tournaments', 'calendar',
            'ranking', 'prize money', 'points', 'draws'
        ]
        
        # Verificar estructura de partidos (debe tener scores)
        rows = table.find_all('tr')
        if len(rows) < 3:  # Muy pocas filas para ser tabla de partidos
            return False
        
        # Buscar scores reales (formato típico: 6-4, 7-6, etc.)
        score_pattern = re.compile(r'\d+-\d+')
        has_tennis_scores = any(
            score_pattern.search(cell.get_text())
            for row in rows
            for cell in row.find_all(['td', 'th'])
        )
        
        # Verificar palabras clave
        has_strong_indicators = any(indicator in table_text for indicator in strong_match_indicators)
        has_exclude_indicators = any(indicator in table_text for indicator in exclude_indicators)
        
        # Debe tener scores de tenis Y palabras clave, pero NO indicadores de exclusión
        is_main_table = has_tennis_scores and has_strong_indicators and not has_exclude_indicators
        
        return is_main_table
    
    def extract_main_table(self, soup):
        """
        Extrae SOLO la tabla principal de partidos
        """
        all_tables = soup.find_all('table')
        print(f"📊 Analizando {len(all_tables)} tablas...")
        
        main_tables = []
        
        for i, table in enumerate(all_tables):
            if self.is_main_matches_table(table):
                print(f"✅ Tabla {i+1}: TABLA PRINCIPAL de partidos identificada")
                main_tables.append((i, table))
            else:
                # Mostrar por qué se descarta
                table_preview = table.get_text()[:100].replace('\n', ' ')
                print(f"❌ Tabla {i+1}: Descartada - {table_preview}...")
        
        print(f"🎾 Tablas principales encontradas: {len(main_tables)}")
        return main_tables
    
    def handle_all_merged_cells(self, table):
        """
        Maneja celdas combinadas para TODAS las columnas (especialmente 8 y 9)
        """
        rows = table.find_all('tr')
        
        # Mapa para rastrear celdas que se extienden múltiples filas
        cell_map = {}  # {(row, col): content}
        max_cols = 0
        
        # Primera pasada: mapear todas las celdas considerando rowspan/colspan
        for row_idx, row in enumerate(rows):
            cells = row.find_all(['td', 'th'])
            col_idx = 0
            
            for cell in cells:
                # Encontrar la próxima columna disponible
                while (row_idx, col_idx) in cell_map:
                    col_idx += 1
                
                cell_text = cell.get_text(strip=True)
                rowspan = int(cell.get('rowspan', 1))
                colspan = int(cell.get('colspan', 1))
                
                # Llenar todas las celdas que esta celda ocupa
                for r in range(rowspan):
                    for c in range(colspan):
                        cell_map[(row_idx + r, col_idx + c)] = cell_text
                
                col_idx += colspan
                max_cols = max(max_cols, col_idx)
        
        # Segunda pasada: crear filas consistentes
        processed_rows = []
        for row_idx in range(len(rows)):
            row_data = []
            for col_idx in range(max_cols):
                content = cell_map.get((row_idx, col_idx), '')
                row_data.append(content)
            processed_rows.append(row_data)
        
        return processed_rows
    
    def identify_tournament_headers(self, processed_rows):
        """
        Identifica filas que son headers de torneos
        """
        tournament_headers = []
        
        for i, row in enumerate(processed_rows):
            row_text = ' '.join(row).lower()
            
            # Patrones que indican header de torneo
            tournament_patterns = [
                'atp', 'masters', 'open', 'cup', 'championship',
                'tournament', 'grand slam'
            ]
            
            # La fila debe tener pocas celdas llenas (típico de headers)
            non_empty_cells = sum(1 for cell in row if cell.strip())
            
            # Verificar si parece header de torneo
            if (any(pattern in row_text for pattern in tournament_patterns) and 
                non_empty_cells <= 3 and 
                len(row_text) > 5):
                
                tournament_headers.append({
                    'row_index': i,
                    'tournament_name': ' '.join([cell for cell in row if cell.strip()])[:50]
                })
        
        return tournament_headers
    
    def extract_matches_with_context(self, processed_rows):
        """
        Extrae partidos identificando el contexto del torneo
        """
        matches = []
        current_tournament = "Unknown Tournament"
        
        # Identificar headers de torneos
        tournament_headers = self.identify_tournament_headers(processed_rows)
        
        print(f"🏆 Torneos identificados: {len(tournament_headers)}")
        for header in tournament_headers:
            print(f"   - Fila {header['row_index']}: {header['tournament_name']}")
        
        # Procesar cada fila
        for row_idx, row in enumerate(processed_rows[1:], 1):  # Saltar primera fila (header)
            
            # Verificar si esta fila es un header de torneo
            for header in tournament_headers:
                if header['row_index'] == row_idx:
                    current_tournament = header['tournament_name']
                    print(f"📍 Procesando torneo: {current_tournament}")
                    break
            
            # Verificar si esta fila contiene un partido
            if self.is_match_row(row):
                match_data = self.parse_enhanced_match(row, row_idx)
                match_data['tournament'] = current_tournament
                match_data['scraped_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                
                matches.append(match_data)
        
        return matches
    
    def is_match_row(self, row):
        """
        Determina si una fila contiene un partido (no un header)
        """
        row_text = ' '.join(row).strip()
        
        # Debe tener contenido mínimo
        if len(row_text) < 10:
            return False
        
        # Buscar indicadores de partido
        has_vs_pattern = ' vs ' in row_text.lower() or ' v ' in row_text.lower()
        has_score_pattern = re.search(r'\d+-\d+', row_text)
        has_time_pattern = re.search(r'\d{1,2}:\d{2}', row_text)
        
        # Al menos debe tener uno de estos patrones
        return has_vs_pattern or has_score_pattern or has_time_pattern
    
    def parse_enhanced_match(self, row, row_idx):
        """
        Parsea información del partido con mejor lógica
        """
        match_data = {
            'row_index': row_idx,
            'time': '',
            'player1': '',
            'player2': '',
            'score': '',
            'round': '',
            'status': ''
        }
        
        # Asignar todas las columnas disponibles
        for i, cell in enumerate(row[:12]):  # Hasta 12 columnas
            match_data[f'col_{i}'] = cell
        
        # Lógica específica para cada tipo de información
        for i, cell in enumerate(row):
            if not cell.strip():
                continue
            
            # Columna 0: típicamente hora
            if i == 0 and re.match(r'\d{1,2}:\d{2}', cell):
                match_data['time'] = cell
            
            # Buscar jugadores (columnas 1-4 típicamente)
            elif 1 <= i <= 4 and len(cell) > 3 and not any(c.isdigit() for c in cell):
                if not match_data['player1']:
                    match_data['player1'] = cell
                elif not match_data['player2'] and cell != match_data['player1']:
                    match_data['player2'] = cell
            
            # Buscar score (números con guiones)
            elif re.search(r'\d+-\d+', cell):
                if not match_data['score']:
                    match_data['score'] = cell
            
            # Buscar round/status
            elif any(keyword in cell.lower() for keyword in ['round', 'r1', 'r2', 'qf', 'sf', 'final', 'finished', 'live']):
                match_data['round'] = cell
        
        return match_data
    
    def scrape_optimized_matches(self):
        """
        Scraping optimizado final
        """
        print("🚀 SCRAPING FINAL OPTIMIZADO")
        print("=" * 60)
        
        # URL principal de resultados
        url = f"{self.base_url}/results/"
        
        response = self.get_page_safe(url, "página de resultados")
        if not response:
            return []
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Extraer SOLO la tabla principal
        main_tables = self.extract_main_table(soup)
        
        if not main_tables:
            print("❌ No se encontró la tabla principal de partidos")
            return []
        
        all_matches = []
        
        # Procesar cada tabla principal (debería ser solo 1)
        for table_idx, table in main_tables:
            print(f"\n🎾 Procesando tabla principal {table_idx + 1}...")
            
            # Manejar celdas combinadas en TODAS las columnas
            processed_rows = self.handle_all_merged_cells(table)
            
            print(f"📊 Filas procesadas: {len(processed_rows)}")
            print(f"📊 Columnas detectadas: {max(len(row) for row in processed_rows) if processed_rows else 0}")
            
            # Extraer partidos con contexto de torneo
            matches = self.extract_matches_with_context(processed_rows)
            
            all_matches.extend(matches)
        
        return all_matches
    
    def save_final_data(self, matches, filename='tennis_matches_final.csv'):
        """
        Guarda datos finales con análisis mejorado
        """
        if not matches:
            print("⚠️  No hay datos para guardar")
            return None
        
        df = pd.DataFrame(matches)
        filepath = self.data_dir / filename
        
        # Guardar CSV
        df.to_csv(filepath, index=False, encoding='utf-8')
        
        print(f"\n💾 ✅ DATOS FINALES GUARDADOS")
        print(f"📁 Ubicación: {filepath}")
        print(f"📊 Total registros: {len(df)}")
        
        return df
    
    def comprehensive_analysis(self, df):
        """
        Análisis comprehensive de los datos finales
        """
        print("\n" + "=" * 70)
        print("📊 ANÁLISIS COMPREHENSIVE - DATOS FINALES")
        print("=" * 70)
        
        # Información general
        print(f"\n📈 INFORMACIÓN GENERAL:")
        print(f"- Total de registros: {len(df)}")
        print(f"- Columnas disponibles: {len(df.columns)}")
        print(f"- Torneos únicos: {df['tournament'].nunique()}")
        
        # Calidad de extracción por campo
        print(f"\n🎯 CALIDAD DE EXTRACCIÓN:")
        quality_fields = ['time', 'player1', 'player2', 'score', 'round']
        
        for field in quality_fields:
            if field in df.columns:
                valid_count = df[field].notna().sum()
                non_empty_count = (df[field].str.len() > 0).sum() if df[field].dtype == 'object' else valid_count
                percentage = non_empty_count / len(df) * 100
                print(f"- {field:<10}: {non_empty_count:4d}/{len(df)} ({percentage:5.1f}%)")
        
        # Análisis de torneos
        print(f"\n🏆 TORNEOS IDENTIFICADOS:")
        tournament_counts = df['tournament'].value_counts()
        for tournament, count in tournament_counts.head(10).items():
            print(f"- {tournament:<30}: {count:3d} partidos")
        
        # Mejores ejemplos de partidos completos
        print(f"\n🎾 MEJORES PARTIDOS EXTRAÍDOS:")
        complete_matches = df[
            df['player1'].notna() & 
            df['player2'].notna() & 
            df['score'].notna() &
            (df['player1'].str.len() > 2) &
            (df['player2'].str.len() > 2)
        ]
        
        print(f"   Partidos completos: {len(complete_matches)}/{len(df)} ({len(complete_matches)/len(df)*100:.1f}%)")
        
        if len(complete_matches) > 0:
            print(f"\n🏅 EJEMPLOS DE PARTIDOS COMPLETOS:")
            for i, (_, match) in enumerate(complete_matches.head(5).iterrows(), 1):
                time_str = match.get('time', 'No time')
                score_str = match.get('score', 'No score')
                tournament_str = match.get('tournament', 'Unknown')[:20]
                
                print(f"{i}. {time_str} | {match['player1']} vs {match['player2']}")
                print(f"   Score: {score_str} | Torneo: {tournament_str}")
        
        # Problemas identificados
        print(f"\n⚠️  PROBLEMAS IDENTIFICADOS:")
        problems = []
        
        if len(complete_matches) < len(df) * 0.3:
            problems.append(f"Solo {len(complete_matches)}/{len(df)} partidos completos")
        
        if df['tournament'].isna().sum() > len(df) * 0.5:
            problems.append("Muchos partidos sin torneo identificado")
        
        if len(problems) > 0:
            for problem in problems:
                print(f"- {problem}")
        else:
            print("✅ No se detectaron problemas mayores")
        
        return {
            'total_matches': len(df),
            'complete_matches': len(complete_matches),
            'tournaments': df['tournament'].nunique(),
            'quality_score': len(complete_matches) / len(df) if len(df) > 0 else 0
        }

def main():
    """
    Función principal optimizada
    """
    print("🎾 TENNIS EXPLORER SCRAPER - VERSIÓN FINAL")
    print("=" * 70)
    
    # Crear scraper final
    scraper = FinalTennisExplorerScraper(delay=3)
    
    # Ejecutar scraping optimizado
    matches = scraper.scrape_optimized_matches()
    
    if matches:
        # Guardar y analizar
        df = scraper.save_final_data(matches)
        
        if df is not None:
            results = scraper.comprehensive_analysis(df)
            
            print(f"\n🎉 ¡SCRAPING FINAL COMPLETADO!")
            print(f"\n📊 RESUMEN:")
            print(f"- Partidos totales: {results['total_matches']}")
            print(f"- Partidos completos: {results['complete_matches']}")
            print(f"- Calidad: {results['quality_score']*100:.1f}%")
            print(f"- Torneos: {results['tournaments']}")
            
            if results['quality_score'] > 0.3:
                print(f"\n✅ ¡DATOS DE BUENA CALIDAD!")
                print(f"📋 PRÓXIMOS PASOS:")
                print(f"1. Análisis exploratorio de datos (EDA)")
                print(f"2. Limpieza y preprocessing")
                print(f"3. Crear features para ML")
                print(f"4. Entrenar primer modelo")
            else:
                print(f"\n⚠️  CALIDAD BAJA - Necesita ajustes")
                print(f"💡 SUGERENCIAS:")
                print(f"- Ajustar selectores de tabla")
                print(f"- Probar URLs más específicas")
                print(f"- Revisar estructura del sitio")
    
    else:
        print("\n❌ No se obtuvieron datos")

if __name__ == "__main__":
    main()