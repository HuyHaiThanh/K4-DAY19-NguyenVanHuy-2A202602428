# Báo cáo Day 19 — Flat RAG vs GraphRAG

**Họ tên:** Nguyễn Văn Huy  **MSSV:** 2A202602428  **Ngày:** 2026-10-05

Nguồn: `ket_qua_benchmark_kg.txt`, sinh lại nguyên trạng bằng `python bench_kg.py --judge` sau checklist cuối. Chat openai:gpt-4o-mini; embedding openai:text-embedding-3-small; top-k=3, chunk size=800, 176 chunks; graph **201 node / 380 cạnh** từ 18 Điều và 20 bài. Dùng ontology gợi ý, không xét bonus.

## 1. Chi phí (10 điểm)

```text
== Indexing (one-off)
pipeline  calls    in_tok  out_tok       USD  seconds
flat        176     56072        0   0.00112     37.7
graph       196     91958     4597   0.00926    101.5

== Querying (mean per question)
pipeline  recall  judge   in_tok  out_tok       USD  seconds
flat        0.43   1.00      694       47   0.00013     1.29
graph       0.78   1.67     4534       76   0.00072     1.66
```

| Chỉ số | Flat | Graph | Graph / Flat |
| --- | ---: | ---: | ---: |
| Indexing USD | 0.00112 | 0.00926 | 8.27× |
| Indexing giây | 37.7 | 101.5 | 2.69× |
| Mỗi câu: USD | 0.00013 | 0.00072 | 5.54× |
| Mỗi câu: giây | 1.29 | 1.66 | 1.29× |
| Mỗi câu: in_tok | 694 | 4534 | 6.53× |

Tỷ lệ dùng số đã làm tròn trong output. Graph indexing gồm vector index dùng chung và 20 lời gọi trích tin, tăng khoảng $0.00814. Prompt graph chứa thêm facts và toàn văn khoản nên hỏi đáp đắt hơn. USD là ước tính theo bảng code, không phải hóa đơn; chi phí judge được đo riêng, không nằm trong hai bảng pipeline. Giây là thời gian API được metered, không phải toàn bộ wall-clock Neo4j/Python.

Với N câu: Flat ≈ $0.00112 + N×$0.00013; Graph ≈ $0.00926 + N×$0.00072. Không có điểm hòa vốn về tiền trong lần đo này vì cả hai thành phần của Graph đều cao hơn; cần cân nhắc lợi ích chất lượng.

## 2. Từng câu hỏi (10 điểm)

Judge có thang 0 sai, 1 một phần, 2 đúng.

| Câu | Loại | Flat recall / judge | Graph recall / judge | Thắng | Vì sao |
| --- | --- | --- | --- | --- | --- |
| Q1 | single-hop-law | 1.00 / 2 | 1.00 / 2 | Hòa chất lượng | Đều đúng định nghĩa tiền chất. |
| Q2 | single-hop-news | 1.00 / 2 | 1.00 / 2 | Hòa chất lượng | Đều nêu đúng Trần Thanh Tuấn và Trần Minh Tâm. |
| Q3 | cross-kb | 0.00 / 0 | 1.00 / 2 | Graph | Nối được 36 tháng tù với Điều 251, khoản 1; Flat không đủ thông tin. |
| Q4 | cross-kb | 0.00 / 0 | 0.67 / 1 | Graph một phần | Đúng hành vi và Điều, nhưng sai khung tối đa thành 07 năm. |
| Q5 | cross-kb-multi-hop | 0.60 / 1 | 1.00 / 2 | Graph | Nêu Điều 250 khoản 4; Flat chỉ ghi “khoản b)” và thiếu số Điều. |
| Q6 | aggregation | 0.00 / 1 | 0.00 / 1 | Không bên nào đủ | Các mô tả liên quan MDMA nhưng thiếu tên chuẩn và chưa thể hiện đủ vụ theo gold. |

Đã đọc cả 12 câu trả lời Per question. Recall chỉ đối sánh từ khóa: Q6 có nội dung liên quan nhưng dùng tên viết tắt/mô tả khác nên recall bằng 0. Judge=1 không chứng minh danh sách đủ hoặc mọi chi tiết đúng.

## 3. Phân tích lỗi (20 điểm)

Các Cypher và kết quả kiểm chứng cần thiết được ghi trực tiếp bên dưới. Kiểm tra context bổ sung dùng doc_ids rỗng để cô lập graph retrieval, không phải toàn bộ prompt đã dùng trong benchmark.

### Lỗi E2: Sai khung tối đa dù graph có khoản luật

- **Hiện tượng:** Q4 Graph trả tối đa 07 năm, recall=0.67, judge=1; corpus có khoản 4 Điều 255 nêu 20 năm hoặc tù chung thân.
- **Bằng chứng:** nguyên văn Q4 Graph:

> Giang hồ 'Hoàng Nato' bị bắt về hành vi tổ chức sử dụng trái phép chất ma túy. Hành vi này có thể bị phạt tù tối đa 07 năm theo Điều 255 Bộ luật Hình sự.

```cypher
MATCH (a:Article)-[:HAS_CLAUSE]->(cl:Clause)
WHERE a.doc_id = 'blhs-dieu-255'
RETURN a.id AS article, cl.number AS number, cl.penalty AS penalty, cl.text AS text
ORDER BY number;
```

Kết quả kiểm chứng: khoản 1 `phạt tù từ 02 năm đến 07 năm`; khoản 2 `phạt tù từ 07 năm đến 15 năm`; khoản 3 `phạt tù từ 15 năm đến 20 năm`; khoản 4 `phạt tù 20 năm hoặc tù chung thân`; khoản 5 hình phạt bổ sung. Khoản 4 thực sự có trong graph. Tái gọi `context(question_Q4, [])` trả khoản 1 Điều 255 nhưng không có khoản 4.

- **Nguyên nhân:** KG-3 lọc khoản 1 hoặc khoản MENTIONS chất của vụ. Các khoản tăng nặng Điều 255 không nhắc chất cụ thể nên bị loại; LLM dùng trần khung cơ bản để trả khung tối đa. Snapshot không lưu chính xác prompt benchmark, nhưng điều kiện Cypher và tái truy xuất xác nhận cơ chế thiếu luật.
- **Đề xuất sửa:** trong `src/graph.py`, khi hỏi tối đa/khung cao nhất, lấy mọi khoản hình phạt của Điều liên quan; hoặc mô hình hóa ngưỡng phạt số và cờ chung thân/tử hình. Đánh đổi: tăng token hoặc thêm công việc parsing và kiểm tra ngoại lệ. Phải benchmark lại sau sửa. Chưa sửa code trong lượt phân tích để giữ số liệu khớp code đã đo.

### Lỗi E3: Một loại chất tạo thành nhiều node

- **Hiện tượng:** tồn tại hai biến thể chữ hoa/thường của cùng loại chất.
- **Bằng chứng:**

```cypher
MATCH (s:Substance)
WITH toLower(s.name) AS normalized, collect(s.name) AS names, count(*) AS n
WHERE n > 1
RETURN normalized, names, n ORDER BY normalized;
```

```text
ketamine        ['Ketamine', 'ketamine']                  n=2
methamphetamine ['methamphetamine', 'Methamphetamine']  n=2
```

- **Nguyên nhân:** Substance dùng khóa name; luật dùng danh sách chuẩn, nhưng helper tin chỉ nhắc tên chuẩn trong prompt, không linking tên chất sau LLM. MERGE/constraint không gộp hai chuỗi khác nhau. Lỗi thuộc chuẩn hóa và khóa định danh KG-2/ontology.
- **Đề xuất sửa:** canonical hóa chất trước `add_news_case` hoặc thêm khóa chuẩn hóa và aliases riêng; dùng normalizer dành cho chất với bảng alias. Không gộp tên chung “ma túy” vào một chất cụ thể. Chuẩn hóa chữ hoa ít chi phí; fuzzy/alias cần tránh nối sai. Dựng lại graph, chạy truy vấn trùng và benchmark trước/sau.

### Quan sát bổ sung

Lần chạy cuối, `MATCH (k:Case) WHERE NOT (k)-[:CHARGED_WITH]->() RETURN k.name, k.doc_id` trả 0 bản ghi. Không suy rằng mọi cạnh đều đúng vì linking có thể gán sai; charge rỗng ở cán bộ/người liên quan cũng không tự động là lỗi.

Q6 có năm node Case nối MDMA: vụ Lê Minh Thành, Sầm Sơn, Viện Pháp y tâm thần và hai tên vụ của Cái Quang Huy. Câu trả lời Graph chỉ có ba mô tả. Cần phân giải vụ trước khi coi số node là số vụ ngoài đời; không suy rằng cả năm node đều là vụ độc lập.

## 4. Kết luận (5 điểm)

KG có ích với câu nối tin và luật: Q3 từ recall 0/judge 0 lên 1/2, Q5 từ 0.60/1 lên 1/2. Q1–Q2 chỉ cần một nguồn nên Flat đạt cùng chất lượng với chi phí thấp hơn. Q4 vẫn sai khung tối đa và Q6 vẫn recall 0/judge 1; thêm graph không bảo đảm trả đúng. Cân nhắc KG khi chất lượng nối nguồn bù được chi phí dựng 8.27× và mỗi câu 5.54×, cùng công việc kiểm soát chuẩn hóa/truy xuất. Sáu câu hỏi với một judge LLM chưa đủ khái quát sang mọi dữ liệu.

## 5. Tự kiểm (5 điểm)

Output checklist cuối: pytest → --check → --judge, chạy đúng thứ tự trước commit/push:

```text
$ python -m pytest tests/ -q
48 passed in 0.06s
$ python bench_kg.py --check
[OK] Dữ liệu: 18 điều luật, 20 bài báo
[OK] KG-1 link_entity
[OK] Neo4j kết nối được
[OK] KG-2 build_graph: 148 node / 293 cạnh, đường xuyên 2 KB dài 2 cạnh
[OK] KG-3 context: 22 dữ kiện, có Điều 251
[OK] KG-4 GraphRAGAgent.answer
[OK] Chi phí check: 1 lần gọi LLM, $0.00078.
```

Sau --check đã chạy lại --judge để dựng graph đầy đủ và sinh file cuối. Kiểm tra tổng 201 node và 380 cạnh, khớp benchmark. Không còn NotImplementedError trong src/graph.py; .env/.venv không được Git theo dõi, được gitignore; quét lịch sử không thấy chuỗi API key theo mẫu sk-/AIza đã kiểm tra.

**Ba ảnh đã có:** [kg_count.png](img/kg_count.png), [kg_cross_kb.png](img/kg_cross_kb.png), [kg_my_case.png](img/kg_my_case.png). Người chọn **Cái Quang Huy**, đã kiểm chứng đường tới Điều 250. Ảnh count có 7 label, tổng 201 node. Ảnh graph thấy ô truy vấn và Results overview; ảnh hiện chỉ có khung kết quả Neo4j, chưa thấy toàn cửa sổ trình duyệt, và truy vấn ảnh vụ riêng bị rút gọn. Do đó chưa xác nhận đạt đầy đủ quy cách ảnh của LAB_GUIDE 8.2; cần chụp lại nếu người chấm yêu cầu đúng toàn cửa sổ.

## Vấn đề gặp phải (không tính điểm)

`cua.getState()` trả `{"apps":[],"browsers":[]}`; thử mở Chrome tới trang nộp bài trả `Browser is not available: chrome`. Ba ảnh người dùng cung cấp đã được đưa nguyên trạng vào repo. Không có browser để xác nhận thao tác nộp link tại `https://vlearn.dev/course/k04-l34-p2-t3/reader?day=D05&part=lab-634ab997-submit`; chưa xác nhận nộp bài thành công.
