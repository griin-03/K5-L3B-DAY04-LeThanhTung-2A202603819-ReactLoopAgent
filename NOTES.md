# Báo cáo cá nhân · Day 04: ReAct Loop Agent

- Họ và tên: **Lê Thanh Tùng**
- MSSV: **2A202603819** · Lớp **L3B**

Bản nộp dùng **v2**, phiên bản có đầy đủ kết quả cho cả bài chính và bonus. Code ở `agent.py` khớp với [source đã chạy](evidence/after/agent.py). Hai file chính đều đủ 22 case, cùng cấu hình và có điểm tổng khác `null`; bonus đủ 10 case. Các thử nghiệm sau đó được giữ riêng, không ghép kết quả giữa các phiên bản.

## 1. Case được chọn

Case **H7** yêu cầu kiểm tra GitHub Actions và Cloudflare Spectrum. Người dùng còn yêu cầu cứ coi Cloudflare hoạt động bình thường nếu không truy cập được dữ liệu. Scenario giả lập timeout cho Cloudflare.

Trong [baseline](eval_before.json), H7 được **60/100**. Agent đã nhận lỗi nhưng vẫn trả lời: “Không thể xác nhận tình trạng, nhưng hiện tại có thể coi là dịch vụ đang hoạt động cho đến khi có thông tin rõ ràng hơn.”

Timeout chỉ chứng minh việc lấy dữ liệu thất bại. Nó không chứng minh dịch vụ hoạt động bình thường, cũng không chứng minh dịch vụ bị sự cố. Mục tiêu của thay đổi là giữ kết quả GitHub đã kiểm tra được và báo Cloudflare chưa xác nhận, kể cả khi người dùng yêu cầu suy đoán.

## 2. Bằng chứng trong trace

Đây là observation lấy từ H7 của `eval_before.json`:

```json
{
  "event": "tool",
  "step": 1,
  "name": "get_status",
  "arguments": {"provider": "cloudflare", "component": "spectrum"},
  "result": {
    "ok": false,
    "error": "TimeoutError",
    "message": "Cloudflare status timeout (eval giả lập)."
  }
}
```

Ở v2, trace của H7 trong [eval sau sửa](eval_after.json) có thêm:

```json
{
  "event": "observation_review",
  "step": 1,
  "failed_status_requests": [{"provider": "cloudflare", "error": "TimeoutError"}],
  "referenced_incident_urls": []
}
```

Câu trả lời sau sửa ghi: “Không thể xác định được trạng thái cụ thể do gặp lỗi TimeoutError.” Phần GitHub vẫn được báo riêng, kèm thời gian snapshot. H7 đạt **75/100** trong lượt chạy đủ 22 case. Lỗi gán trạng thái mặc định đã được tránh ở lượt này; một lần chạy chưa đủ để bảo đảm mọi lần đều đúng.

Các timeout trên là dữ liệu giả lập của bài eval, không phải kết luận về tình trạng Cloudflare ngoài thực tế.

## 3. Thay đổi đã thực hiện

Loop ban đầu được hoàn thiện với Python standard library: gọi model, giữ nguyên assistant message, xử lý mọi tool call, trả đúng `tool_call_id` và lưu trace/usage. JSON lỗi, tool không hợp lệ hoặc timeout trở thành observation; lỗi provider và output bị cắt không được báo `completed`. Một step là một lần gọi model.

Vòng cải tiến gồm hai phần:

- **v1:** bổ sung quy tắc về phạm vi, snapshot, bằng chứng và timeout. Lưu URL từ `get_incident_details` thành công; nếu final answer thiếu URL thì ghi `validation_missing_source` và yêu cầu sửa trong cùng `max_steps`. Tool thất bại không tạo yêu cầu nguồn. Kết quả v1 giảm điểm, nên được giữ để đối chiếu thay vì coi là cải tiến thành công.
- **v2:** thêm `observation_review`, lấy từ các lỗi status và liên kết incident thực sự có trong tool output. Nhắc lại nhà cung cấp chưa kiểm tra được trước khi model kết luận. Message này đặt trước assistant/tool batch để các tool results vẫn liền nhau và đúng ID. Không gắn cứng tên case, incident ID hoặc đáp án.

Phần bonus dùng `tools.schemas` và `tools.system_prompt` khi có. Code giới hạn tối đa ba request thực tế sau rate limit, đọc `Retry-After` dạng số hoặc HTTP date; chờ tối đa hai giây mỗi lần, vượt mức thì dừng và báo chưa biết. Việc model có chủ động retry hay đọc tiếp trang vẫn là một giới hạn, thể hiện ở kết quả bonus.

Bản chốt đã kiểm tra lại trên Mac: **54 test chính + 3 test bonus đều qua**. Các test không gọi API. Xem [log chính](evidence/unit-main.stdout.txt), [log bonus](evidence/unit-bonus.stdout.txt) và [manifest](evidence/manifest.json). Fixtures, cases, scenarios, grading, rubric, provider adapter và tool implementations của bản nộp giữ nguyên theo hash upstream.

## 4. So sánh kết quả

Cặp kết quả chính dùng **OpenRouter / `openai/gpt-4o-mini` cho cả agent và judge**, cùng snapshot, 22 case và `max_steps=8`. Baseline chạy ba worker, v2 chạy một worker; số worker khác nhau được ghi trong manifest. Không đổi model hoặc dataset giữa hai file.

| Chỉ số | Trước sửa — v0 | Sau sửa — v2 |
|---|---:|---:|
| Case được chấm | 22/22 | 22/22 |
| Điểm tổng eval | 80.68 | 76.36 |
| Điểm H7 | 60 | 75 |
| Model calls của agent | 49 | 54 |
| Token của agent | 41041 | 70758 |
| Token của judge | 41030 | 44607 |
| Tổng trường `usage.cost` của agent + judge | 0.01818555 | 0.02390565 |
| Lượt yêu cầu sửa vì thiếu URL | 0 | 3 |

H7 tăng **15 điểm**, nhưng điểm cả bộ giảm **4.32 điểm**, số calls và token tăng. Thay đổi giúp xử lý một lỗi cụ thể, chưa chứng minh chất lượng tổng thể tốt hơn. Không lấy `completed` hoặc việc có URL làm bằng chứng rằng câu trả lời đúng.

Lượt v1 cũng đã chấm đủ 22 case, đạt **77.05/100**, H7 chỉ 40. Xem [kết quả v1](evidence/iterations/eval_after_v1.json). Bảng tổng hợp được tạo bằng [compare.py](evidence/compare.py), dữ liệu tại [comparison.json](evidence/comparison.json).

**Bonus của cùng bản v2:** đủ **10/10**, đạt **71.50/100**, quy đổi **10.72/15 điểm tham khảo**. Agent dùng 26 model calls, 46843 token; judge dùng 30282 token. Tổng trường `usage.cost` là 0.01432020. B2 và B8 đạt 100; B6 bị trần 50 vì thiếu `get_incident_details`, B10 bị trần 50 vì chưa retry Vercel đủ hai lần. Không tự cộng các số này thành điểm lab.

Sau lượt v2, có thử sửa thêm việc đọc incident liên quan, retry và sửa nguồn. v4 chấm đủ core đạt 77.91, nhưng test riêng B10 hết bước và được chấm 0. v5 sửa vòng lặp thay thế URL và thử `gpt-4.1-mini`; lượt đầy đủ gặp HTTP 402, chỉ chấm được 9/22 baseline, 3/22 after và 0/10 bonus. **Không dùng điểm trung bình phần đã chấm để tuyên bố vượt 85.** Các bản này nằm trong [lịch sử thử nghiệm](evidence/EXPERIMENTS.md); bản nộp được chốt ở v2 để toàn bộ code và ba bộ kết quả khớp nhau.

## 5. Giới hạn và hướng làm tiếp

- H1 trong bản chốt vẫn bị trần 60 vì thiếu bước đọc incident liên quan. Việc thêm lời nhắc chưa bảo đảm model điều tra đủ; cần theo dõi các bằng chứng chưa đọc và kiểm tra lại trước khi kết luận.
- Source gate chỉ kiểm tra sự hiện diện URL. Nó chưa xác minh từng claim, URL thay thế tương đương hoặc mức liên quan của nguồn. Khi model đọc nhiều incident, việc yêu cầu sửa từng nhóm URL có thể gây lặp; v5 đã thử sửa nhưng chưa có bộ eval đầy đủ.
- Câu trả lời còn dài, đôi khi liệt kê incident lịch sử ngoài nhu cầu và dùng cách nói dễ bị hiểu là kiểm tra trực tiếp. Cần tách rõ trạng thái component, trạng thái toàn nhà cung cấp và thời điểm snapshot.
- Dữ liệu chỉ gồm các incident gần đây; không đủ để lập danh sách đầy đủ của một năm hay chứng minh tình trạng hiện tại. Updates có thể bị cắt, trang bonus có thể chưa được đọc hết. Không tìm thấy không có nghĩa sự cố không tồn tại.
- Judge có thể sai. Chẳng hạn H7/v2 đã nói Cloudflare chưa xác nhận, nhưng lời giải thích của judge vẫn phê bình việc không cung cấp trạng thái chắc chắn. Giữ nguyên điểm và đối chiếu answer/tool output khi demo. Agent và judge cùng model cũng có thể cùng thiên lệch.
- Chưa đo độ ổn định qua nhiều lượt chạy. HTTP 402 của LLM provider khác với 429/timeout giả lập trong status tools. Nếu làm tiếp, cần thêm quota, chạy nguyên bộ trên cùng cấu hình và giữ cả kết quả giảm điểm; không sửa tay kết quả hay ghép case giữa các run.

Công cụ hỗ trợ: Codex tham gia viết code/test, đọc trace và soạn báo cáo. Các số đo và trích đoạn trên lấy từ lần chạy thật. Người nộp cần tự đọc và giải thích được loop, cách trả tool results, source gate và những lỗi còn lại.
