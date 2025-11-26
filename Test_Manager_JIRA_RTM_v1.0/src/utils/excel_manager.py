import pandas as pd
import os
from typing import List, Dict, Any

class ExcelManager:
    def export_data(self, issues_data: List[Dict[str, Any]], steps_data: List[Dict[str, Any]], file_path: str):
        """
        Export issues and steps to an Excel file with multiple sheets.
        """
        try:
            with pd.ExcelWriter(file_path, engine='openpyxl') as writer:
                df_issues = pd.DataFrame(issues_data)
                df_issues.to_excel(writer, sheet_name='Issues', index=False)
                
                if steps_data:
                    df_steps = pd.DataFrame(steps_data)
                    df_steps.to_excel(writer, sheet_name='Steps', index=False)
        except Exception as e:
            raise RuntimeError(f"Failed to export excel: {e}")

    def import_data(self, file_path: str) -> Dict[str, List[Dict[str, Any]]]:
        """
        Import data from Excel. Returns a dict with 'issues' and 'steps'.
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")
            
        try:
            xls = pd.ExcelFile(file_path)
            data = {}
            
            # Read Issues
            if 'Issues' in xls.sheet_names:
                # Replace NaN with None/Empty string for cleaner UI handling
                df = pd.read_excel(xls, 'Issues').fillna("")
                data['issues'] = df.to_dict(orient='records')
            else:
                data['issues'] = []
                
            # Read Steps
            if 'Steps' in xls.sheet_names:
                df = pd.read_excel(xls, 'Steps').fillna("")
                data['steps'] = df.to_dict(orient='records')
            else:
                data['steps'] = []
                
            return data
        except Exception as e:
            raise RuntimeError(f"Failed to import excel: {e}")

excel_manager = ExcelManager()

