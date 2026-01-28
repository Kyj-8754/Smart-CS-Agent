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
                # status 공백 제거 등 전처리
                row['status'] = row['status'].strip()
                self.orders[row["order_id"]] = row

    def _save_data(self):
        """변경된 데이터를 CSV 파일에 영구 저장합니다."""
        if not self.orders:
            return
            
        fieldnames = ["order_id", "item", "status", "customer_name", "customer_id", "order_date"]
        with open(self.csv_file_path, mode='w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for order in self.orders.values():
                # 저장 시 필요한 필드만 추출
                row = {k: order.get(k, "") for k in fieldnames}
                writer.writerow(row)

    def _find_active_orders(self, user_id: str):
        """
        유저의 주문 중 '진행 중'인 주문 목록을 반환합니다.
        반환: (active_orders_list, most_recent_order)
        """
        user_orders = [o for o in self.orders.values() if o.get('customer_id') == user_id]
        
        if not user_orders:
            return [], None
            
        # 활성 상태 정의
        active_statuses = ["배송중", "상품준비중"]
        active_orders = [o for o in user_orders if o['status'] in active_statuses]
        
        # 시간순 정렬 (최신순) - order_date가 있으면 사용, 없으면 order_id 역순
        def sort_key(x):
            if 'order_date' in x and x['order_date']:
                 return x['order_date']
            return x['order_id']
            
        sorted_orders = sorted(user_orders, key=sort_key, reverse=True)
        sorted_active = sorted(active_orders, key=sort_key, reverse=True)
        
        most_recent = sorted_orders[0] if sorted_orders else None
        
        return sorted_active, most_recent

    def process_transaction(self, intent: str, entity: str = None, user_id: str = None) -> dict:
        """
        사용자의 의도(Intent)와 엔티티(Entity)를 받아 트랜잭션을 처리합니다.
        user_id가 제공되면 해당 유저의 맥락을 고려합니다.
        """
        # 0. [NEW] 승인 대기 중인 트랜잭션이 있고, 사용자가 확답(예/아니오)을 한 경우 우선 처리
        pending_txn = None
        if user_id:
             for txn_id, txn in self.pending_transactions.items():
                 if txn.get("user_id") == user_id and txn.get("status") == "pending_approval":
                     pending_txn = txn
                     break
        
        if pending_txn:
             # 긍정 응답 처리
             affirmative = ["예", "네", "그래", "해줘", "yes", "okay", "confirm"]
             negative = ["아니", "아니오", "취소", "no", "cancel"]
             
             # entity(=query)가 긍정/부정인지 확인
             user_response = entity.lower() if entity else ""
             
             if any(word in user_response for word in affirmative):
                 return self.execute_transaction(pending_txn["transaction_id"])
             elif any(word in user_response for word in negative):
                 del self.pending_transactions[pending_txn["transaction_id"]]
                 return {"status": "cancelled", "message": "취소가 철회되었습니다."}
             
             # 모호한 답변이면 다시 물어봄 (여기서 return하지 않고 아래 로직 태울수도 있지만, 컨텍스트가 강력하므로 재확인)
             # 단, 일반 transaction intent("배송 조회")로 넘어갈 수도 있으므로, 
             # 긍/부정이 명확하지 않으면 아래 일반 로직으로 흘려보냄.

        # Intent가 포괄적인 'transaction'일 경우, entity(Query) 내용을 기반으로 세부 의도 파악
        if intent == "transaction" and entity:
            if any(k in entity for k in ["취소", "cancel"]):
                intent = "cancel"
            elif any(k in entity for k in ["조회", "배송", "어디", "status", "tracking"]):
                intent = "status_check"

        # 최신 데이터 로드
        self._load_data()
        
        # 1. 엔티티에서 주문번호 추출 (ORD-001 형태)
        order_id = None
        if entity:
            match = re.search(r'(ORD-\d+)', entity.upper())
            if match:
                order_id = match.group(1)
        
        # 1.5. [NEW] 주문번호가 없고 유저 세션에 'candidates'가 있다면, 아이템명 등으로 매칭 시도
        if not order_id and user_id and user_id in self.user_sessions:
            candidates = self.user_sessions[user_id].get("candidates", [])
            if candidates and entity:
                # candidates는 order_id 리스트임. 해당 주문들의 정보 조회
                for cand_id in candidates:
                    if cand_id in self.orders:
                        cand_order = self.orders[cand_id]
                        # 아이템명이 쿼리에 포함되어 있는지 확인 (간단한 포함 여부)
                        # 예: entity="사운드바 보여줘", item="사운드바" -> Match
                        if cand_order['item'] in entity or cand_order['item'].replace(" ", "") in entity.replace(" ", ""):
                            order_id = cand_id
                            # 매칭 성공 시 candidates 제거 (선택 완료)
                            del self.user_sessions[user_id]["candidates"]
                            
                            # [FIX] 모호성 해소 성공 시, 의도를 '조회'로 확정
                            if intent == "transaction":
                                intent = "status_check"
                            break
        
        # 2. 주문번호가 없고 유저 ID가 있다면, 스마트 조회를 시도
        # (취소 Intent일 때는 신중해야 하므로 여기서 바로 자동 할당하지 않음, status_check일 때만 아래 로직으로 후보군 탐색)
        
        # --- 배송 상태 조회 로직 ---
        if "status" in intent.lower() or "조회" in intent or "배송" in intent:
            if not order_id and user_id:
                active_orders, most_recent = self._find_active_orders(user_id)
                
                # Case 1: 활성 주문이 여러 개 -> 리스트 반환하여 선택 유도
                if len(active_orders) > 1:
                    # 세션에 후보 리스트 저장 (선택 문맥을 위해)
                    self.user_sessions[user_id] = {"candidates": [o['order_id'] for o in active_orders]}
                    
                    order_list_str = "\n".join([f"- {o['item']} ({o['status']})" for o in active_orders])
                    return {
                        "status": "multiple_choice",
                        "message": f"현재 진행 중인 주문이 {len(active_orders)}건 있습니다. 어떤 주문을 조회하시겠습니까?\n{order_list_str}",
                        "data": active_orders
                    }
                
                # Case 2: 활성 주문이 1개 -> 자동 선택
                elif len(active_orders) == 1:
                    order_id = active_orders[0]['order_id']
                
                # Case 3: 활성 주문 없음 -> 가장 최근 기록(배송완료 등) 보여주기
                elif most_recent:
                    order_id = most_recent['order_id']

            if not order_id:
                msg = "조회할 주문 내역이 없습니다."
                return {"status": "error", "message": msg}
            
            if order_id in self.orders:
                order = self.orders[order_id]
                
                # 본인 확인
                if user_id and order.get('customer_id') and order['customer_id'] != user_id:
                    return {"status": "error", "message": "해당 주문에 대한 권한이 없습니다."}

                # 세션에 저장 (유저별) - 명확하게 조회한 대상을 last_viewed로 설정
                self.user_sessions[user_id] = {"last_viewed": order_id}
                
                return {
                    "status": "completed",
                    "message": f"고객님의 주문 {order_id} ({order['item']})은(는) 현재 '{order['status']}' 상태입니다.",
                    "data": order
                }
            else:
                return {"status": "error", "message": f"주문번호 {order_id}를 찾을 수 없습니다."}

        # --- 주문 취소 로직 ---
        elif "cancel" in intent.lower() or "취소" in intent:
            # 1. 명시적 order_id 확인
            # 2. 없으면 세션의 last_viewed 확인
            # 3. 없으면 거절
            
            target_order_id = order_id
            
            if not target_order_id:
                if user_id and user_id in self.user_sessions:
                    target_order_id = self.user_sessions[user_id].get("last_viewed")
            
            if not target_order_id:
                 return {
                     "status": "need_selection", 
                     "message": "취소할 주문이 선택되지 않았습니다. 먼저 주문 배송 조회를 통해 대상을 확인해주세요."
                 }
            
            order_id = target_order_id # 타겟 확정
            
            if order_id in self.orders:
                order = self.orders[order_id]
                
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
                    "target_item": order['item'], # 검증용 정보
                    "current_status": order['status'], # 검증용 정보
                    "new_value": "주문취소",
                    "status": "pending_approval",
                    "user_id": user_id,
                    "timestamp": datetime.now().isoformat()
                }
                
                self.pending_transactions[transaction_id] = pending_action
                
                return {
                    "status": "pending_approval",
                    "message": f"주문 {order_id} ({order['item']}, {order['status']})를 정말 취소하시겠습니까? (예/아니오)",
                    "data": pending_action,
                    # [NEW] Frontend UI Trigger
                    "ui_action": {
                        "type": "show_approval_dialog",
                        "description": f"주문 {order_id} ({order['item']}) 취소 승인 요청",
                        "data": {
                            "주문번호": order_id,
                            "상품명": order['item'],
                            "현재상태": order['status'],
                            "요청작업": "주문 취소"
                        }
                    }
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
            # [검증 강화] 데이터 다시 로드 및 상태 재확인
            self._load_data()
            order_id = action['target_entity']
            
            if order_id not in self.orders:
                 del self.pending_transactions[transaction_id]
                 return {"status": "error", "message": "주문 정보가 사라졌습니다."}
            
            current_order = self.orders[order_id]
            
            # 상태 변경 여부 확인 (동시성/타이밍 이슈 방지)
            if current_order['status'] != action['current_status']:
                del self.pending_transactions[transaction_id]
                return {
                    "status": "error", 
                    "message": f"주문 상태가 변경되어 취소할 수 없습니다. (현재: {current_order['status']})"
                }
            
            # 실제 업데이트 수행
            self.orders[order_id]['status'] = action['new_value']
            self._save_data()
            
            # 캐시/세션 정리
            del self.pending_transactions[transaction_id]
            
            # 세션에서 해당 주문 제거 (선택적)
            user_id = action.get("user_id")
            if user_id and user_id in self.user_sessions:
                 if self.user_sessions[user_id].get("last_viewed") == order_id:
                     del self.user_sessions[user_id]["last_viewed"]
                
            return {
                "status": "success", 
                "transaction_id": transaction_id, 
                "message": f"주문 {order_id}가 성공적으로 취소되었습니다."
            }

        
        return {"status": "error", "message": "트랜잭션 실행 실패"}
