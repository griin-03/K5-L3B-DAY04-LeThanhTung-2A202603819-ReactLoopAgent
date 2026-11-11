# Các lượt thử ngoài bản chốt

Bản nộp ở thư mục gốc là **v2**, dùng `gpt-4o-mini` cho agent và judge. Cả before, after và bonus đều chấm đủ, khớp source snapshot. Các file dưới đây giữ lại quá trình thử, bao gồm kết quả giảm điểm và lỗi quota. Không ghép case giữa các run, không sửa điểm trong JSON.

| Phiên bản/lượt | Source | Kết quả thật |
|---|---|---|
| v0 ban đầu | [before/agent.py](before/agent.py) | [22/22, 80.68](iterations/eval_before_v0_gpt4omini.json) |
| v1 | [source v1](iterations/v1-agent.py) | [22/22, 77.05](iterations/eval_after_v1.json) |
| v2, lỗi hạ tầng lần trước | [source trước HTTP diagnostics](iterations/v2-unscored-agent.py) | [Core 20/22](iterations/eval_after_v2_unscored.json), [bonus 7/10](iterations/eval_bonus_unscored.json); tổng null |
| v2, hết quota | [source v2](iterations/v2-agent.py) | [Core 11/22](iterations/eval_after_v2_http402.json), [bonus 7/10](iterations/eval_bonus_v2_http402.json); tổng null |
| **v2, lượt đầy đủ được chọn** | [source v2](iterations/v2-agent.py) | [Core 22/22, 76.36](iterations/eval_after_v2_complete.json), [bonus 10/10, 71.50](iterations/eval_bonus_v2_complete.json) |
| v3, chỉ sửa hướng dẫn điều tra | [source v3](iterations/v3-agent.py) | Chạy riêng E1=95, H1=60, H2=100, H6=60, H7=75, A5=75, B10=50; không có điểm cả bộ |
| v4, chặn kết luận khi còn incident chưa đọc/request 429 còn retry được | [source v4](iterations/v4-agent.py) | [Core 22/22, 77.91](iterations/eval_after_v4_gpt4omini.json); [B10 riêng=0](iterations/check_v4_b10.json) do hết bước |
| v5, sửa yêu cầu dẫn nguồn và thử model khác | [source v5](iterations/v5-agent.py), [adapter thử nghiệm](iterations/v5-providers.py) | Các lượt dưới đây; chưa có cặp eval đầy đủ |

v4/B10 đã retry Vercel thành công, nhưng model đọc nhiều incident GitHub rồi sửa nguồn theo từng nhóm URL. Khi bổ sung nhóm đang thiếu, nó lại bỏ nhóm đã có, lặp đến `max_steps=16`. v5 yêu cầu giữ đồng thời toàn bộ URL đã đọc, thay vì chỉ gửi lại nhóm thiếu.

Với v5, các request mặc định bằng `gpt-4.1-mini` gặp HTTP 402 ngay từ đầu; các file `check_v5_e1.json`, `check_v5_h1.json`, `check_v5_b10.json` ghi lại lỗi này. Sau đó thử giới hạn đầu ra `MAX_OUTPUT_TOKENS=2048` ở adapter riêng, cho cả agent lẫn judge. Lượt riêng [E1 đạt 100](iterations/check_v5_capped_e1.json), [H1 đạt 94](iterations/check_v5_capped_h1.json), [B10 đạt 96](iterations/check_v5_capped_b10.json). Những số này chỉ thuộc từng case.

Lượt đầy đủ cùng model/budget mới gặp tiếp HTTP 402:

- [Baseline v0 trên gpt-4.1-mini](iterations/eval_before_v0_gpt41mini_unscored.json): 9/22 case được chấm, tổng null. Chạy source v0 trong thư mục tạm, giữ cùng adapter thử nghiệm như v5; không thay code gốc trong lúc eval.
- [After v5](iterations/eval_after_v5_gpt41mini_unscored.json): 3/22 case được chấm, tổng null.
- [Bonus v5](iterations/eval_bonus_v5_gpt41mini_unscored.json): 0/10 case được chấm, tổng/bonus null.

**Không kết luận v5 vượt 85 từ các case riêng hoặc trung bình phần đã chấm.** Sau khi dừng gọi API, chọn v2 làm bản nộp vì đây là phiên bản đã có đủ ba bộ kết quả khớp code. Không dùng số liệu v2 để mô tả hiệu năng v5. Provider adapter gốc được giữ lại ở thư mục chính; thay đổi giới hạn token chỉ nằm trong source thử nghiệm.

Unit tests của v5 từng qua 59 chính + 3 bonus; source test và log được lưu với tiền tố `v5-`/`unit-main-v5` trong `iterations`. Sau khi chốt lại v2 đã chạy lại 54 chính + 3 bonus đều qua, log chính thức nằm ở thư mục `evidence`.

Hash, cấu hình và source tương ứng của từng báo cáo nằm trong [report_index.json](report_index.json). Không có key hoặc thông tin số dư tài khoản trong các file này. Code thử nghiệm chưa phải phần runtime của bản nộp và không được dùng làm bằng chứng đã hoàn thành eval.
