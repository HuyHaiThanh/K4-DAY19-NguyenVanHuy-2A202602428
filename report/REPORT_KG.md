# Báo cáo Day 19 — Flat RAG vs GraphRAG

**Họ tên:** Nguyễn Văn Huy  **MSSV:** 2A202602428  **Ngày:** 2026-10-05

Thiết kế bonus: PenaltyFrame/HAS_PENALTY và chuẩn hóa tên chất. Benchmark mới: `ket_qua_benchmark_kg.txt`; baseline nguyên trạng: `ket_qua_benchmark_kg.hint.txt`, chạy bằng code ontology gợi ý ở commit `3c2c12c`. Cùng chat openai:gpt-4o-mini, embedding openai:text-embedding-3-small, top-k=3, chunk size=800, 176 chunks, 18 Điều và 20 bài. Graph mới **246 node / 425 cạnh**, đủ 8 label và 8 loại cạnh, trong đó 44 PenaltyFrame. Thiết kế ở ONTOLOGY.md.

## 1. Chi phí (10 điểm)

Bảng nguyên văn từ file benchmark mới:

```text
== Indexing (one-off)
pipeline  calls    in_tok  out_tok       USD  seconds
flat        176     56072        0   0.00112     39.1
graph       196     91958     4684   0.00931    104.6

== Querying (mean per question)
pipeline  recall  judge   in_tok  out_tok       USD  seconds
flat        0.43   1.00      694       47   0.00013     1.32
graph       0.89   1.83     4853       78   0.00077     2.20
```

| Chỉ số | Flat | Graph mới | Graph / Flat |
| --- | ---: | ---: | ---: |
| Indexing USD | 0.00112 | 0.00931 | 8.31× |
| Indexing giây | 39.1 | 104.6 | 2.68× |
| Mỗi câu: USD | 0.00013 | 0.00077 | 5.92× |
| Mỗi câu: giây | 1.32 | 2.20 | 1.67× |
| Mỗi câu: in_tok | 694 | 4853 | 6.99× |

Tỷ lệ dùng số đã làm tròn. Graph indexing dùng chung vector index và thêm 20 lời gọi trích tin, tăng khoảng $0.00819. PenaltyFrame tạo bằng regex không thêm lời gọi LLM, nhưng tăng thao tác Neo4j. Prompt có thêm facts và toàn văn khoản; câu hỏi tối đa lấy mọi khoản nên có thể đắt hơn baseline. Giây là thời gian lời gọi API metered, chưa tính toàn bộ thời gian Neo4j/Python. USD ước tính theo code, chưa đối chiếu hóa đơn; judge tính riêng, không cộng vào bảng pipeline.

Với N câu: Flat ≈ $0.00112 + N×$0.00013; Graph ≈ $0.00931 + N×$0.00077. Không có hòa vốn chỉ tính tiền vì Graph có cả hai thành phần cao hơn; lợi ích là chất lượng nối nguồn.

## 2. Từng câu hỏi (10 điểm)

Đã đọc cả 12 câu trả lời. Judge: 0 sai, 1 đúng một phần, 2 đúng và đủ theo LLM chấm; không phải chân lý độc lập.

| Câu | Loại | Flat recall / judge | Graph recall / judge | Thắng | Vì sao |
| --- | --- | --- | --- | --- | --- |
| Q1 | single-hop-law | 1.00 / 2 | 1.00 / 2 | Hòa | Cả hai đúng định nghĩa tiền chất; Flat rẻ hơn. |
| Q2 | single-hop-news | 1.00 / 2 | 1.00 / 2 | Hòa | Đều nêu đúng hai bị cáo tử hình; Graph thêm Điều 251. |
| Q3 | cross-kb | 0.00 / 0 | 1.00 / 2 | Graph | Nối 36 tháng với Điều 251 và khung 02–07 năm; Flat không đủ thông tin. |
| Q4 | cross-kb | 0.00 / 0 | 1.00 / 2 | Graph | Có khung cao nhất từ PenaltyFrame, trả 20 năm hoặc chung thân tại khoản 4 Điều 255. |
| Q5 | cross-kb-multi-hop | 0.60 / 1 | 1.00 / 2 | Graph theo chỉ số | Đúng Điều 250 khoản 4 và khung; nhưng thiếu Ketamine so với gold, cần thận trọng với judge=2. |
| Q6 | aggregation | 0.00 / 1 | 0.33 / 1 | Graph một phần | Nêu tên Lê Minh Thành, vẫn thiếu vụ Viện Pháp y tâm thần trong câu trả lời. |

Recall đối sánh từ khóa nên có thể bỏ qua tương đương ngữ nghĩa. Q5 must_include không có Ketamine nên recall=1 không có nghĩa mọi ý gold đều đủ; judge cũng chấm 2 dù thiếu chất này.

## 3. Phân tích lỗi (20 điểm)

Hai lỗi baseline E2/E3 đã được dùng để thiết kế và kiểm chứng cải tiến; vẫn ghi đủ hiện tượng, bằng chứng, nguyên nhân và sửa. Bằng chứng Cypher trước/sau nằm trong [bonus_before.json](bonus_before.json) và [bonus_after.json](bonus_after.json), không phải số liệu tự suy. Các query chỉ đọc graph. Context tái truy xuất dùng doc_ids=[] để cô lập graph, không phải toàn bộ prompt benchmark.

### E2: Thiếu khung cao nhất — đã sửa và đo lại

- **Hiện tượng:** Q4 baseline recall=0.67, judge=1; trả sai tối đa 07 năm dù graph có khoản 4 Điều 255.
- **Bằng chứng:** nguyên văn Q4 Graph trong file `.hint.txt`:

> Giang hồ 'Hoàng Nato' bị bắt về hành vi tổ chức sử dụng trái phép chất ma túy. Hành vi này có thể bị phạt tù tối đa 07 năm theo Điều 255 Bộ luật Hình sự.

```cypher
MATCH (a:Article)-[:HAS_CLAUSE]->(c:Clause)
WHERE a.doc_id='blhs-dieu-255'
RETURN c.number AS number,c.penalty AS penalty ORDER BY number;
```

Baseline trả khoản 1: 02–07 năm; khoản 2: 07–15 năm; khoản 3: 15–20 năm; khoản 4: 20 năm hoặc tù chung thân; khoản 5: hình phạt bổ sung.

- **Nguyên nhân:** KG-3 baseline chỉ giữ khoản 1 hoặc khoản nhắc chất. Khoản 4 Điều 255 không nhắc chất cụ thể nên bị loại; khung cơ bản bị dùng làm tối đa.
- **Sửa và đánh đổi:** thêm PenaltyFrame, thuộc tính max_years/life/death, cạnh HAS_PENALTY. Với câu hỏi tối đa/cao nhất/nặng nhất, lấy mọi khoản liên quan và xếp death → life → max_years để đưa fact cao nhất mỗi Điều lên đầu. Không hardcode người/Điều/khoản/đáp án. Tăng số node và prompt; parser chưa bao phủ mọi hình phạt.

```cypher
MATCH (a:Article)-[:HAS_CLAUSE]->(c:Clause)-[:HAS_PENALTY]->(f:PenaltyFrame)
WHERE a.doc_id='blhs-dieu-255'
RETURN c.number AS number,f.max_years AS max_years,f.life AS life,f.death AS death,f.text AS text
ORDER BY number;
```

Kết quả mới: khoản 1 `(7,false,false)`; khoản 2 `(15,false,false)`; khoản 3 `(20,false,false)`; khoản 4 `(20,true,false)`. Frame khoản 4 được xếp cao hơn khoản 3 nhờ life=true. Q4 mới recall=1, judge=2, nguyên văn:

> Giang hồ 'Hoàng Nato' bị bắt về hành vi tổ chức sử dụng trái phép chất ma túy. Hành vi này có thể bị phạt tù tối đa 20 năm hoặc tù chung thân theo Điều 255 BLHS, khoản 4.

### E3: Chất trùng vì casing — đã sửa và kiểm chứng

- **Hiện tượng:** baseline có Ketamine/ketamine và Methamphetamine/methamphetamine thành các node riêng.
- **Bằng chứng:** cùng query trước/sau:

```cypher
MATCH (s:Substance)
WITH toLower(s.name) AS normalized, collect(s.name) AS names, count(*) AS n
WHERE n > 1
RETURN normalized, names, n ORDER BY normalized;
```

```text
Trước:
ketamine        ['Ketamine', 'ketamine']                  n=2
methamphetamine ['methamphetamine', 'Methamphetamine']  n=2
Sau: 0 bản ghi
```

- **Nguyên nhân:** khóa Substance.name trước đây lấy nguyên văn LLM; MERGE và constraint unique không đồng nhất chữ hoa/thường. Prompt đề nghị tên chuẩn không bảo đảm LLM tuân thủ.
- **Sửa và đánh đổi:** canonical_substance chuẩn hóa khoảng trắng/casing, ánh xạ chính xác về SUBSTANCES trước khi ghi node và cạnh; tên chưa biết giữ dạng casefold. Không fuzzy hóa chất hoặc đoán tên chung thành chất cụ thể. Không thêm API; chưa gộp tên lóng/tên đồng nghĩa và chưa giải quyết Case/Person trùng.

### E5: Q6 bỏ sót vụ dù graph có — còn tồn tại

- **Hiện tượng:** Graph mới chỉ trả ba vụ, bỏ vụ Viện Pháp y tâm thần; recall=0.33, judge=1.
- **Bằng chứng:** query trực tiếp:

```cypher
MATCH (k:Case)-[:INVOLVES]->(:Substance {name:'MDMA'})
RETURN k.name AS name,k.doc_id AS doc_id,k.summary AS summary ORDER BY name;
```

Kết quả mới có bốn vụ: góp tiền tại Hà Nội, Sầm Sơn, vận chuyển từ Đức, Viện Pháp y tâm thần Trung ương (`news-100260924105118645`). Per question Q6 Graph chỉ nêu ba mục: “Vụ góp tiền mua ma túy tại Hà Nội”, “Vụ tổ chức sử dụng ma túy tại Sầm Sơn”, “Vụ vận chuyển ma túy từ Đức về Việt Nam”.

- **Nguyên nhân:** context tổng hợp bị giới hạn/đi từ seed và cạnh một bước, không có chế độ truy vấn tổng hợp chuyên biệt kèm danh sách đầy đủ; LLM có thể lược bỏ thông tin. Chưa lưu prompt nguyên trạng để tách chắc chắn lỗi retrieval với lỗi trả lời; không quy toàn bộ cho LLM.
- **Đề xuất:** với câu hỏi liệt kê, lấy kết quả toàn graph và đưa từng vụ, người, doc_id vào facts riêng; kiểm tra câu trả lời bao phủ mọi dòng. Tăng prompt hoặc cần phân trang; phải phân giải Case trước khi coi node là số vụ ngoài đời.

## 4. Kết luận (5 điểm)

Q3/Q4/Q5 cho thấy lợi ích nối tin và luật: Graph mới judge=2, Flat lần lượt 0/0/1. Q1–Q2 Flat đã đủ; KG làm tăng chi phí. Graph mới recall trung bình 0.89 so Flat 0.43, nhưng dựng cao 8.31× và mỗi câu 5.92×; cần chất lượng nối nguồn đủ giá trị để bù chi phí. Q6 còn lỗi, không khẳng định GraphRAG luôn đúng. Mẫu chỉ sáu câu, hai lần trích tin không hoàn toàn ổn định; chưa kết luận tổng quát ngoài corpus này.

## 5. Tự kiểm (5 điểm)

```text
$ python -m pytest tests/ -q
51 passed in 0.08s
# 48 tests gốc + 3 regression tests bonus; không sửa test gốc.
$ python bench_kg.py --check
[OK] Dữ liệu: 18 điều luật, 20 bài báo
[OK] KG-1 link_entity
[OK] Neo4j kết nối được
[OK] KG-2 build_graph: 192 node / 337 cạnh, đường xuyên 2 KB dài 2 cạnh
[OK] KG-3 context: 22 dữ kiện, có Điều 251
[OK] KG-4 GraphRAGAgent.answer
[OK] Chi phí check: 1 lần gọi LLM, $0.00078.
$ python bench_kg.py --judge
# Sinh file benchmark mới, graph đầy đủ: 246 nodes / 425 rels.
```

Đã kiểm chứng đủ 8 label, 8 type và không thiếu doc_id ở Article/Clause/Case/PenaltyFrame. Không chạy lại --check sau benchmark vì sẽ reset graph nhỏ. Không còn NotImplementedError; giữ nguyên bench_kg.py và tests gốc.

## 6. Bằng chứng bonus trước–sau

| Chỉ số Graph | Ontology gợi ý | Ontology mới |
| --- | ---: | ---: |
| Nodes / rels | 201 / 380 | 246 / 425 |
| PenaltyFrame | 0 | 44 |
| Nhóm Substance trùng casing | 2 | 0 |
| Q4 recall / judge | 0.67 / 1 | 1.00 / 2 |
| Mean recall / judge | 0.78 / 1.67 | 0.89 / 1.83 |
| Indexing USD | 0.00926 | 0.00931 |
| Mean query USD | 0.00072 | 0.00077 |

Đáp ứng phần thiết kế có mục đích, bằng chứng và competency Q4 của bonus; điểm cuối do giảng viên chấm. Không quy cải thiện Q6 (0→0.33) chắc chắn cho schema vì LLM trích tin/sinh câu trả lời có biến động. Chứng cứ mạnh hơn là query gộp chất và frame cao nhất đã được đưa vào context Q4.

## 7. Ảnh và trạng thái nộp bài

Ba ảnh bonus người dùng cung cấp đã được kiểm tra và lưu nguyên trạng: [kg_count.png](img/kg_count.png), [kg_cross_kb.png](img/kg_cross_kb.png), [kg_my_case.png](img/kg_my_case.png). Ảnh count đủ 8 label, tổng 246 node, gồm 44 PenaltyFrame; khớp benchmark và bằng chứng bonus. Ảnh cầu nối thấy Person, Case, Crime, Article cùng ba loại cạnh. Ảnh Cái Quang Huy có 15 node/14 cạnh trong kết quả, gồm 4 Clause và 4 PenaltyFrame, thể hiện HAS_PENALTY; đây là số của kết quả truy vấn, không phải toàn graph. Cả ba thấy cửa sổ trình duyệt, ô truy vấn; hai ảnh Graph có Results overview. Phần cuối truy vấn ảnh vụ riêng vẫn bị giao diện rút gọn; truy vấn đầy đủ được ghi bên dưới. Chưa xác nhận thao tác nộp link trên vlearn.

Sau `:clear`, chụp cả cửa sổ, ô truy vấn đầy đủ, Graph và Results overview:

```cypher
// kg_count.png
MATCH (n) RETURN labels(n)[0] AS label, count(*) AS n ORDER BY n DESC;

// kg_cross_kb.png
MATCH p=(:Person)-[:INVOLVED_IN]->(:Case)-[:CHARGED_WITH]->(:Crime)<-[:DEFINES]-(:Article)
RETURN p LIMIT 25;

// kg_my_case.png — thêm khung phạt để thể hiện schema mới
MATCH p=(:Person {name:'Cái Quang Huy'})-[:INVOLVED_IN]->(k:Case)-[:CHARGED_WITH]->(:Crime)<-[:DEFINES]-(a:Article)
OPTIONAL MATCH q=(k)-[:INVOLVES|LOCATED_IN]->()
OPTIONAL MATCH f=(a)-[:HAS_CLAUSE]->(:Clause)-[:HAS_PENALTY]->(:PenaltyFrame)
RETURN p,q,f;
```

## Tự review và phản biện

- Baseline file được sao chép nguyên trạng trước thay code, không sửa tay số liệu; commit baseline cho phép tái dựng. Benchmark mới sinh trực tiếp từ code.
- PenaltyFrame thực sự thay đổi schema, không chỉ đổi tên; KG-3 thực sự dùng frame trong xếp hạng. Tests bảo vệ không nhầm số điều kiện và không biến chung thân thành năm.
- Q4 sửa đúng nhưng không suy rằng người cụ thể đã bị tuyên khung cao nhất. Q5 có judge=2 vẫn thiếu Ketamine; thừa nhận giới hạn phép đo.
- Hai lỗi baseline có bằng chứng và sửa; Q6 vẫn có lỗi cần tiếp tục nghiên cứu. Chưa làm bonus về ngưỡng khối lượng hoặc lịch sử tố tụng.
- Đã đối chiếu ảnh bonus với schema và số liệu graph mới; ghi nhận giới hạn phần cuối truy vấn bị rút gọn ở ảnh vụ riêng. Không xác nhận việc nộp link khi chưa có bằng chứng từ vlearn.
