from typing import List, Dict, Any

import os
import pandas as pd


class ExcelManager:
    def export_data(
        self, issues_data: List[Dict[str, Any]], steps_data: List[Dict[str, Any]], file_path: str
    ) -> None:
        """이슈 및 스텝 데이터를 Excel로 내보내기 (Issues/Steps 시트)."""
        try:
            with pd.ExcelWriter(file_path, engine="openpyxl") as writer:
                df_issues = pd.DataFrame(issues_data)
                df_issues.to_excel(writer, sheet_name="Issues", index=False)

                if steps_data:
                    df_steps = pd.DataFrame(steps_data)
                    df_steps.to_excel(writer, sheet_name="Steps", index=False)
        except Exception as e:
            raise RuntimeError(f"Failed to export excel: {e}")

    def import_data(self, file_path: str) -> Dict[str, List[Dict[str, Any]]]:
        """Excel에서 Issues/Steps 데이터를 읽어 dict 로 반환."""
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")

        try:
            xls = pd.ExcelFile(file_path)
            data: Dict[str, List[Dict[str, Any]]] = {}

            if "Issues" in xls.sheet_names:
                df = pd.read_excel(xls, "Issues").fillna("")
                data["issues"] = df.to_dict(orient="records")
            else:
                data["issues"] = []

            if "Steps" in xls.sheet_names:
                df = pd.read_excel(xls, "Steps").fillna("")
                data["steps"] = df.to_dict(orient="records")
            else:
                data["steps"] = []

            return data
        except Exception as e:
            raise RuntimeError(f"Failed to import excel: {e}")


excel_manager = ExcelManager()


