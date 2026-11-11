# Chạy và đọc bài

Lê Thanh Tùng — 2A202603819 — L3B. Bài chạy bằng CLI, không có yêu cầu deploy web.

## Chạy lại

Project chỉ dùng Python standard library, cần Python 3.10 trở lên. Trên máy đang làm bài đã có môi trường `.venv`; dùng trực tiếp:

```bash
source .env
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python -m unittest discover -s bonus -p 'test_*.py' -v
.venv/bin/python run.py 'GitHub Actions hiện có sự cố không? Xem incident gần đây và dẫn nguồn.'
```

Nếu clone trên máy khác, tạo venv bằng Python 3.10+, copy `.env.example` thành `.env` nếu chưa có, rồi điền provider/model/key. Lần làm bài này dùng `openrouter` và `openai/gpt-4o-mini` cho cả agent lẫn judge. Không đưa key vào file Python.

Đọc `NOTES.md` trước khi chạy lại eval. Các bộ kết quả của bản chốt v2 đã được lưu đầy đủ; muốn đo thêm thì dùng tên file khác:

```bash
source .env
.venv/bin/python evals/run_evals.py --workers 1 --max-steps 8 --output replay_core.json
.venv/bin/python evals/run_evals.py --bonus --workers 1 --max-steps 16 --output replay_bonus.json
```

Unit tests không gọi mạng. Các lệnh `run.py` và eval gọi LLM thật, dùng quota API. Mặc định tools đọc snapshot; thêm `--mode live` vào `run.py` để truy cập status API thật. Snapshot không phải tình trạng dịch vụ tại thời điểm chạy lệnh.

Bản chốt v2 đã chấm đủ 22 case chính và 10 bonus. Chạy `.venv/bin/python evidence/compare.py` để kiểm tra cặp kết quả, hash các file giữ nguyên và đọc số calls/token/cost. Không cần key cho lệnh này hoặc cho việc đọc JSON đã lưu.

Các thử nghiệm v3–v5 nằm trong `evidence/iterations`, không phải code đang chạy ở thư mục gốc. v5 thử `gpt-4.1-mini` và adapter có tùy chọn giới hạn đầu ra 2048 token; lượt đầy đủ vẫn gặp HTTP 402. Xem [EXPERIMENTS.md](evidence/EXPERIMENTS.md) trước khi thử lại. Bản chốt dùng adapter gốc và `gpt-4o-mini`, không dùng tùy chọn đó. Hiện đã dừng gọi API theo yêu cầu; chỉ chạy thêm khi có quota và cần đo lại. Không cần deploy web hay giữ tiến trình nào chạy nền.

## Những chỗ cần hiểu trong agent.py

1. `messages` giữ toàn bộ hội thoại. Assistant message được thêm nguyên vẹn trước tool results để provider nhận đúng cặp yêu cầu/kết quả.
2. Một response có thể chứa nhiều tool calls. Loop xử lý hết và trả từng `tool_call_id`; một step vẫn chỉ là một lần gọi model.
3. JSON lỗi hoặc tool timeout trở thành observation để model phản hồi. Lỗi provider, câu trả lời rỗng hoặc `finish=length` kết thúc bằng `error`.
4. `max_steps` dùng chung cho điều tra và sửa câu trả lời. Kiểm tra nguồn không được tự mở một budget mới.
5. Chỉ URL từ `get_incident_details` thành công được lưu. Thiếu URL thì có event `validation_missing_source` và yêu cầu sửa trong lượt còn lại. Có URL không chứng minh mọi câu trong answer đều đúng.
6. Với 429, code giới hạn ba lần thực thi cho cùng tool/provider và đọc `Retry-After` dạng số hoặc HTTP date. Chờ tối đa hai giây mỗi lần; lâu hơn thì dừng request đó và báo chưa biết. Trace vẫn ghi cả yêu cầu bị chặn.
7. `tools.schemas` và `tools.system_prompt` cho phép dùng cùng loop với tools bonus. Không có tên case, incident ID hoặc đáp án eval được gắn cứng trong agent.

## Demo ngắn

- Mở case H7 trong `eval_before.json`: Cloudflare trả timeout nhưng answer vẫn giả định có thể coi dịch vụ hoạt động.
- Đối chiếu cùng case trong `eval_after.json`, đọc cả tool results, answer và lời giải thích của judge.
- Mở H1 để theo dõi việc đọc incident liên quan qua nhiều model steps.
- Mở test nguồn thiếu trong `tests/test_validation.py` để thấy vì sao không chỉ kiểm tra `finish=stop`.
- Nếu trình bày bonus, đọc B2/B3/B4: pagination, retry một lần thành công và lỗi kéo dài. Kết quả cụ thể nằm trong `eval_bonus.json`.

Code và tài liệu có Codex hỗ trợ; các số đo lấy từ lần chạy thật. Người nộp cần tự đọc và giải thích được loop, trace và giới hạn của kiểm tra nguồn.
