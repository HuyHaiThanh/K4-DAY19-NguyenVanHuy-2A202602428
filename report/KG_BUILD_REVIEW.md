# KG-1 và KG-2 — kiểm chứng và tự review

Ngày kiểm chứng: 2026-10-05. Phạm vi: ontology gợi ý đã chọn, chưa triển khai KG-3/KG-4. Tài liệu này cập nhật trạng thái thực nghiệm sau bản thiết kế `ONTOLOGY.md` viết trước khi code.

## Thay đổi

- `link_entity`: chuẩn hóa hai phía, ưu tiên khớp chính xác, sau đó `difflib.get_close_matches(n=1, cutoff=0.8)`. Trả tên gốc trong `known`, hoặc `None`. Bỏ tên chuẩn hóa rỗng; khi hai tên chuẩn hóa giống nhau, giữ tên xuất hiện đầu tiên.
- `build_graph`: tạo constraints, trích luật bằng regex và nạp luật trước; lấy danh sách tội chuẩn không trùng; trích từng tin với `json_mode=True`, rồi ghi bằng helper HINT. Hàm không tự reset; `bench_kg.py --build` reset graph trước khi gọi.
- Giữ nguyên tests, benchmark và helper HINT. Node tài liệu `Article`, `Clause`, `Case` có `doc_id`; các node dùng chung theo helper không có một `doc_id` riêng.

## Kết quả thực tế

```text
python -m pytest tests/test_graph.py -k LinkEntity -v
5 passed, 2 deselected

python -m pytest tests/test_base.py tests/test_graph.py -k "not GraphRAGAgent" -q
46 passed, 2 deselected

python bench_kg.py --build --limit 2
[provider] chat = openai:gpt-4o-mini | embedding = openai:text-embedding-3-small
Đã nạp 18 điều luật + 2 bài báo: 148 node / 292 cạnh
2 lần gọi LLM, $0.00096, 13.1s
```

USD là ước tính do code tính, thời gian là số đo LLM được lệnh in ra. Đây là nạp graph nhỏ, không phải benchmark Flat RAG vs GraphRAG; lệnh build không gọi embedding.

| Label | Số node | Quan hệ | Số cạnh |
| --- | ---: | --- | ---: |
| Clause | 99 | MENTIONS | 169 |
| Article | 18 | HAS_CLAUSE | 99 |
| Crime | 13 | DEFINES | 13 |
| Substance | 10 | INVOLVED_IN | 5 |
| Person | 5 | INVOLVES | 4 |
| Case | 2 | LOCATED_IN | 1 |
| Location | 1 | CHARGED_WITH | 1 |

Đã kiểm tra bằng driver Neo4j với Cypher trong ảnh:

```cypher
MATCH (a), (b)
WHERE a.doc_id STARTS WITH 'blhs-' AND b.doc_id STARTS WITH 'news-'
MATCH p = shortestPath((a)-[*..4]-(b))
RETURN a.doc_id AS law, b.doc_id AS news, length(p) AS hops LIMIT 5;
```

Có 5 bản ghi: từ `blhs-dieu-247`/`blhs-dieu-248` tới `news-100260918080821054`, dài 3–4 cạnh. Tuy nhiên đường này có thể đi qua chất chung nên chưa chứng minh nối đúng tội danh. Kiểm tra bổ sung:

```cypher
MATCH (p:Person)-[:INVOLVED_IN]->(k:Case)-[:CHARGED_WITH]->(c:Crime)<-[:DEFINES]-(a:Article)
RETURN p.name AS person, k.doc_id AS news, c.name AS crime, a.id AS article;
```

Kết quả: Kim Xuân Tuấn, Trịnh Vũ Kiên, Nguyễn Quang Hưng, Lê Minh Thành đều đi từ bài `news-100260918080821054`, qua `mua bán trái phép chất ma túy`, tới `Điều 251 BLHS`.

```cypher
MATCH (n)
WHERE any(l IN labels(n) WHERE l IN ['Article','Clause','Case']) AND n.doc_id IS NULL
RETURN count(n) AS n;
```

Kết quả: `n = 0`. Đủ 7 label và 7 loại cạnh theo ontology. Chưa chụp ảnh Browser; có thể xem graph nhỏ hiện còn ở `http://localhost:7474`.

## Tự phản biện

1. **Test pass chưa đủ chứng minh graph đúng:** 5 test chỉ kiểm tra linking. Đã bổ sung kiểm tra Neo4j thật cho số lượng, nguồn tài liệu và cầu nối qua Crime; chưa kiểm chứng câu trả lời Q1–Q6 vì KG-3/KG-4 còn TODO.
2. **Có vụ không nối luật:** truy vấn `MATCH (k:Case) OPTIONAL MATCH (k)-[:CHARGED_WITH]->(c:Crime) RETURN k.name, k.doc_id, collect(c.name)` trả `Vụ góp tiền mua ma túy tại Hà Nội` với tội mua bán và `Vụ vận chuyển ma túy của Cái Quang Huy` với danh sách tội rỗng; cả hai mang `doc_id = news-100260918080821054`. Bài này có đoạn giới thiệu vụ Cái Quang Huy ở cuối. Quan sát cho thấy trích xuất đã lấy phần bài liên quan; chưa đủ chứng cứ để quy toàn bộ nguyên nhân tội rỗng cho linking hay LLM nếu không lưu JSON gốc. Hướng sửa sau: tách nội dung chính hoặc yêu cầu bằng chứng cho từng vụ và ghi nhận tên tội bị loại. Đánh đổi: thay đổi preprocessing/prompt và có thể tăng token. Không tự ép gán Điều 250 từ tên người.
3. **Fuzzy match chỉ đo giống chuỗi:** có thể chọn tội gần tên nhưng khác ý nghĩa. Giữ ngưỡng theo đề; cần kiểm tra tên đầu vào và nguồn trước khi tăng độ bao phủ.
4. **Helper có giới hạn:** JSON lỗi có thể bị bỏ qua; khóa theo tên có thể trùng/gộp sai, thiếu lịch sử nguồn. Không sửa helper ngoài phạm vi hai TODO trong bước này; những hạn chế này cần tiếp tục phân tích khi benchmark.
5. **Không tuyên bố toàn bộ lab đã pass:** 2 test GraphRAGAgent chưa thuộc phạm vi hiện tại. Chưa chạy `--check` đầy đủ, nạp toàn bộ tin, benchmark `--judge`, hay chụp ba ảnh nộp bài.

## Bước tiếp theo

Triển khai KG-3: từ seed và Case đi qua Crime tới Article/Clause; kiểm tra trường hợp khung tối đa và truy vấn tổng hợp. Sau đó KG-4 ghép chunk và graph facts vào prompt. Các số liệu trên có thể thay đổi khi chạy lại vì LLM trích tin không hoàn toàn ổn định.
