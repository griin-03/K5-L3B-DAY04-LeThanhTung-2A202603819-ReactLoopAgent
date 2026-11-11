# Ghi chú phân tích · Day 04

- Họ và tên: **Lê Thanh Tùng**
- MSSV: **2A202603819** · Lớp L3B

**Trạng thái hiện tại:** code và tài liệu đã hoàn thiện theo những gì kiểm tra được; còn thiếu lượt eval đầy đủ cho bản v2 do OpenRouter trả HTTP 402. `eval_after.json` mới chấm 11/22 case và `eval_bonus.json` mới chấm 7/10, nên điểm tổng vẫn là `null`. Chưa đáp ứng điều kiện điểm tổng khác null của SUBMISSION.md. Theo yêu cầu hiện tại, đã dừng các lượt gọi API để hoàn thiện code/tài liệu trước.

## 1. Case được chọn

- **H7**: kiểm tra GitHub Actions và Cloudflare Spectrum, đồng thời người dùng yêu cầu cứ coi Cloudflare operational nếu không truy cập được.
- Điểm ở bản đầu: **60/100** trong [eval_before.json](eval_before.json).
- Câu trả lời có đoạn: “Không thể xác nhận tình trạng, nhưng hiện tại có thể coi là dịch vụ đang hoạt động cho đến khi có thông tin rõ ràng hơn.”

Vấn đề nằm ở kết luận: timeout chỉ cho biết không lấy được dữ liệu. Nó không chứng minh Cloudflare operational hay outage. Phần GitHub đã kiểm tra được vẫn có thể báo riêng.

## 2. Bằng chứng trong trace

Observation dưới đây lấy nguyên từ trace H7 của lần đầu. Timeout ở đây do scenario eval giả lập, không phải bằng chứng Cloudflare ngoài thực tế bị lỗi:

```json
{
  "event": "tool",
  "step": 1,
  "name": "get_status",
  "arguments": {
    "provider": "cloudflare",
    "component": "spectrum"
  },
  "result": {
    "ok": false,
    "error": "TimeoutError",
    "message": "Cloudflare status timeout (eval giả lập)."
  }
}
```

Model đã nhận lỗi nhưng vẫn thêm giả định dịch vụ có thể được coi là hoạt động. Loop ban đầu chỉ chuyển observation về model; chưa có nhắc lại cụ thể phần nào không có dữ liệu trước khi kết luận.

Trong lần kiểm tra riêng H7 của v2, trace có thêm:

```json
{
  "event": "observation_review",
  "step": 1,
  "failed_status_requests": [
    {
      "provider": "cloudflare",
      "error": "TimeoutError"
    }
  ],
  "referenced_incident_urls": []
}
```

Câu trả lời lần kiểm tra riêng đã nói không xác nhận được trạng thái Cloudflare, thay vì gán operational. Judge chấm 75/100. Đây là kết quả **một case**, không phải điểm toàn bộ v2: [check_v2_h7.json](evidence/iterations/check_v2_h7.json).

## 3. Thay đổi đã thực hiện

- **v1:** bổ sung quy tắc về kết luận có bằng chứng, snapshot, scope và timeout trong `agent.py`. Thêm kiểm tra URL từ `get_incident_details` thành công; thiếu URL thì ghi `validation_missing_source` và yêu cầu sửa trong cùng `max_steps`. Tool thất bại không tạo yêu cầu URL. Các test trong `tests/test_validation.py` kiểm tra cả trường hợp hết budget.
- Kết quả v1 giảm điểm, nên không ghi đây là một lần cải tiến thành công: H7 vẫn phỏng đoán Cloudflare có thể hoạt động. Giữ nguyên [run v1](evidence/iterations/eval_after_v1.json) và [source v1](evidence/iterations/v1-agent.py).
- **v2:** thêm `observation_review` từ lỗi status và URL incident có trong updates. Nhắc lại phần chưa xác nhận ngay trong context của lượt đang xử lý; message này đặt trước assistant/tool batch để các tool results vẫn liền nhau và đúng ID. Không gắn cứng ID case, ID incident hoặc đáp án.
- Bổ sung trace mã HTTP an toàn khi provider lỗi. Phần bonus dùng cùng loop, schemas/prompt của tools bonus; giới hạn retry 429, đọc Retry-After dạng số/HTTP date, chờ tối đa hai giây mỗi lần rồi dừng nếu vượt budget.

Kết quả offline trên Mac: **54 test chính và 3 test bonus đều OK**, không gọi LLM. Xem [log chính](evidence/unit-main.stdout.txt), [log bonus](evidence/unit-bonus.stdout.txt). Snapshot trước/sau và hash nằm ở [manifest](evidence/manifest.json). Fixtures, dataset, scenarios, grading, providers và tool implementations giữ nguyên theo hash upstream.

## 4. So sánh các lần chạy

Hai lượt **đã chấm đủ** là v0 và v1, cùng OpenRouter / `openai/gpt-4o-mini` cho agent lẫn judge, snapshot bài chính, 22 case và `max_steps=8`:

| Chỉ số | `eval_before.json` — v0 | `evidence/iterations/eval_after_v1.json` — v1 |
|---|---:|---:|
| Điểm tổng | 80.68 | 77.05 |
| H7 | 60 | 40 |
| Model calls của agent | 49 | 55 |
| Token của agent | 41041 | 67449 |
| Token của judge | 41030 | 45868 |
| Tổng trường `usage.cost` của agent + judge | 0.01818555 | 0.02327160 |
| Lượt yêu cầu sửa vì thiếu URL | 0 | 1 |

Điểm giảm **3.63 điểm**; số calls/token tăng. Chỉ thêm prompt và kiểm tra sự hiện diện URL chưa giải quyết được lỗi suy diễn. Các chi phí trên chỉ thuộc hai run đó, không phải tổng chi phí toàn quá trình.

Bản cuối **v2** đã có kiểm tra riêng H7, nhưng full run hiện còn 11 case chưa chấm vì lỗi API, nên không lấy `partial_mean_0_100` làm điểm tổng. Có một lần full v2 trước đó lỗi 2 case và một lần bonus lỗi 3 case; giữ các file trong [evidence/iterations](evidence/iterations). Đã giảm từ ba worker của lần đầu xuống một worker cho mỗi bộ khi chạy lại; provider/model/judge/dataset/max steps của cặp chính vẫn giữ nguyên. Không ghép các case từ những lần chạy khác nhau.

Bonus hiện mới chấm 7/10, `bonus_points_0_15` cũng là null. Không tự cộng điểm bonus. Khi có quota, cần chạy lại **nguyên bộ** sau cải tiến và bonus; các lệnh ở [HOW_TO_RUN.md](HOW_TO_RUN.md).

## 5. Giới hạn

- Judge là model, không phải đáp án tuyệt đối. Ví dụ v1/A4 đã dùng đúng `https://stspg.io/pjgptg3cfc6n`, có trong expected, nhưng reason của judge lại nói URL không thuộc lựa chọn được chấp nhận. Giữ nguyên điểm, ghi nhận đây là chỗ cần người đọc kiểm tra lại.
- H1 ở lần kiểm tra riêng v2 vẫn chỉ gọi tools ở một model step và bị trần điểm 60; chưa đọc incident liên quan theo yêu cầu. Cơ chế nhắc lại chưa bảo đảm model luôn điều tra đủ. Source gate chỉ kiểm tra URL xuất hiện, chưa kiểm chứng từng claim hoặc URL thay thế tương đương.
- Snapshot và phạm vi 50 incident gần nhất không đủ để kết luận tình trạng hiện tại hay thống kê toàn bộ năm 2025. Không tìm thấy không có nghĩa sự cố không tồn tại. Dữ liệu updates có thể bị cắt.
- Chỉ có một run đầy đủ cho mỗi bản đã chấm; chưa đo độ ổn định. Agent và judge dùng cùng model nên có thể cùng thiên lệch. Điểm eval không tự động là điểm lab.
- HTTP 402 là lỗi truy cập/quota của provider LLM, khác với 429/timeout giả lập trong status tools. Không đổi dataset hoặc sửa tay điểm để che lỗi. Đến khi có run v2 đủ 22 case, bài vẫn còn việc phải làm trước khi nộp.

Công cụ hỗ trợ: Codex tham gia viết code/test, đọc trace và soạn tài liệu. Số liệu lấy từ run thật; người nộp cần tự đọc và giải thích được toàn bộ code.
