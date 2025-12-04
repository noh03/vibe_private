
import os

from gui.main_window import run


if __name__ == "__main__":
    # main.py 와 같은 디렉터리를 기준으로 경로를 계산
    base_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(base_dir, "jira_config.json")
    db_path = os.path.join(base_dir, "rtm_local.db")

    run(db_path=db_path, config_path=config_path)
