import csv
import os
import re
from datetime import datetime

class TransactionService:
    def __init__(self):
        # 데이터 파일 경로 설정
        # backend/services/../data/orders.csv
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.csv_file_path = os.path.join(base_dir, 'data', 'orders.csv')
        
        self.orders = {}
        self.pending_transactions = {} # 트랜잭션 임시 저장소 (캐시)
        self.user_sessions = {} # 유저별 세션 (last_viewed 등)
        self._load_data()

    def _load_data(self):
        """CSV 파일에서 주문 데이터를 로드합니다."""
        if not os.path.exists(self.csv_file_path):
            print(f"File not found: {self.csv_file_path}")
            return
        
        with open(self.csv_file_path, mode='r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            self.orders = {} # 초기화
            for row in reader:
                # order_id를 키로 사용
                self.orders[row["order_id"]] = row

    def _save_data(self):
        """변경된 데이터를 CSV 파일에 영구 저장합니다."""
        if not self.orders:
            return
            
        fieldnames = ["order_id", "item", "status", "customer_name", "customer_id"]
        with open(self.csv_file_path, mode='w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for order in self.orders.values():
                writer.writerow(order)

    def _find_active_order(self, user_id: str):
        """
        유저의 주문 중 현재 트래킹이 필요한 가장 최근 주문을 찾습니다.
        우선순위: 배송중 > 상품준비중 > 배송완료(최근)
        취소된 주문은 제외합니다.
        """
        user_orders = [o for o in self.orders.values() if o.get('customer_id') == user_id]
        
        if not user_orders:
            return None
            
        # 우선순위에 따라 정렬하여 반환
        for status in ["배송중", "상품준비중"]:
            for order in user_orders:
                if order['status'] == status:
                    return order
        
        # 활성 주문이 없으면 가장 최근의 배송완료 주문이라도 반환 (단, 취소 제외)
        # 여기서는 단순하게 리스트의 뒤쪽(최근)에서부터 배송완료를 찾음 ORder ID가 시간순이라고 가정
        sorted_orders = sorted(user_orders, key=lambda x: x['order_id'], reverse=True)
        for order in sorted_orders:
            if order['status'] != "주문취소":
                return order
                
        return None

    def process_transaction(self, intent: str, entity: str = None, user_id: str = None) -> dict:
        """
        사용자의 의도(Intent)와 엔티티(Entity)를 받아 트랜잭션을 처리합니다.
        user_id가 제공되면 해당 유저의 맥락을 고려합니다.
        """
        # 최신 데이터 로드
        self._load_data()
        
        # 1. 엔티티에서 주문번호 추출 (ORD-001 형태)
        order_id = None
        if entity:
            match = re.search(r'(ORD-\d+)', entity.upper())
            if match:
                order_id = match.group(1)
        
        # 2. 주문번호가 없고 유저 ID가 있다면, 스마트 조회를 시도
        if not order_id and user_id:
            # 의도가 '조회' 관련일 때만 스마트 조회 (취소 때는 세션/명시적 ID 우선)
            if "status" in intent.lower() or "조회" in intent or "배송" in intent:
                active_order = self._find_active_order(user_id)
                if active_order:
                    order_id = active_order['order_id']

        # --- 배송 상태 조회 로직 ---
        if "status" in intent.lower() or "조회" in intent or "배송" in intent:
            if not order_id:
                msg = "배송 조회할 주문 내역을 찾을 수 없습니다."
                if user_id:
                    msg += " (최근 주문 내역 없음)"
                else:
                    msg += " 주문 번호를 알려주세요."
                return {"status": "error", "message": msg}
            
            if order_id in self.orders:
                order = self.orders[order_id]
                
                # 본인 확인 (유저 ID가 제공된 경우)
                if user_id and order.get('customer_id') and order['customer_id'] != user_id:
                    return {"status": "error", "message": "해당 주문에 대한 권한이 없습니다."}

                # 세션에 저장 (유저별)
                if user_id:
                    self.user_sessions[user_id] = {"last_viewed": order_id}
                else:
                    self.pending_transactions["global_last_viewed"] = order_id # Fallback
                
                return {
                    "status": "completed",
                    "message": f"고객님의 주문 {order_id} ({order['item']})은(는) 현재 '{order['status']}' 상태입니다.",
                    "data": order
                }
            else:
                return {"status": "error", "message": f"주문번호 {order_id}를 찾을 수 없습니다."}

        # --- 주문 취소 로직 ---
        elif "cancel" in intent.lower() or "취소" in intent:
            # 1순위: 명시적 order_id
            # 2순위: 유저 세션의 last_viewed
            if not order_id:
                if user_id and user_id in self.user_sessions:
                    order_id = self.user_sessions[user_id].get("last_viewed")
                elif "global_last_viewed" in self.pending_transactions:
                    order_id = self.pending_transactions["global_last_viewed"]
            
            if not order_id:
                return {"status": "error", "message": "취소할 주문이 명확하지 않습니다. 먼저 주문을 조회해주세요."}
            
            if order_id in self.orders:
                order = self.orders[order_id]
                
                # 본인 확인
                if user_id and order.get('customer_id') and order['customer_id'] != user_id:
                    return {"status": "error", "message": "해당 주문을 취소할 권한이 없습니다."}

                # 상태 체크
                if order['status'] == "배송완료":
                    return {"status": "failed", "message": f"주문 {order_id}는 이미 배송이 완료되어 취소할 수 없습니다."}
                if order['status'] == "주문취소":
                    return {"status": "failed", "message": f"주문 {order_id}는 이미 취소된 주문입니다."}
                
                # 취소 트랜잭션 생성
                transaction_id = f"TXN-{int(datetime.now().timestamp())}"
                pending_action = {
                    "transaction_id": transaction_id,
                    "action_type": "cancel_order",
                    "target_entity": order_id,
                    "current_value": order['status'],
                    "new_value": "주문취소",
                    "status": "pending_approval",
                    "user_id": user_id, # 트랜잭션 소유자 기록
                    "timestamp": datetime.now().isoformat()
                }
                
                self.pending_transactions[transaction_id] = pending_action
                
                return {
                    "status": "pending_approval",
                    "message": f"주문 {order_id} ({order['item']}, {order['status']})를 정말 취소하시겠습니까? (예/아니오)",
                    "data": pending_action
                }
            else:
                return {"status": "error", "message": "주문 정보를 찾을 수 없습니다."}
        
        return {"status": "error", "message": "알 수 없는 요청입니다."}

    def execute_transaction(self, transaction_id: str):
        """
        사용자가 확답(승인)을 했을 때 호출되어 실제 데이터 수정을 수행합니다.
        """
        if transaction_id not in self.pending_transactions:
            return {"status": "error", "message": "유효하지 않거나 만료된 트랜잭션 ID입니다."}
            
        action = self.pending_transactions[transaction_id]
        
        if action['action_type'] == "cancel_order":
            order_id = action['target_entity']
            if order_id in self.orders:
                self.orders[order_id]['status'] = action['new_value']
                self._save_data()
                
                # 캐시/세션 정리
                del self.pending_transactions[transaction_id]
                
                # 세션에서 해당 주문 제거 (선택적)
                user_id = action.get("user_id")
                if user_id and user_id in self.user_sessions:
                     if self.user_sessions[user_id].get("last_viewed") == order_id:
                         del self.user_sessions[user_id]["last_viewed"]
                # 전역 last_viewed도 정리
                if "global_last_viewed" in self.pending_transactions and self.pending_transactions["global_last_viewed"] == order_id:
                    del self.pending_transactions["global_last_viewed"]
                    
                return {
                    "status": "success", 
                    "transaction_id": transaction_id, 
                    "message": f"주문 {order_id}가 성공적으로 취소되었습니다."
                }
        
        return {"status": "error", "message": "트랜잭션 실행 실패"}
