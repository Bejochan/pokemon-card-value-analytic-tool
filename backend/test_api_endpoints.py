import sys, time, base64, asyncio
sys.path.insert(0, 'backend')

from app.main import get_card_forecast, evaluate_card_condition_base64
from app.schemas import CardConditionRequest

print("=== 1. TEST GET /cards/sv4-241/forecast ===")
t0 = time.time()
res_fc = get_card_forecast("sv4-241")
print(f"Done in: {round(time.time() - t0, 3)} s")
print(f"Card: {res_fc['card_name']}")
print(f"Current: ${res_fc['current_price_usd']} | Day 7: ${res_fc['predicted_price_day7_usd']}")
print(f"Signal: {res_fc['signal']} | AI Confidence: {res_fc['ai_confidence_pct']}%")
for pt in res_fc['forecast']:
    print(f"  Day {pt['day']} ({pt['date']}) : ${pt['predicted_price_usd']:.2f}")

print("\n=== 2. TEST POST /cards/sv4-241/condition (TAMPAK DEPAN & BELAKANG) ===")
def to_b64(path):
    with open(path, "rb") as f:
        return "data:image/jpeg;base64," + base64.b64encode(f.read()).decode("utf-8")

req = CardConditionRequest(
    front_image=to_b64("backend/models/debug_TAMPAK_DEPAN.jpg"),
    back_image=to_b64("backend/models/debug_TAMPAK_BELAKANG.jpg")
)

t1 = time.time()
res_cond = evaluate_card_condition_base64("sv4-241", req)
print(f"Done in: {round(time.time() - t1, 3)} s")
print(f"Score: {res_cond['condition_score_pct']}%")
print(f"Tier: {res_cond['condition_report']['condition_tier']}")
print(f"Front Defects: {[d['label'] for d in res_cond['condition_report']['front_defects']]}")
print(f"Back Defects: {[d['label'] for d in res_cond['condition_report']['back_defects']]}")
print(f"Total Defects Count: {res_cond['condition_report']['defect_count']}")
print(f"Base Price USD: ${res_cond['pricing']['base_price_usd']} -> Final USD: ${res_cond['pricing']['final_price_usd']}")
print(f"Base Price IDR: Rp {res_cond['pricing']['base_price_idr']:,} -> Final IDR: Rp {res_cond['pricing']['final_price_idr']:,}")

print("\n>>> ALL TESTS SUCCESSFUL! <<<")

