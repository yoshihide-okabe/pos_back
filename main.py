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
    "host": "localhost",
    "user": "root",
    "password": "Sudachishirasu1",  # 自分のMySQLのパスワードに変更
    "database": "class5_db"
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
        cursor = conn.cursor()

        # レジ担当者コードのデフォルト設定
        emp_cd = request.emp_cd if request.emp_cd.strip() else '9999999999'
        
        # 取引の登録（取引一意キーは AUTO_INCREMENT の TRD_ID で管理）
        cursor.execute(
            """
            INSERT INTO transactions_okabe (DATETIME, EMP_CD, STORE_CD, POS_NO, TOTAL_AMT) 
            VALUES (NOW(), %s, %s, %s, %s)
            """,
            (emp_cd, '30', '90',  0)
        )

        transaction_id = cursor.lastrowid   # 取引一意キーの取得

        if not transaction_id:
            raise HTTPException(status_code=500, detail="Failed to insert transaction record")

        total_amount = 0

        for item in request.items:
            
            if not item.code:
                raise HTTPException(status_code=400, detail="Invalid item data: PRD_CODE is required")

            # `m_product_okabe` から `PRD_ID`, `NAME`, `PRICE` を取得
            cursor.execute("SELECT PRD_ID, NAME, PRICE FROM m_product_okabe WHERE CODE = %s", (item.code,))
            product = cursor.fetchone()

            if not product:
                raise HTTPException(status_code=404, detail=f"Product with code {item.code} not found")
                
            # prd_id, product_name, product_price = product
            prd_id = product["PRD_ID"]
            product_name = product["NAME"]
            product_price = product["PRICE"]

            # `DTL_ID` の最大値を取得し、+1 する
            cursor.execute("SELECT MAX(DTL_ID) FROM transaction_details_okabe")
            max_dtl_id = cursor.fetchone()[0]
            
            # `MAX(DTL_ID)` が `None` の場合、最初の値を `1` に設定
            new_dtl_id = 1 if max_dtl_id is None else max_dtl_id + 1
            
            # 商品明細の登録
            cursor.execute(
                """
                INSERT INTO transaction_details_okabe
                (DTL_ID, TRD_ID, PRD_ID, PRD_CODE, PRD_NAME, PRD_PRICE) 
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (new_dtl_id, transaction_id, prd_id, item.code, product_name, int(product_price))
            )
            total_amount += int(product_price)


        # 合計金額の更新
        cursor.execute(
            "UPDATE transactions_okabe SET TOTAL_AMT = %s WHERE TRD_ID = %s",
            (total_amount, transaction_id)
        )

        conn.commit()
        cursor.close()
        conn.close()

        return {"success": True, "total_amount": total_amount}
    
    except mysql.connector.Error as err:
        raise HTTPException(status_code=500, detail=f"MySQL Error: {err}")

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Server Error: {str(e)}")
        
#  **起動スクリプトを追加**
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))  # 環境変数 PORT を取得（デフォルト 8000）
    uvicorn.run(app, host="0.0.0.0", port=port)


