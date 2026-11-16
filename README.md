# DSI433 Group 04 · Risk Appetite Scenario Tool

Live demo ของสไลด์ 9 (Reinsurance Analysis) จากโปรเจกต์ Thailand Flood CAT Modeling

- `app.py` คำนวณผล reinsurance ด้วย Monte Carlo 100,000 ปี (SEED 433) แบบเดียวกับ `DSI433_Full_CAT_Modeling.ipynb` ส่วนที่ 11
- `template.html` คือหน้าตาเว็บแอป ตัวเลขถูกเติมจาก `app.py`
- `data/province_rp_losses.csv` คือผลของ Track A (77 จังหวัด × 8 return period)

## Deploy บน Streamlit Community Cloud
share.streamlit.io → Create app → เลือก repo นี้ · branch `main` · main file `app.py` → Deploy

## รันในเครื่อง
```
pip install -r requirements.txt
streamlit run app.py
```

ตัวเลขเป็นความเสียหายทางเศรษฐกิจจากแบบจำลองภายใต้สมมติฐาน (พอร์ตสมมติ 1% ของมูลค่าทรัพย์สิน จ่ายสินไหม 80%) ยังไม่รวมเบี้ยประกันภัยต่อ
