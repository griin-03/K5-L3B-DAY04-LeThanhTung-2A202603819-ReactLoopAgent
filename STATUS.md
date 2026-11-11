# Trạng thái bản nộp Day 04

Lê Thanh Tùng — **2A202603819** — **L3B**.

Bản chốt là **v2**, khớp [source snapshot](evidence/after/agent.py) và các file eval gốc:

| Hạng mục | Kết quả |
|---|---|
| Unit tests | 54 chính + 3 bonus, đều qua |
| `eval_before.json` | 22/22 case, 80.68/100 |
| `eval_after.json` | 22/22 case, 76.36/100 |
| `eval_bonus.json` | 10/10 case, 71.50/100; bonus tham khảo 10.72/15 |
| Báo cáo | `NOTES.md`, đủ 5 mục |
| CLI | Python standard library; không cần deploy web |

Cặp before/after cùng provider/model/judge/snapshot/dataset và `max_steps=8`; tổng điểm đều khác `null`. Không ghép case từ nhiều lần chạy. H7 tăng từ 60 lên 75, nhưng điểm tổng giảm 4.32; không tuyên bố vượt 85 hoặc coi điểm eval là điểm lab.

Các thử nghiệm mới hơn và các lượt lỗi HTTP 402 được giữ trong [EXPERIMENTS.md](evidence/EXPERIMENTS.md), tách khỏi bản chốt. Xem [NOTES.md](NOTES.md) để đọc trace, so sánh và giới hạn; [HOW_TO_RUN.md](HOW_TO_RUN.md) để chạy bài.

Việc còn lại khi nộp: người học đọc và giải thích được code, rồi tự dán link repo vào bài Day 04 trên LMS. Repo không xác nhận thời hạn hay trạng thái nộp trên LMS.
