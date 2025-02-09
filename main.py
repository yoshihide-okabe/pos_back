import sys  # 🔥 sys をインポートして標準出力を強制フラッシュ

sys.stdout.reconfigure(encoding='utf-8') # 🔥 これでログがすぐに表示される
print("🚀 FastAPI アプリケーションが起動しました", file=sys.stdout)

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import mysql.connector
from typing import List
from fastapi.middleware.cors import CORSMiddleware
import os
import uvicorn

app = FastAPI() 

# 🚀 CORS設定を追加
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://tech0-gen8-step4-pos-app-115.azurewebsites.net",  # 本番用
        "http://localhost:3000"  # ローカル開発用
    ],
    allow_credentials=True,
    allow_methods=["*"],  # すべてのHTTPメソッド（GET, POSTなど）を許可
    allow_headers=["*"],  # すべてのHTTPヘッダーを許可
)

@app.get("/")
def read_root():
    return {"message": "Hello, FastAPI!"}

# MySQL接続設定
db_config = {
    "host": "tech0-gen-8-step4-db-5.mysql.database.azure.com",
    "user": "Tech0Gen8TA5",
    "password": "gen8-1-ta@5",
    "database": "class5_db",
    "ssl_ca": "C:\\MySQL\\MySQL Server 8.4\\certs\\DigiCertGlobalRootCA.crt.pem"  # ✅ 余計なカンマを削除
}

# 商品情報モデル
class Product(BaseModel):
    code: str
    name: str
    price: int

# 購入リクエストモデル
class PurchaseItem(BaseModel):
    code: str
    name: str
    price: int

class PurchaseRequest(BaseModel):
    emp_cd: str
    store_cd: str
    pos_no: str
    items: List[PurchaseItem]

@app.get("/product/{code}")
def get_product(code: str):
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor(dictionary=True)
    
    print(f"🔍 受信した商品コード: {code}")  # 受信したコードを確認
    cursor.execute("SELECT * FROM m_product_okabe WHERE CODE = %s", (code,))
    product = cursor.fetchone()
    print(f"🔍 検索結果: {product}")  # ここでデータが取得できているか確認
    
    cursor.close()
    conn.close()
    
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    return product

@app.post("/purchase")
def purchase_items(request: PurchaseRequest):
    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor(dictionary=True)

        emp_cd = request.emp_cd if request.emp_cd.strip() else '9999999999'

        # 取引データを挿入
        cursor.execute(
            "INSERT INTO transactions_okabe (DATETIME, EMP_CD, STORE_CD, POS_NO, TOTAL_AMT) VALUES (NOW(), %s, %s, %s, %s)",
            (emp_cd, '30', '90', 0)
        )
        conn.commit()  # ✅ ここでコミット
        transaction_id = cursor.lastrowid

        print(f"✅ 取引データ挿入成功: TRD_ID = {transaction_id}", file=sys.stdout)
        sys.stdout.flush()
        
        if not transaction_id:
            raise HTTPException(status_code=500, detail="Failed to insert transaction record")

        total_amount = 0

        for item in request.items:
            print(f"🔍 商品コード取得: {item.code}", file=sys.stdout)
            sys.stdout.flush()

            cursor.execute("SELECT PRD_ID, NAME, PRICE FROM m_product_okabe WHERE CODE = %s", (item.code,))
            product = cursor.fetchone()

            if not product:
                raise HTTPException(status_code=404, detail=f"Product with code {item.code} not found")

            prd_id = product["PRD_ID"]
            product_name = product["NAME"]
            product_price = product["PRICE"]
            print(f"✅ 商品情報取得: PRD_ID={prd_id}, NAME={product_name}, PRICE={product_price}", file=sys.stdout)
            sys.stdout.flush()

            cursor.execute("SELECT MAX(DTL_ID) FROM transaction_details_okabe")
            max_dtl_id = cursor.fetchone()

            print(f"🔍 `MAX(DTL_ID)` の取得結果: {max_dtl_id}", file=sys.stdout)
            sys.stdout.flush()

            new_dtl_id = 1 if max_dtl_id is None or max_dtl_id[0] is None else max_dtl_id[0] + 1
            print(f"✅ 新しい明細ID: {new_dtl_id}", file=sys.stdout)
            sys.stdout.flush()

            print(f"🛠 INSERTデータ: DTL_ID={new_dtl_id}, TRD_ID={transaction_id}, PRD_ID={prd_id}, PRD_CODE={item.code}, PRD_NAME={product_name}, PRD_PRICE={product_price}", file=sys.stdout)
            sys.stdout.flush()
            
            cursor.execute(
                """
                INSERT INTO transaction_details_okabe
                (DTL_ID, TRD_ID, PRD_ID, PRD_CODE, PRD_NAME, PRD_PRICE) 
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (new_dtl_id, transaction_id, prd_id, item.code, product_name, int(product_price))
            )
            total_amount += int(product_price)
            print(f"✅ 明細データ登録成功: DTL_ID={new_dtl_id}", file=sys.stdout)
            sys.stdout.flush()

        # 合計金額を更新
        cursor.execute(
            "UPDATE transactions_okabe SET TOTAL_AMT = %s WHERE TRD_ID = %s",
            (total_amount, transaction_id)
        )
        conn.commit()
        print(f"✅ 合計金額更新成功: TOTAL_AMT = {total_amount}", file=sys.stdout)
        sys.stdout.flush()

        cursor.close()
        conn.close()

        return {"success": True, "total_amount": total_amount}
    
    except mysql.connector.Error as err:
        print(f"❌ MySQLエラー: {err}", file=sys.stdout)
        sys.stdout.flush()
        raise HTTPException(status_code=500, detail=f"MySQL Error: {err}")

    except Exception as e:
        print(f"❌ 予期しないエラー: {str(e)}", file=sys.stdout)
        sys.stdout.flush()
        raise HTTPException(status_code=500, detail=f"Server Error: {str(e)}")
        
#  **起動スクリプトを追加**
#if __name__ == "__main__":
#    port = int(os.environ.get("PORT", 8000))  # 環境変数 PORT を取得（デフォルト 8000）
#    uvicorn.run(app, host="0.0.0.0", port=port)
#
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=int(os.environ.get("PORT", 8000)), reload=True)



