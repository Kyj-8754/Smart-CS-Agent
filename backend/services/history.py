import csv
import os
import uuid
from datetime import datetime

class HistoryService:
    def __init__(self):
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.csv_file_path = os.path.join(base_dir, 'data', 'history.csv')
        self._ensure_file_exists()

    def _ensure_file_exists(self):
        if not os.path.exists(self.csv_file_path):
            with open(self.csv_file_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(['id', 'user_id', 'timestamp', 'query', 'intent', 'response', 'feedback'])

    def log_interaction(self, user_id, query, intent, response):
        """대화 내용을 기록합니다."""
        interaction_id = str(int(datetime.now().timestamp() * 1000)) # Simple unique ID based on timestamp
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        
        # response가 객체일 수 있으므로 문자열 변환 (간단히 메시지만 저장)
        response_text = response.get('message', '') if isinstance(response, dict) else str(response)

        with open(self.csv_file_path, 'a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow([interaction_id, user_id, timestamp, query, intent, response_text, ''])
            
        return interaction_id

    def get_user_history(self, user_id):
        """특정 사용자의 대화 기록을 최신순으로 반환합니다."""
        history = []
        if not os.path.exists(self.csv_file_path):
            return history

        with open(self.csv_file_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row['user_id'] == user_id:
                    history.append(row)
        
        # 최신순 정렬 (timestamp 기준 내림차순, 단순 문자열 비교도 YYYY-MM-DD 형식이면 가능)
        return sorted(history, key=lambda x: x['timestamp'], reverse=True)

    def update_feedback(self, interaction_id, feedback_type):
        """특정 대화의 피드백을 업데이트합니다."""
        rows = []
        updated = False
        
        if not os.path.exists(self.csv_file_path):
            return False

        with open(self.csv_file_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            fieldnames = reader.fieldnames
            for row in reader:
                if row['id'] == str(interaction_id):
                    row['feedback'] = feedback_type
                    updated = True
                rows.append(row)

        if updated:
            with open(self.csv_file_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(rows)
                
        return updated
